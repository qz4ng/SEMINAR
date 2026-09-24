import pandas as pd
import numpy as np
from typing import Literal
from pydantic import BaseModel, Field
import time

from ra_causal.core.contracts import StepResult, StepReport, Finding, Status
from ra_causal.core.context import PipelineContext
from ra_causal.core.registry import REGISTRY
from ra_causal.core.errors import DataQualityError

MODULE_ID = "P04"
MODULE_NAME = "outliers"
SPEC_VERSION = "1.0"

class P04Config(BaseModel):
    # Mô tả các cột cần kiểm tra outlier, phương pháp kiểm tra, và các tham số liên quan
    columns: list[str] = Field(default_factory=lambda: ["yield_t_ha", "field_size_ha", "soil_om_baseline_pct", "experience_yr"])


    # Phương pháp kiểm tra outlier: "domain_range" sử dụng khoảng giá trị hợp lệ từ schema, "iqr" sử dụng khoảng IQR, 
    # "robust_z" sử dụng robust z-score, "percentile" sử dụng các percentile.
    method: Literal["domain_range", "iqr", "robust_z", "percentile"] = "robust_z"
    method_by_column: dict[str, Literal["domain_range", "iqr", "robust_z", "percentile"]] = Field(default_factory=lambda: {"yield_t_ha": "domain_range", "field_size_ha": "domain_range"})
    iqr_k: float = 3.0
    robust_z_threshold: float = 3.5
    percentile_bounds: tuple[float, float] = (0.005, 0.995)
    group_by: list[str] = Field(default_factory=lambda: ["country"])
    min_group_size: int = 30
    # Hành động sau khi phát hiện outlier: 
    # "flag_only" chỉ đánh dấu, "winsorize" thay thế giá trị outlier bằng ngưỡng, "to_na" thay thế bằng NaN, 
    # "drop_row" loại bỏ hàng, "log_transform" áp dụng log transform, "keep_as_feature" giữ nguyên và tạo cột mới.
    action: Literal["flag_only", "winsorize", "to_na", "drop_row", "log_transform", "keep_as_feature"] = "flag_only"
    parallel_actions: list[Literal["winsorize", "log_transform"]] = Field(default_factory=lambda: ["winsorize"])
    winsorize_at: Literal["bound", "percentile"] = "bound"
    # Tỷ lệ tối đa các hàng bị đánh dấu là outlier trước khi ném lỗi. Nếu tỷ lệ này vượt quá, có thể có vấn đề với dữ liệu (ví dụ: lỗi đơn vị).
    max_flag_rate: float = 0.05
    unit_error_detection: bool = True
    unit_error_factors: list[float] = Field(default_factory=lambda: [1000, 100, 10, 0.1, 0.01, 0.001])

@REGISTRY.register(MODULE_ID, P04Config)
def run(df: pd.DataFrame, cfg: P04Config, ctx: PipelineContext) -> StepResult:
    start_time = time.time()
    out = df.copy()
    findings = []
    
    thresholds_report = {}
    suspected_unit_factors = {}
    summary_before_after = {}
    
    any_flag = pd.Series(False, index=out.index)
    rows_dropped = 0
    
    for col in cfg.columns:
        if col not in out.columns:
            continue
        if not pd.api.types.is_numeric_dtype(out[col]) or pd.api.types.is_bool_dtype(out[col]):
            findings.append(Finding("P04.NON_NUMERIC_COLUMN_SKIPPED", "warning", f"Skipped non-numeric {col}", count=1, column=col))
            continue
            
        method = cfg.method_by_column.get(col, cfg.method)
        flag_col = f"flag__p04__outlier__{col}"
        out[flag_col] = False
        
        col_flags = pd.Series(False, index=out.index)
        
        
        bounds_lower = pd.Series(np.nan, index=out.index)
        bounds_upper = pd.Series(np.nan, index=out.index)
        
        # Calculate thresholds
        if method == "domain_range":
            contract = ctx.schema.columns.get(col)
            if contract and contract.range:
                vmin, vmax = contract.range
                col_flags = (out[col].notna() & ((out[col] < vmin) | (out[col] > vmax))).fillna(False).astype(bool)
                thresholds_report[f"{col}_all"] = {"lower": vmin, "upper": vmax, "method": method, "n_flagged": int(col_flags.sum())}
                if cfg.winsorize_at == "percentile":
                    p_lower, p_upper = out[col].dropna().quantile(cfg.percentile_bounds)
                    bounds_lower.loc[:] = p_lower
                    bounds_upper.loc[:] = p_upper
                else:
                    bounds_lower.loc[:] = vmin
                    bounds_upper.loc[:] = vmax
        else:
            # Grouped
            # observed=True: chỉ lặp qua nhóm thật sự có dữ liệu, không lặp qua mức category rỗng
            groups = out.groupby(cfg.group_by, observed=True)
            for name, idx in groups.groups.items():
                group_vals = out.loc[idx, col].dropna()
                if len(group_vals) < cfg.min_group_size:
                    findings.append(Finding("P04.SMALL_GROUP", "info", f"Group {name} size {len(group_vals)} < {cfg.min_group_size}, using global bounds", count=len(group_vals), column=col))
                    # global
                    group_vals = out[col].dropna()
                    name = "global"
                    if len(group_vals) == 0:
                        continue
                        
                lower, upper = -np.inf, np.inf
                if method == "robust_z":
                    med = group_vals.median()
                    mad = np.median(np.abs(group_vals - med))
                    if mad == 0:
                        findings.append(Finding("P04.ZERO_MAD", "warning", f"Zero MAD in {col} group {name}", count=len(group_vals), column=col))
                        continue
                    z = 0.6745 * (group_vals - med) / mad
                    # We approximate bounds
                    lower = med - (cfg.robust_z_threshold * mad / 0.6745)
                    upper = med + (cfg.robust_z_threshold * mad / 0.6745)
                elif method == "iqr":
                    q1, q3 = group_vals.quantile([0.25, 0.75])
                    iqr = q3 - q1
                    lower = q1 - cfg.iqr_k * iqr
                    upper = q3 + cfg.iqr_k * iqr
                elif method == "percentile":
                    lower, upper = group_vals.quantile(cfg.percentile_bounds)
                    
                mask = (out.loc[idx, col] < lower) | (out.loc[idx, col] > upper)
                col_flags.loc[idx] = mask.fillna(False).astype(bool)
                
                if cfg.winsorize_at == "percentile":
                    w_lower, w_upper = group_vals.quantile(cfg.percentile_bounds)
                else:
                    w_lower, w_upper = lower, upper
                bounds_lower.loc[idx] = w_lower
                bounds_upper.loc[idx] = w_upper
                
                if name not in thresholds_report:
                    thresholds_report[f"{col}_{name}"] = {"lower": float(lower), "upper": float(upper), "method": method, "n_flagged": int(mask.sum())}

                    
        out[flag_col] = col_flags
        any_flag |= col_flags
        
        if col_flags.any():
            findings.append(Finding("P04.OUTLIERS_FLAGGED", "info", f"Outliers in {col}", count=int(col_flags.sum()), column=col))
            
            summary_before_after[col] = {"before_mean": float(out[col].mean()), "before_sd": float(out[col].std())}
            
            # Unit error detection
            if cfg.unit_error_detection and ctx.schema.columns.get(col) and ctx.schema.columns[col].range:
                vmin, vmax = ctx.schema.columns[col].range
                suspect_factors = {}
                for f in cfg.unit_error_factors:
                    test_vals = out.loc[col_flags, col] / f
                    in_range = (test_vals >= vmin) & (test_vals <= vmax)
                    if in_range.any():
                        suspect_factors[f] = int(in_range.sum())
                        if f"flag__p04__suspected_unit_error__{col}" not in out.columns:
                            out[f"flag__p04__suspected_unit_error__{col}"] = False
                        out.loc[in_range[in_range].index, f"flag__p04__suspected_unit_error__{col}"] = True
                if suspect_factors:
                    suspected_unit_factors[col] = suspect_factors
                    findings.append(Finding("P04.SUSPECTED_UNIT_ERROR", "warning", f"Unit error suspected in {col}", count=sum(suspect_factors.values()), column=col))

            
            # Parallel actions
            if "winsorize" in cfg.parallel_actions:
                out[f"{col}__winsorized"] = out[col].clip(lower=bounds_lower, upper=bounds_upper)
            
            # Action
            if cfg.action == "to_na":
                out.loc[col_flags, col] = np.nan
            elif cfg.action == "winsorize":
                out[col] = out[col].clip(lower=bounds_lower, upper=bounds_upper)

                
            summary_before_after[col]["after_mean"] = float(out[col].mean())
            summary_before_after[col]["after_sd"] = float(out[col].std())
            
    out["flag__p04__any"] = any_flag
    
    flag_rate = float(any_flag.mean())
    if flag_rate > cfg.max_flag_rate:
        raise DataQualityError(MODULE_ID, "P04.MAX_FLAG_RATE_EXCEEDED", f"Flag rate {flag_rate:.1%} exceeds {cfg.max_flag_rate:.1%}. Check unit conversions.", details={"rate": flag_rate, "limit": cfg.max_flag_rate})

    if cfg.action == "drop_row" and any_flag.any():
        dropped_idx = out[any_flag].index
        rows_dropped = len(dropped_idx)
        out = out.drop(index=dropped_idx)
        # Add finding about drops
        findings.append(Finding("P04.ROWS_DROPPED", "info", f"Dropped {rows_dropped} rows", count=rows_dropped))

    details = {
        "thresholds": thresholds_report,
        "flag_rate": flag_rate,
        "suspected_unit_factors": suspected_unit_factors,
        "summary_before_after": summary_before_after
    }
    findings.append(Finding(f"{MODULE_ID}.SUMMARY", "info", "Module summary", count=0, details=details))
        
    status = Status.OK_WITH_WARNINGS if flag_rate > 0 or suspected_unit_factors else Status.OK

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
        rows_dropped=rows_dropped,
        rows_flagged=int(out[[c for c in out.columns if c.startswith("flag__")]].any(axis=1).sum()) if any(c.startswith("flag__") for c in out.columns) else 0,
        columns_added=sorted(list(set(out.columns) - set(df.columns))),
        columns_modified=[c for c in df.columns if c in out.columns and not df[c].equals(out[c])],
        params_effective=cfg.model_dump(),
        findings=findings,
        artifacts={},
        context_updates=[]
    )
    
    return StepResult(data=out, report=report)

