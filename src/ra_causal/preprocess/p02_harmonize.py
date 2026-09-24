import pandas as pd
import numpy as np
from typing import Literal, Any
from pydantic import BaseModel
import difflib
import unicodedata
import time
import os
import yaml

from ra_causal.core.contracts import StepResult, StepReport, Finding, Status
from ra_causal.core.context import PipelineContext
from ra_causal.core.registry import REGISTRY
from ra_causal.core.errors import ConfigError

MODULE_ID = "P02"
MODULE_NAME = "harmonize"
SPEC_VERSION = "1.0"

class StringNormalize(BaseModel):
    trim: bool = True
    lower: bool = True
    strip_accents: bool = True
    collapse_spaces: bool = True

class UnmappedAction(BaseModel):
    # Hành vi khi gặp giá trị không được ánh xạ 
    # "to_na": đổi thành NaN, "keep_raw": giữ nguyên giá trị thô, "raise": ném lỗi
    default: Literal["to_na", "keep_raw", "raise"] = "to_na"
    # Ghi đè theo cột: ví dụ {"country": "raise", "cover_crop": "raise"}
    overrides: dict[str, Literal["to_na", "keep_raw", "raise"]] = {"country": "raise", "cover_crop": "raise"}

class P02Config(BaseModel):
    string_normalize: StringNormalize = StringNormalize()
    # Cách ánh xạ hạng mục: "explicit" dùng alias trong raw_assumed.yaml, "fuzzy_suggest" gợi ý nhưng không tự đổi, "fuzzy_auto" tự đổi nếu khớp gần đúng
    category_mapping_mode: Literal["explicit", "fuzzy_suggest", "fuzzy_auto"] = "explicit"
    # Ngưỡng khớp gần đúng: nếu tỷ lệ giống nhau (SequenceMatcher) >= ngưỡng này thì coi là khớp
    fuzzy_threshold: float = 0.90
    unmapped_action: UnmappedAction = UnmappedAction()
    # Cách xử lý đơn vị năng suất: "unit_column" dùng cột yield_unit, "source_declaration" dùng khai báo trong raw_assumed.yaml, "threshold_inference" suy luận theo ngưỡng, "none" không đổi
    unit_policy: Literal["unit_column", "source_declaration", "threshold_inference", "none"] = "unit_column"
    # Cột chứa đơn vị năng suất (chỉ dùng khi unit_policy="unit_column")
    unit_column_name: str = "yield_unit"
    # Hành vi khi unit_policy="unit_column" nhưng cột đơn vị không có trong dữ liệu: "source_declaration" dùng khai báo trong raw_assumed.yaml, "none" không đổi, "raise" ném lỗi
    unit_fallback: Literal["source_declaration", "none", "raise"] = "source_declaration"
    # Ngưỡng suy luận đơn vị: nếu yield > ngưỡng này thì suy luận là kg/ha, còn lại là t/ha
    unit_threshold: float = 1000.0
    # Cách xác định mức hạng mục: "schema" dùng allowed trong schema, "data" lấy từ dữ liệu (có thể thay đổi giữa các lần chạy)
    decimal_comma: Literal["auto", True, False] = "auto"
    # Cách xác định mức hạng mục: "schema" dùng allowed trong schema, "data" lấy từ dữ liệu (có thể thay đổi giữa các lần chạy)
    category_levels_source: Literal["schema", "data"] = "schema"

def _normalize_string(s, cfg: StringNormalize):
    if not isinstance(s, str):
        return s
    if cfg.strip_accents:
        s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    if cfg.lower:
        s = s.lower()
    if cfg.collapse_spaces:
        s = " ".join(s.split())
    elif cfg.trim:
        s = s.strip()
    return s

def _is_text_like(series: pd.Series) -> bool:
    """Cột có thể chứa chuỗi: object, string, hoặc category (category phải đổi sang object
    trước khi gán giá trị mới, nếu không pandas báo 'Cannot setitem on a Categorical')."""
    return (
        pd.api.types.is_object_dtype(series)
        or pd.api.types.is_string_dtype(series)
        or isinstance(series.dtype, pd.CategoricalDtype)
    )

def _alias_table(col: str, contract, raw_config: dict, norm_cfg: StringNormalize) -> dict:
    """Bảng alias áp dụng cho đúng một cột, khóa đã được chuẩn hóa cùng cách với dữ liệu.

    Tách theo cột thay vì gộp chung một bảng, để alias của quốc gia không vô tình
    được dùng cho biến nhị phân và ngược lại.
    """
    if contract is not None and contract.dtype == "boolean":
        src = raw_config.get("boolean_aliases", {}) or {}
    elif col == "country":
        src = raw_config.get("country_aliases", {}) or {}
    else:
        src = (raw_config.get("category_aliases", {}) or {}).get(col, {}) or {}
    return {_normalize_string(str(k), norm_cfg): v for k, v in src.items()}

def _match_allowed(raw_val, norm_allowed: dict, norm_cfg: StringNormalize):
    """Khớp một giá trị thô với tập giá trị hợp lệ của schema. Trả về mã canonical hoặc None.

    Chuẩn hóa chỉ dùng để SO KHỚP; giá trị trả về luôn là mã canonical đúng hoa/thường.
    """
    if isinstance(raw_val, (bool, np.bool_)):
        return int(raw_val) if int(raw_val) in norm_allowed.values() else None
    if isinstance(raw_val, (int, float, np.integer, np.floating)) and not pd.isna(raw_val):
        if float(raw_val).is_integer() and int(raw_val) in norm_allowed.values():
            return int(raw_val)
    key = _normalize_string(str(raw_val), norm_cfg)
    return norm_allowed.get(key)

@REGISTRY.register(MODULE_ID, P02Config)
def run(df: pd.DataFrame, cfg: P02Config, ctx: PipelineContext) -> StepResult:
    start_time = time.time()
    out = df.copy()
    findings = []
    
    # Load raw_assumed for aliases
    raw_config_path = os.path.join(os.path.dirname(__file__), "../../../configs/schema/raw_assumed.yaml")
    with open(raw_config_path, "r", encoding="utf-8") as f:
        raw_config = yaml.safe_load(f)
    
    # 1. Chuẩn hóa chuỗi & 6. dấu thập phân
    # Chuẩn hóa chỉ phục vụ việc SO KHỚP. Cột mã định danh (record_id, grower_id, field_id…)
    # chỉ được cắt khoảng trắng: hạ hoa hay bỏ dấu ở đó là sửa chính khóa dữ liệu.
    # Hạ hoa/bỏ dấu chỉ áp cho cột hạng mục và nhị phân, rồi được ánh xạ về mã canonical ở bước 2.
    id_norm = StringNormalize(
        trim=cfg.string_normalize.trim,
        collapse_spaces=cfg.string_normalize.collapse_spaces,
        lower=False,
        strip_accents=False,
    )
    for col in out.columns:
        if not _is_text_like(out[col]):
            continue
        contract = ctx.schema.columns.get(col)
        is_mapped_col = contract is not None and contract.dtype in ("category", "boolean")
        norm_cfg = cfg.string_normalize if is_mapped_col else id_norm

        s = out[col].astype(object)
        s = s.map(lambda x: _normalize_string(x, norm_cfg) if isinstance(x, str) else x)

        # Dấu thập phân: chỉ xét cột mà schema khai là số nhưng dữ liệu còn ở dạng chuỗi
        if contract is not None and contract.dtype in ("float32", "float64", "int8", "int16"):
            s_val = s.dropna().astype(str)
            if not s_val.empty:
                use_comma = False
                if cfg.decimal_comma == "auto":
                    use_comma = bool(s_val.str.match(r"^\d+,\d+$").mean() > 0.5)
                elif cfg.decimal_comma is True:
                    use_comma = True
                if use_comma:
                    s = s.map(lambda x: x.replace(",", ".") if isinstance(x, str) else x)

        out[col] = s

    # 2. Category mapping
    mapping_applied = []
    fuzzy_suggestions = []
    raise_bucket: dict[str, list[dict]] = {}  # cột có chính sách raise -> các giá trị lạ
    for col in out.columns:
        if col not in ctx.schema.columns:
            continue
        contract = ctx.schema.columns[col]
        is_cat_or_bool = contract.dtype in ("category", "boolean")
        
        if is_cat_or_bool:
            if contract.dtype == "boolean":
                allowed = [0, 1]
            elif cfg.category_levels_source == "data":
                # Lấy mức từ chính dữ liệu: linh hoạt nhưng tập mức đổi giữa các lần chạy
                allowed = sorted({str(v) for v in out[col].dropna().unique()})
                findings.append(Finding(
                    "P02.CATEGORY_LEVELS_FROM_DATA", "warning",
                    f"Mức hạng mục của '{col}' lấy từ dữ liệu, không phải từ schema: "
                    "tập mức có thể đổi giữa các lần chạy",
                    count=len(allowed), column=col))
            else:
                allowed = contract.allowed or []

            if out[col].isna().all():
                continue

            # Làm việc trên bản sao dạng object: gán giá trị mới vào Categorical sẽ báo lỗi
            # "Cannot setitem on a Categorical with a new category".
            s = out[col].astype(object)
            aliases = _alias_table(col, contract, raw_config, cfg.string_normalize)
            norm_allowed = {_normalize_string(str(v), cfg.string_normalize): v for v in allowed}

            for raw_val in pd.unique(s.dropna()):
                mapped_val = _match_allowed(raw_val, norm_allowed, cfg.string_normalize)

                norm_key = _normalize_string(str(raw_val), cfg.string_normalize)
                if mapped_val is None and norm_key in aliases and aliases[norm_key] is None:
                    # Alias khai `null` (vd "Partial": null) nghĩa là CỐ Ý để trống: giá trị
                    # hợp lệ về mặt nghiệp vụ nhưng không xếp được vào mã nào. Khác hẳn
                    # "chưa ánh xạ được" — nên không bị chính sách raise chặn, mà được đưa
                    # về ô trống kèm cờ để người phân tích xem lại từng dòng.
                    mask = s == raw_val
                    n_rows = int(mask.sum())
                    s = s.mask(mask, np.nan)
                    flag_col = f"flag__p02__intentional_na__{col}"
                    if flag_col not in out.columns:
                        out[flag_col] = False
                    out.loc[mask[mask].index, flag_col] = True
                    ids = sorted(out.loc[mask, "record_id"].astype(str).tolist())[:10] if "record_id" in out.columns else []
                    findings.append(Finding(
                        "P02.ALIAS_TO_NA", "warning",
                        f"'{raw_val}' ở cột {col} được khai là cố ý để trống (alias null): "
                        f"{n_rows} dòng thành ô trống và được gắn cờ {flag_col} để xem lại",
                        count=n_rows, column=col, sample_ids=ids))
                    continue

                if mapped_val is None:
                    mapped_val = aliases.get(norm_key)

                # Khớp gần đúng
                if mapped_val is None and cfg.category_mapping_mode in ("fuzzy_suggest", "fuzzy_auto") and isinstance(raw_val, str):
                    norm_raw = _normalize_string(raw_val, cfg.string_normalize)
                    best_match, best_score = None, 0.0
                    for norm_val, valid in norm_allowed.items():
                        score = difflib.SequenceMatcher(None, norm_raw, norm_val).ratio()
                        if score > best_score:
                            best_score, best_match = score, valid
                    if best_score >= cfg.fuzzy_threshold:
                        if cfg.category_mapping_mode == "fuzzy_auto":
                            mapped_val = best_match
                        else:
                            fuzzy_suggestions.append({"column": col, "raw_value": raw_val,
                                                      "suggestion": best_match, "score": round(best_score, 4)})

                mask = s == raw_val
                n_rows = int(mask.sum())

                if mapped_val is not None:
                    if mapped_val != raw_val:
                        mapping_applied.append({"column": col, "raw_value": str(raw_val),
                                                "mapped_value": str(mapped_val), "n_rows": n_rows})
                        s = s.mask(mask, mapped_val)
                else:
                    action = cfg.unmapped_action.overrides.get(col, cfg.unmapped_action.default)
                    if action == "raise":
                        # Chưa dừng ngay: gom HẾT giá trị lạ của mọi cột rồi báo một lần,
                        # để người dùng bổ sung alias trong một lượt thay vì chạy lại từng giá trị.
                        raise_bucket.setdefault(col, []).append({"raw_value": str(raw_val), "n_rows": n_rows})
                        continue
                    if action == "to_na":
                        s = s.mask(mask, np.nan)
                    # keep_raw: giữ nguyên giá trị
                    flag_col = f"flag__p02__unmapped__{col}"
                    if flag_col not in out.columns:
                        out[flag_col] = False
                    out.loc[mask[mask].index, flag_col] = True
                    findings.append(Finding("P02.UNMAPPED_CATEGORY", "warning",
                                            f"Không ánh xạ được '{raw_val}' trong {col}",
                                            count=n_rows, column=col))

            out[col] = s

            # 7. Ép lại kiểu theo schema
            if contract.dtype == "boolean":
                out[col] = pd.to_numeric(out[col], errors="coerce").astype("Float64").astype("boolean")
            elif contract.dtype == "category":
                out[col] = out[col].astype("category")

    if raise_bucket:
        lines = [f"  - {col}: " + ", ".join(f"'{v['raw_value']}' ({v['n_rows']} dòng)" for v in vals)
                 for col, vals in sorted(raise_bucket.items())]
        raise ConfigError(
            MODULE_ID, "P02.UNMAPPED_CATEGORY",
            "Có giá trị không ánh xạ được ở cột đặt chính sách raise:\n" + "\n".join(lines) +
            "\nBổ sung alias trong configs/schema/raw_assumed.yaml "
            "(hoặc khai `null` nếu giá trị đó hợp lệ nhưng cố ý để trống).",
            details={"unmapped": {col: vals for col, vals in sorted(raise_bucket.items())}})

    if fuzzy_suggestions:
        findings.append(Finding("P02.FUZZY_SUGGESTION", "info", "Fuzzy suggestions generated", count=len(fuzzy_suggestions)))

    # 4 & 5. Unit conversion
    unit_conversions = {}
    if "yield_t_ha" in out.columns:
        yield_vals = pd.to_numeric(out["yield_t_ha"], errors="coerce")
        n_converted = 0
        factor = 1.0
        policy_used = "none"
        
        needs_conversion = False
        
        if cfg.unit_policy == "threshold_inference":
            if (yield_vals > cfg.unit_threshold).any():
                needs_conversion = True
                policy_used = "threshold_inference"
        elif cfg.unit_policy == "source_declaration":
            # This logic depends on what is in unit_declarations in raw_assumed.yaml
            if raw_config.get("unit_declarations", {}).get("yield") == "kg/ha":
                needs_conversion = True
                policy_used = "source_declaration"
        # Ignoring unit_column logic for brevity unless we have yield_unit column
        elif cfg.unit_policy == "unit_column":
            if cfg.unit_column_name in out.columns:
                mask = out[cfg.unit_column_name].astype(str).str.lower().str.contains("kg")
                if mask.any():
                    out.loc[mask, "yield_t_ha"] = pd.to_numeric(out.loc[mask, "yield_t_ha"], errors="coerce") / 1000.0
                    # Cập nhật luôn cột đơn vị: sau khi quy đổi, dữ liệu đã là t/ha.
                    # Không làm việc này thì chạy module lần hai sẽ chia tiếp 1000.
                    out.loc[mask, cfg.unit_column_name] = ctx.schema.columns["yield_t_ha"].unit or "t/ha"
                    n_converted = int(mask.sum())
                    policy_used = "unit_column"
                    factor = 1000.0
            else:
                if cfg.unit_fallback == "raise":
                    raise ConfigError(MODULE_ID, "P02.UNIT_POLICY_UNAVAILABLE", "unit_column not found")
                elif cfg.unit_fallback == "source_declaration":
                    if raw_config.get("unit_declarations", {}).get("yield") == "kg/ha":
                        needs_conversion = True
                        policy_used = "source_declaration"
        
        if needs_conversion:
            factor = 1000.0
            if policy_used == "threshold_inference":
                # Chỉ quy đổi ĐÚNG những dòng vượt ngưỡng. Chia cả cột sẽ phá 80% dòng
                # vốn đã ghi đúng t/ha.
                mask = (yield_vals > cfg.unit_threshold).fillna(False)
                out.loc[mask, "yield_t_ha"] = yield_vals[mask] / factor
                n_converted = int(mask.sum())
                out["flag__p02__unit_inferred"] = mask
                findings.append(Finding(
                    "P02.UNIT_INFERRED", "warning",
                    f"Đơn vị được SUY LUẬN theo ngưỡng {cfg.unit_threshold} cho {n_converted} dòng; "
                    "một ruộng năng suất thật sự cao có thể bị chia nhầm 1000",
                    count=n_converted, column="yield_t_ha"))
            else:
                # Khai báo theo nguồn: cả nguồn dùng chung một đơn vị
                out["yield_t_ha"] = yield_vals / factor
                n_converted = int(yield_vals.notna().sum())
        
        if n_converted > 0:
            findings.append(Finding("P02.UNIT_CONVERTED", "info", f"Yield converted by {policy_used}", count=n_converted))
            unit_conversions["yield_t_ha"] = factor
            
        # Mixed unit suspected
        if yield_vals.notna().any():
            high_prop = (yield_vals > 1000).mean()
            if 0.02 <= high_prop <= 0.98:
                findings.append(Finding("P02.MIXED_UNIT_SUSPECTED", "warning", "Bimodal yield distribution suggests mixed units", count=len(yield_vals)))

    status = Status.OK_WITH_WARNINGS if any(f.severity in ("warning", "error") for f in findings) else Status.OK
    
    details = {
        "mapping_applied": sorted(mapping_applied, key=lambda x: (x["column"], x["raw_value"])),
        "unit_conversion": {"n_rows_converted": n_converted, "factor": factor, "policy_used": policy_used} if "yield_t_ha" in out.columns else {},
        "fuzzy_suggestions": fuzzy_suggestions
    }
    findings.append(Finding(f"{MODULE_ID}.SUMMARY", "info", "Module summary", count=0, details=details))

    report = _build_report(df, out, cfg, findings, {}, start_time, status)
    
    return StepResult(
        data=out,
        report=report,
        context_updates={"unit_conversions": unit_conversions}
    )

def _build_report(df_in, df_out, cfg, findings, artifacts, start_time, status):
    cols_added = sorted(set(df_out.columns) - set(df_in.columns))
    cols_mod = [c for c in df_in.columns if c in df_out.columns and not df_in[c].equals(df_out[c])]
    
    return StepReport(
        module_id=MODULE_ID,
        module_name=MODULE_NAME,
        spec_version=SPEC_VERSION,
        status=status,
        started_at=pd.Timestamp(start_time, unit='s').isoformat(),
        duration_s=round(time.time() - start_time, 3),
        n_rows_in=len(df_in),
        n_rows_out=len(df_out),
        n_cols_in=len(df_in.columns),
        n_cols_out=len(df_out.columns),
        rows_dropped=len(df_in) - len(df_out),
        rows_flagged=int(df_out[[c for c in df_out.columns if c.startswith("flag__")]].any(axis=1).sum()) if any(c.startswith("flag__") for c in df_out.columns) else 0,
        columns_added=cols_added,
        columns_modified=cols_mod,
        params_effective=cfg.model_dump(),
        findings=findings,
        artifacts={k: f"{k}.parquet" for k in artifacts.keys()},
        context_updates=["unit_conversions"]
    )

