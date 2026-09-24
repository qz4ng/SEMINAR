import pandas as pd
import numpy as np
from typing import Literal
from pydantic import BaseModel, Field
import time

from ra_causal.core.contracts import StepResult, StepReport, Finding, Status
from ra_causal.core.context import PipelineContext
from ra_causal.core.registry import REGISTRY
from ra_causal.core.errors import ConfigError

MODULE_ID = "P05"
MODULE_NAME = "treatment_define"
SPEC_VERSION = "1.0"

class P05Config(BaseModel):
    # Xác định cách xác định biến điều trị từ cột nguồn. Các chế độ:
    # - binary_threshold: nhị phân hóa dựa trên ngưỡng (default)
    # - multi_level: nhiều mức dựa trên ngưỡng (không được triển khai trong mã hiện tại)
    # - per_version: xác định điều trị dựa trên từng phiên bản (không được triển khai trong mã hiện tại)
    # - continuous: giữ nguyên giá trị liên tục (không được triển khai trong mã hiện tại)
    mode: Literal["binary_threshold", "multi_level", "per_version", "continuous"] = "binary_threshold"
    source_column: str = "cover_crop_months"

    # Các tham số cho chế độ nhị phân hóa dựa trên ngưỡng
    # Các mẫu có giá trị >= threshold_months được coi là "điều trị" (True), các mẫu < threshold_months được coi là "kiểm soát" (False).
    threshold_months: float = 2.0
    # Danh sách các ngưỡng để kiểm tra độ nhạy. Mỗi ngưỡng sẽ tạo ra một cột điều trị mới,
    #  ví dụ: cover_crop__thr1p0, cover_crop__thr2p0, ....
    threshold_sensitivity: list[float] = Field(default_factory=lambda: [1.0, 2.0, 3.0])
    # Hành động đối với các mẫu "partial" (một số điều kiện được thỏa mãn nhưng không đủ để xác định là điều trị hay kiểm soát).
    partial_action: Literal["to_na", "treated", "control", "own_level"] = "to_na"

    # Nhóm các loại cover crop thành các nhóm lớn hơn để tránh các ô nhỏ. Các tùy chọn:
    # - group: nhóm các loại cover crop thành các nhóm lớn hơn (ví dụ: "legume", "grass", "mixed")
    # - all: giữ nguyên tất cả các loại cover crop riêng lẻ
    # - keep: giữ nguyên các loại cover crop hiện có    
    type_grouping: Literal["group", "all", "keep"] = "group"


    # Các mẫu trong các ô nhỏ hơn min_cell sẽ được cảnh báo trong báo cáo.
    min_cell: int = 30
    write_treatment_column: bool = True

def _partial_mask(out: pd.DataFrame, cfg: "P05Config", has_source: bool) -> pd.Series:
    """Dòng nào là "Partial".

    Nguồn tin cậy nhất là cờ của P02: `flag__p02__intentional_na__cover_crop` đánh dấu
    đúng những ô khai `null` trong bảng alias (vd "Partial"). Nếu không có cờ đó (dữ liệu
    cũ, hoặc P02 dùng unmapped_action=to_na), mới suy luận gián tiếp: cover_crop trống
    nhưng số tháng > 0.
    """
    mask = pd.Series(False, index=out.index)
    if "flag__p02__intentional_na__cover_crop" in out.columns:
        mask = out["flag__p02__intentional_na__cover_crop"].fillna(False).astype(bool)
    elif "flag__p02__unmapped__cover_crop" in out.columns and has_source and "cover_crop" in out.columns:
        months = pd.to_numeric(out[cfg.source_column], errors="coerce")
        mask = (out["cover_crop"].isna() & (months > 0)).fillna(False).astype(bool)
    return mask


def _apply_partial(treatment: pd.Series, partial_mask: pd.Series, action: str) -> pd.Series:
    """Áp partial_action lên cột treatment nhị phân (kiểu boolean nullable)."""
    t = treatment.copy()
    if action == "treated":
        t[partial_mask] = True
    elif action == "control":
        t[partial_mask] = False
    else:  # to_na, và own_level (không có mức riêng khi treatment nhị phân)
        t[partial_mask] = pd.NA
    return t


@REGISTRY.register(MODULE_ID, P05Config)
def run(df: pd.DataFrame, cfg: P05Config, ctx: PipelineContext) -> StepResult:
    start_time = time.time()
    out = df.copy()
    findings = []
    
    if "cover_crop" in out.columns:
        # Chỉ lưu giá trị gốc ở lần chạy đầu: chạy lại module không được ghi đè
        # bản gốc bằng giá trị đã nhị phân hóa.
        if "cover_crop__raw" not in out.columns:
            out["cover_crop__raw"] = out["cover_crop"]
        
    has_source = cfg.source_column in out.columns and out[cfg.source_column].notna().any()
    partial_mask = _partial_mask(out, cfg, has_source)
    artifacts = {}

    if not has_source:
        findings.append(Finding("P05.FALLBACK_TO_BINARY", "warning", "source_column missing or all NaN, using cover_crop", count=0))
        # Chỉ có cover_crop dạng Có/Không/Partial: vẫn phải áp partial_action,
        # nếu không thì dòng "Partial" lặng lẽ thành ô trống mà không ai biết.
        if partial_mask.any() and "cover_crop" in out.columns:
            out["cover_crop"] = _apply_partial(out["cover_crop"].astype("boolean"), partial_mask, cfg.partial_action)
    else:
        # Binary threshold
        new_treatment = out[cfg.source_column] >= cfg.threshold_months
        new_treatment = new_treatment.where(out[cfg.source_column].notna(), np.nan)
        
        # Partial action
        if partial_mask.any():
            new_treatment = _apply_partial(new_treatment.astype(float).astype("boolean"),
                                           partial_mask, cfg.partial_action)

        if cfg.write_treatment_column:
            out["cover_crop"] = new_treatment.astype(float).astype("boolean")

        # Sensitivities
        max_diff_count = 0
        for thr in cfg.threshold_sensitivity:
            col_name = f"cover_crop__thr{str(thr).replace('.', 'p') if thr % 1 != 0 else int(thr)}"
            sens_treatment = (out[cfg.source_column] >= thr).where(out[cfg.source_column].notna(), np.nan).astype(float).astype("boolean")
            out[col_name] = sens_treatment
            if new_treatment is not None:
                diff_mask = (sens_treatment != new_treatment) & sens_treatment.notna() & new_treatment.notna()
                max_diff_count = max(max_diff_count, int(diff_mask.sum()))
                
        if max_diff_count > 0:
            findings.append(Finding("P05.THRESHOLD_SENSITIVITY", "info", f"Max {max_diff_count} samples change status under sensitivity thresholds", count=max_diff_count))
            
        # Type grouping
        if "cover_crop_type" in out.columns:
            if cfg.type_grouping == "group":
                out["cover_crop_type__grouped"] = out["cover_crop_type"]
                # logic to group if needed. Since ["none", "legume", "grass", "mixed"] is already grouped, do nothing
            else:
                out["cover_crop_type__grouped"] = out["cover_crop_type"]
                
            # Version table & Heterogeneity
            # Simplification: just check if groups < min_cell
            counts = out["cover_crop_type__grouped"].value_counts()
            for k, v in counts.items():
                if v > 0 and v < cfg.min_cell:
                    findings.append(Finding("P05.SMALL_VERSION_CELL", "warning", f"Small version cell: {k}", count=v))
                    
            if "yield_t_ha" in out.columns:
                means = out[out["cover_crop"] == True].groupby("cover_crop_type__grouped", observed=True)["yield_t_ha"].mean()
                if len(means.dropna()) > 1:
                    max_diff = means.max() - means.min()
                    pooled_sd = out.loc[out["cover_crop"] == True, "yield_t_ha"].std()
                    if pooled_sd > 0 and max_diff > pooled_sd:
                        findings.append(Finding("P05.VERSION_HETEROGENEITY", "warning", "Yield means vary > 1 SD across cover crop types", count=len(means)))

    if partial_mask.any():
        # Không bỏ dòng nào: gắn cờ từng dòng "Partial" và tách một bảng rà soát riêng,
        # để người phân tích xem domain của chính cột đó rồi mới quyết định giữ hay bỏ.
        out["flag__p05__partial"] = partial_mask
        ids = sorted(out.loc[partial_mask, "record_id"].astype(str).tolist()) if "record_id" in out.columns else []
        findings.append(Finding(
            "P05.PARTIAL_FLAGGED", "warning",
            f"{int(partial_mask.sum())} dòng ghi 'Partial' được gắn cờ flag__p05__partial "
            f"(xử lý theo partial_action = '{cfg.partial_action}'); xem artifact partial_review",
            count=int(partial_mask.sum()), column="cover_crop", sample_ids=ids[:10],
            details={"partial_action": cfg.partial_action}))
        if cfg.partial_action == "own_level":
            findings.append(Finding(
                "P05.OWN_LEVEL_NOT_BINARY", "warning",
                "partial_action='own_level' cần treatment nhiều mức; với treatment nhị phân, "
                "các dòng này được để trống ở cột cover_crop",
                count=int(partial_mask.sum()), column="cover_crop"))
        artifacts["partial_review"] = out.loc[partial_mask].copy()

    if out["cover_crop"].isna().any():
        findings.append(Finding("P05.TREATMENT_MISSING", "warning", "Treatment column has NaNs", count=int(out["cover_crop"].isna().sum())))

    treatment_def = {
        "source": cfg.source_column if has_source else "cover_crop",
        "rule": f">= {cfg.threshold_months}" if has_source else "asis",
        "partial_action": cfg.partial_action,
        "type_grouping": cfg.type_grouping
    }
    
    status = Status.OK_WITH_WARNINGS if any(f.severity in ("warning", "error") for f in findings) else Status.OK

    report = StepReport(
        module_id=MODULE_ID,
        module_name=MODULE_NAME,
        spec_version=SPEC_VERSION,
        status=status,
        started_at=pd.Timestamp(start_time, unit='s').isoformat(),
        duration_s=round(time.time() - start_time, 3),
        n_rows_in=len(df),
        n_rows_out=len(out),
        n_cols_in=len(df.columns),
        n_cols_out=len(out.columns),
        rows_dropped=0,
        rows_flagged=int(out[[c for c in out.columns if c.startswith("flag__")]].any(axis=1).sum()) if any(c.startswith("flag__") for c in out.columns) else 0,
        columns_added=sorted(list(set(out.columns) - set(df.columns))),
        columns_modified=[c for c in df.columns if c in out.columns and not df[c].equals(out[c])],
        params_effective=cfg.model_dump(),
        findings=findings,
        artifacts={name: f"{name}.parquet" for name in artifacts},
        context_updates=["treatment_definition", "treatment_column"]
    )
    
    return StepResult(data=out, report=report, artifacts=artifacts, context_updates={"treatment_definition": treatment_def, "treatment_column": "cover_crop"})

