import pandas as pd
import numpy as np
from typing import Literal, Any
from pydantic import BaseModel, Field
from ra_causal.core.contracts import StepResult, StepReport, Finding, Status
from ra_causal.core.context import PipelineContext
from ra_causal.core.registry import REGISTRY
from ra_causal.core.errors import SchemaError
from ra_causal.utils.pandas_tools import to_schema_dtype
import time

MODULE_ID = "P01"
MODULE_NAME = "schema_check"
SPEC_VERSION = "1.0"

class P01Config(BaseModel):
    # quy định hành động khi phát hiện lỗi schema. "quarantine" là mặc định, "raise" sẽ dừng pipeline, "flag" sẽ đánh dấu các dòng lỗi nhưng vẫn giữ lại
    on_error: Literal["quarantine", "raise", "flag"] = "quarantine"
    # quy định hành động khi phát hiện lỗi kiểu dữ liệu. "strict" sẽ dừng pipeline, "permissive" sẽ cố gắng ép kiểu dữ liệu
    dtype_coercion: Literal["strict", "permissive"] = "permissive"
    # quy định hành động khi phát hiện giá trị ngoài miền hợp lệ. 
    # "to_na" sẽ chuyển các giá trị ngoài miền thành NaN, "flag" sẽ đánh dấu các dòng lỗi nhưng vẫn giữ lại, "clip" sẽ cắt các giá trị ngoài miền về biên, "raise" sẽ dừng pipeline
    out_of_range: Literal["to_na", "flag", "clip", "raise"] = "flag"  

    # quy định hành động khi phát hiện cột không có trong schema. "warn_keep" sẽ cảnh báo nhưng giữ lại, "drop" sẽ loại bỏ các cột lạ, "raise" sẽ dừng pipeline
    unknown_columns: Literal["warn_keep", "drop", "raise"] = "warn_keep"

    # quy định hành động khi phát hiện khóa chính trùng lặp. 
    # "defer_to_p03" sẽ chuyển các dòng trùng lặp sang P03 để xử lý, "raise" sẽ dừng pipeline
    duplicate_key_action: Literal["defer_to_p03", "raise"] = "defer_to_p03"

    # danh sách các cột được coi là khóa chính (record_id). Mặc định là ["record_id"]
    required_id_columns: list[str] = Field(default_factory=lambda: ["record_id"])

@REGISTRY.register(MODULE_ID, P01Config)
def run(df: pd.DataFrame, cfg: P01Config, ctx: PipelineContext) -> StepResult:
    start_time = time.time()
    out = df.copy()
    findings: list[Finding] = []
    
    if out.empty:
        findings.append(Finding(code="P01.EMPTY_INPUT", severity="warning", message="Input DataFrame is empty.", count=0))
        return StepResult(
            data=out,
            report=_build_report(df, out, cfg, findings, {}, start_time, Status.OK_WITH_WARNINGS)
        )

    # 1. Check required columns
    schema_cols = ctx.schema.columns
    missing_req = [c for c, contract in schema_cols.items() if contract.required and c not in out.columns]
    if missing_req:
        raise SchemaError(
            module_id=MODULE_ID,
            code="P01.MISSING_REQUIRED_COLUMN",
            message=f"Missing required columns: {missing_req}",
            details={"missing": missing_req}
        )

    # 2. Unknown columns
    unknown_cols = [c for c in out.columns if c not in schema_cols and not c.startswith("noise_")]
    if unknown_cols:
        if cfg.unknown_columns == "raise":
            raise SchemaError(
                module_id=MODULE_ID,
                code="P01.UNKNOWN_COLUMN",
                message=f"Unknown columns found: {unknown_cols}",
                details={"unknown": unknown_cols}
            )
        elif cfg.unknown_columns == "drop":
            out = out.drop(columns=unknown_cols)
        else:
            findings.append(Finding(code="P01.UNKNOWN_COLUMN", severity="warning", message=f"Kept unknown columns: {unknown_cols}", count=len(unknown_cols), details={"columns": unknown_cols}))

    # Track errors per row (using index)
    error_mask = pd.Series(False, index=out.index)
    errors_by_column = {}
    deferred_to_p02: list[str] = []  # cột chữ chưa ép được, để P02 ánh xạ
    
    # Pre-calculate string nulls if any
    
    # 3 & 4 & 5. Type coercion, allowed categories, out of range
    for col in out.columns:
        if col not in schema_cols:
            continue
        contract = schema_cols[col]
        col_errors = {"coerce_failed": 0, "out_of_range": 0, "not_allowed": 0}
        
        # Coerce
        if cfg.dtype_coercion == "permissive":
            if contract.dtype in ("int16", "int8", "float32"):
                coerced = pd.to_numeric(out[col], errors="coerce")
                fail_mask = out[col].notna() & coerced.isna()
                if fail_mask.any():
                    col_errors["coerce_failed"] += int(fail_mask.sum())
                    error_mask |= fail_mask
                out[col] = coerced
            
            try:
                out[col] = to_schema_dtype(out[col], contract.dtype)
            except Exception:
                if contract.dtype in ("boolean", "category"):
                    # Cột nhị phân/hạng mục còn ở dạng chữ ("Yes"/"No"/"Partial", "Có"/"Không"):
                    # đó là việc của P02 (ánh xạ qua bảng alias), KHÔNG phải lỗi dòng.
                    # Nếu coi là lỗi, P01 sẽ cách ly toàn bộ dòng và P02 không bao giờ
                    # nhìn thấy dữ liệu — đã xảy ra: 120/120 dòng bị cách ly.
                    out[col] = out[col].astype(object)
                    deferred_to_p02.append(col)
                else:
                    fail_mask = out[col].notna()
                    col_errors["coerce_failed"] += int(fail_mask.sum())
                    error_mask |= fail_mask
        else:
            try:
                out[col] = to_schema_dtype(out[col], contract.dtype)
            except Exception as e:
                raise SchemaError(MODULE_ID, "P01.COERCE_FAILED", f"Failed to coerce {col} to {contract.dtype} in strict mode", {"column": col}) from e
        
        # Categorical allowed
        # CHÚ Ý: giá trị hạng mục lạ KHÔNG được tính là lỗi ở mức dòng. P02 sinh ra
        # chính là để ánh xạ "Country 1", "c1 ", "C-1" về mã chuẩn; nếu P01 đưa các
        # dòng đó vào diện cách ly thì P02 không bao giờ nhìn thấy chúng và ta mất
        # dữ liệu một cách âm thầm. Ở đây chỉ đánh dấu và báo cáo.
        if contract.dtype == "category" and contract.allowed:
            invalid_mask = out[col].notna() & (~out[col].isin(contract.allowed))
            if invalid_mask.any():
                col_errors["not_allowed"] += int(invalid_mask.sum())
                out[f"flag__p01__not_allowed__{col}"] = invalid_mask.fillna(False)

        # Range
        # Tương tự: giá trị ngoài miền có thể là lỗi ĐƠN VỊ (yield ghi kg/ha) mà P02 sẽ
        # quy đổi, hoặc giá trị cực trị mà P04 mới có quyền quyết định. P01 chỉ đánh dấu.
        if contract.range is not None and pd.api.types.is_numeric_dtype(out[col]):
            vmin, vmax = contract.range
            out_mask = (out[col].notna() & ((out[col] < vmin) | (out[col] > vmax))).fillna(False)
            if out_mask.any():
                col_errors["out_of_range"] += int(out_mask.sum())
                if cfg.out_of_range == "raise":
                    raise SchemaError(MODULE_ID, "P01.OUT_OF_RANGE", f"Values out of range in {col}", {"column": col})
                elif cfg.out_of_range == "to_na":
                    out.loc[out_mask, col] = np.nan
                elif cfg.out_of_range == "clip":
                    out[col] = out[col].clip(lower=vmin, upper=vmax)
                if cfg.out_of_range in ("flag", "to_na", "clip"):
                    out[f"flag__p01__out_of_range__{col}"] = out_mask
        
        if sum(col_errors.values()) > 0:
            errors_by_column[col] = col_errors
            if col_errors["coerce_failed"] > 0:
                findings.append(Finding(code="P01.COERCE_FAILED", severity="warning", message=f"Coercion failed in {col}", count=col_errors["coerce_failed"], column=col))
            if col_errors["out_of_range"] > 0:
                findings.append(Finding(code="P01.OUT_OF_RANGE", severity="warning", message=f"Out of range in {col}", count=col_errors["out_of_range"], column=col))
            if col_errors["not_allowed"] > 0:
                findings.append(Finding(code="P01.NOT_ALLOWED_CATEGORY", severity="warning", message=f"Not allowed categories in {col}", count=col_errors["not_allowed"], column=col))

    # 6. Record ID checks
    for rid_col in cfg.required_id_columns:
        if rid_col in out.columns:
            bad_id_mask = out[rid_col].isna() | (out[rid_col] == "")
            if bad_id_mask.any():
                error_mask |= bad_id_mask
                findings.append(Finding(code="P01.BAD_RECORD_ID", severity="error", message=f"Bad ID in {rid_col}", count=int(bad_id_mask.sum()), column=rid_col))
                # Always quarantine bad IDs
                
    if "record_id" in out.columns and out["record_id"].duplicated().any():
        n_dup = int(out["record_id"].duplicated().sum())
        if cfg.duplicate_key_action == "raise":
            raise SchemaError(MODULE_ID, "P01.DUPLICATE_KEY_SEEN", "Duplicate record_ids found")
        findings.append(Finding(code="P01.DUPLICATE_KEY_SEEN", severity="info", message="Duplicate record_ids deferred to P03", count=n_dup, column="record_id"))

    if deferred_to_p02:
        findings.append(Finding(
            code="P01.DEFERRED_TO_P02", severity="info",
            message=f"Cột nhị phân/hạng mục ghi dạng chữ, để P02 ánh xạ: {sorted(deferred_to_p02)}",
            count=len(deferred_to_p02), details={"columns": sorted(deferred_to_p02)}))

    # 7. Error handling
    artifacts = {}
    quarantined_ids = []
    
    # Include bad record_ids in quarantine unconditionally
    bad_id_mask_total = pd.Series(False, index=out.index)
    for rid_col in cfg.required_id_columns:
        if rid_col in out.columns:
            bad_id_mask_total |= (out[rid_col].isna() | (out[rid_col] == ""))
            
    quarantine_mask = bad_id_mask_total.copy()
    
    if cfg.on_error == "raise" and (error_mask & ~bad_id_mask_total).any():
        raise SchemaError(MODULE_ID, "P01.SCHEMA_ERROR", "Schema errors found and on_error=raise")
    elif cfg.on_error == "quarantine":
        quarantine_mask |= error_mask
    elif cfg.on_error == "flag":
        if "flag__p01__schema_error" not in out.columns:
            out["flag__p01__schema_error"] = False
        out["flag__p01__schema_error"] |= (error_mask & ~bad_id_mask_total)
        
    if quarantine_mask.any():
        q_df = out[quarantine_mask].copy()
        if "record_id" in q_df.columns:
            quarantined_ids = q_df["record_id"].dropna().astype(str).tolist()
        artifacts["quarantine"] = q_df
        out = out[~quarantine_mask].copy()

    status = Status.OK_WITH_WARNINGS if findings else Status.OK
    
    details = {
        "errors_by_column": errors_by_column,
        "n_quarantined": len(quarantined_ids),
        "schema_version": ctx.schema.version
    }
    findings.append(Finding(f"{MODULE_ID}.SUMMARY", "info", "Module summary", count=0, details=details))

    report = _build_report(df, out, cfg, findings, artifacts, start_time, status)
    
    return StepResult(
        data=out,
        report=report,
        artifacts=artifacts,
        context_updates={"quarantined_ids": quarantined_ids}
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
        context_updates=["quarantined_ids"]
    )

