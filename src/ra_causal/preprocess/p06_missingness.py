import pandas as pd
import numpy as np
from typing import Literal
from pydantic import BaseModel, Field
import time

from ra_causal.core.contracts import StepResult, StepReport, Finding, Status
from ra_causal.core.context import PipelineContext
from ra_causal.core.registry import REGISTRY
from ra_causal.core.errors import DependencyError

MODULE_ID = "P06"
MODULE_NAME = "missingness"
SPEC_VERSION = "1.0"

class P06Config(BaseModel):
    # Xác định cách xử lý dữ liệu bị thiếu trong tập dữ liệu. Các chế độ:
    # - adjustment_set_plus_ay: chỉ xem xét các cột trong tập điều chỉnh cộng với biến điều trị và biến kết quả
    # - all_columns: xem xét tất cả các cột trong tập dữ liệu
    scope: Literal["adjustment_set_plus_ay", "all_columns"] = "adjustment_set_plus_ay"

    # Xác định cách xử lý dữ liệu bị thiếu trong biến kết quả và biến điều trị. Các chế độ:
    # - ipcw_flag: tạo cột cờ cho các mẫu có biến kết quả bị thiếu (default)
    # - complete_case: loại bỏ các mẫu có biến kết quả bị thiếu
    # - both: tạo cột cờ cho các mẫu có biến kết quả bị thiếu
    outcome_missing: Literal["ipcw_flag", "complete_case", "both"] = "ipcw_flag"

    # Xác định cách xử lý dữ liệu bị thiếu trong các biến điều chỉnh. Các chế độ:
    # - median_indicator: điền giá trị trung vị (hoặc mode cho biến phân loại) và tạo cột cờ cho các mẫu được điền (default)
    # - drop_row: loại bỏ các mẫu có bất kỳ biến điều chỉnh nào bị thiếu
    # - category_missing: điền giá trị "Missing" cho các biến phân loại bị thiếu và tạo cột cờ cho các mẫu được điền (không được triển khai trong mã hiện tại)

    covariate_missing: Literal["median_indicator", "drop_row", "category_missing"] = "median_indicator"
    
    # Xác định cách nhóm các mẫu để điền giá trị trung vị/mode. Các chế độ:
    # - country: nhóm theo quốc gia (default)
    # - country_treatment: nhóm theo quốc gia và biến điều trị
    impute_group_by: list[str] = Field(default_factory=lambda: ["country"])

    # Xác định kích thước nhóm tối thiểu để điền giá trị trung vị/mode. 
    # Nếu nhóm nhỏ hơn kích thước này, sử dụng giá trị trung vị/mode toàn cục
    min_group_size: int = 30
    keep_indicator: bool = True

    # Xác định ngưỡng tối đa cho tỷ lệ dữ liệu bị thiếu trong một cột. Nếu tỷ lệ dữ liệu bị thiếu vượt quá ngưỡng này, cột sẽ bị loại bỏ khỏi tập điều chỉnh.
    # Các cột bị loại bỏ sẽ được ghi lại trong báo cáo.
    max_missing_col: float = 0.40
    # Xác định các phương pháp kiểm tra cơ chế dữ liệu bị thiếu. Các phương pháp:
    # - describe: mô tả tỷ lệ dữ liệu bị thiếu theo cột, quốc gia và biến điều trị (default)
    # - regress: hồi quy nhị phân để kiểm tra xem cơ chế dữ liệu bị thiếu có phụ thuộc vào các biến điều chỉnh và biến điều trị
    mechanism_check: list[str] = Field(default_factory=lambda: ["describe", "regress"])
    # Xác định ngưỡng cảnh báo cho sự khác biệt về tỷ lệ dữ liệu bị thiếu giữa các nhóm điều trị. Nếu sự khác biệt vượt quá ngưỡng này, sẽ tạo ra một cảnh báo trong báo cáo.
    diff_warn_threshold: float = 0.05

@REGISTRY.register(MODULE_ID, P06Config)
def run(df: pd.DataFrame, cfg: P06Config, ctx: PipelineContext) -> StepResult:
    start_time = time.time()
    out = df.copy()
    findings = []
    
    L = ctx.adjustment_set[:]
        
    treatment = ctx.treatment_column
    outcome = "yield_t_ha"
    
    if cfg.scope == "adjustment_set_plus_ay":
        target_cols = L + [treatment, outcome]
        target_cols = [c for c in target_cols if c in out.columns]
    else:
        target_cols = out.columns
        
    out["c_outcome_observed"] = out[outcome].notna() if outcome in out.columns else True
    missing_by_column = {}
    pattern_counts = []
    
    # Calculate missing by column * country * A
    group_cols = []
    if "country" in out.columns:
        group_cols.append("country")
    if treatment in out.columns:
        group_cols.append(treatment)
        if group_cols and target_cols:
            for c in target_cols:
                if c not in out.columns:
                    continue
                miss_rate = out[c].isna().groupby([out[g] for g in group_cols], observed=True).mean()
                # Convert keys to string for JSON serialization
                missing_by_column[c] = {str(k): float(v) for k, v in miss_rate.to_dict().items()}

            
    # Calculate 10 most common missing patterns
    if target_cols:
        avail_cols = [c for c in target_cols if c in out.columns]
        if avail_cols:
            patterns = out[avail_cols].isna().astype(int).value_counts().head(10)
            pattern_counts = [{"pattern": str(k), "count": int(v)} for k, v in patterns.items()]

    imputation_report = {}
    
    # Missingness diff by treatment
    if treatment in out.columns and out[treatment].notna().any():
        for col in target_cols:
            if col != treatment:
                miss_by_a = out[col].isna().groupby(out[treatment], observed=True).mean()
                if len(miss_by_a) == 2:
                    diff = abs(miss_by_a.iloc[0] - miss_by_a.iloc[1])
                    if diff > cfg.diff_warn_threshold:
                        findings.append(Finding("P06.MISSING_DIFFERS_BY_TREATMENT", "warning", f"Missingness in {col} differs by > {cfg.diff_warn_threshold} across treatment", count=int(out[col].isna().sum()), column=col))
                        
    # Structural missing
    if "country" in out.columns:
        for col in target_cols:
            if out[col].isna().any():
                miss_by_c = out[col].isna().groupby(out["country"], observed=True).mean()
                if (miss_by_c == 1.0).any():
                    findings.append(Finding("P06.STRUCTURAL_MISSING", "warning", f"{col} is structurally missing (100%) in some country", count=int(out[col].isna().sum()), column=col))
    
    # Max missing
    cols_to_drop = []
    for col in list(L):
        if col in out.columns:
            rate = out[col].isna().mean()
            if rate > cfg.max_missing_col:
                cols_to_drop.append(col)
                L.remove(col)
                findings.append(Finding("P06.COLUMN_DROPPED_HIGH_MISSING", "warning", f"Dropped {col} from L due to > {cfg.max_missing_col} missing", count=int(out[col].isna().sum()), column=col))
                
    # Impute covariates
    for col in L:
        if col not in out.columns or out[col].notna().all():
            continue
        if cfg.covariate_missing == "median_indicator":
            flag_col = f"flag__p06__imputed__{col}"
            out[flag_col] = out[col].isna()
            
            is_num = pd.api.types.is_numeric_dtype(out[col]) and not pd.api.types.is_bool_dtype(out[col])
            # Cột số nguyên không chứa được trung vị lẻ (ví dụ 20.5 vào Int16):
            # làm tròn về số nguyên gần nhất thay vì để pandas báo lỗi kiểu.
            is_int_col = is_num and pd.api.types.is_integer_dtype(out[col])

            def _fit_dtype(v):
                """Đưa giá trị điền về đúng kiểu của cột."""
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    return v
                return int(round(float(v))) if is_int_col else v

            groups = out.groupby(cfg.impute_group_by, observed=True)
            value_used_by_group = {}

            # Global fallback
            if is_num:
                global_val = _fit_dtype(out[col].median())
            else:
                global_val = out[col].mode()[0] if not out[col].mode().empty else "Missing"
                
            for name, idx in groups.groups.items():
                group_vals = out.loc[idx, col].dropna()
                if len(group_vals) < cfg.min_group_size:
                    val = global_val
                    findings.append(Finding("P06.SMALL_GROUP", "info", f"Group {name} size {len(group_vals)} < {cfg.min_group_size}, using global impute for {col}", count=len(group_vals), column=col))
                else:
                    if is_num:
                        val = _fit_dtype(group_vals.median())
                    else:
                        val = group_vals.mode()[0] if not group_vals.mode().empty else global_val
                
                value_used_by_group[str(name)] = float(val) if is_num else str(val)
                
                if not is_num and isinstance(out[col].dtype, pd.CategoricalDtype) and val not in out[col].cat.categories:
                    out[col] = out[col].cat.add_categories([val])
                    
                out.loc[idx, col] = out.loc[idx, col].fillna(val)
                
            # Fallback for completely missing groups or NaN groups
            if out[col].isna().any():
                if not is_num and isinstance(out[col].dtype, pd.CategoricalDtype) and global_val not in out[col].cat.categories:
                    out[col] = out[col].cat.add_categories([global_val])
                out[col] = out[col].fillna(global_val)
                value_used_by_group["global_fallback"] = float(global_val) if is_num else str(global_val)
                
            imputation_report[col] = {
                "method": "median" if is_num else "mode", 
                "n_imputed": int(out[flag_col].sum()), 
                "value_used_by_group": value_used_by_group
            }

                
            findings.append(Finding("P06.IMPUTED", "info", f"Imputed {col}", count=int(out[flag_col].sum()), column=col))
            if not cfg.keep_indicator:
                out = out.drop(columns=[flag_col])
        elif cfg.covariate_missing == "drop_row":
            # Handled later collectively
            pass
            
    # missing any L for missingness report
    out["flag__p06__missing_any_L"] = out[L].isna().any(axis=1) if L else False
            
    # Outcome missing
    rows_dropped = 0
    if outcome in out.columns:
        n_missing_y = out[outcome].isna().sum()
        findings.append(Finding("P06.OUTCOME_MISSING_RATE", "info", f"Outcome missing rate", count=int(n_missing_y), column=outcome))
        
        if cfg.outcome_missing in ("complete_case", "both"):
            drop_idx = out[out[outcome].isna()].index
            out = out.drop(index=drop_idx)
            rows_dropped += len(drop_idx)
            
    if cfg.covariate_missing == "drop_row":
        drop_idx = out[out[L].isna().any(axis=1)].index if L else []
        if len(drop_idx) > 0:
            out = out.drop(index=drop_idx)
            rows_dropped += len(drop_idx)
    if "describe" in cfg.mechanism_check:
        findings.append(Finding("P06.MISSING_SUMMARY", "info", "Missing summary", count=0))
        
    regression_coefs = {}
    if "regress" in cfg.mechanism_check and outcome in df.columns:
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        import warnings
        
        # We need to regress missingness of Y on L and A
        # using the data *before* dropping Y or L rows, so we use `df` or a copy of `df` with L imputed.
        # Actually `out` has L imputed, but maybe Y is dropped. We'll use `df` for Y missingness and `out` for L imputed.
        # To keep it simple, we just build a matrix from `out` (before Y dropping) if possible, but Y might be dropped already!
        # Wait, the regression is ON outcome_observed_column which we computed early as `c_outcome_observed`.
        
        obs_col = "c_outcome_observed"
        if obs_col in out.columns and L:
            features = L + ([treatment] if treatment in L else [])
            X = out[features].copy()
            y = out[obs_col].astype(int)
            
            # Handle categorical
            X = pd.get_dummies(X, drop_first=True)
            
            # Standardize numeric
            for c in X.columns:
                if pd.api.types.is_numeric_dtype(X[c]) and not pd.api.types.is_bool_dtype(X[c]):
                    X[c] = StandardScaler().fit_transform(X[[c]])
            if not X.isna().any().any() and len(y.unique()) > 1:
                with warnings.catch_warnings():

                    warnings.simplefilter("ignore")
                    model = LogisticRegression(max_iter=1000)
                    model.fit(X, y)
                    coefs = pd.Series(model.coef_[0], index=X.columns)
                    coefs = coefs.reindex(coefs.abs().sort_values(ascending=False).index).head(10)
                    regression_coefs = coefs.to_dict()
                    findings.append(Finding("P06.MECHANISM_REGRESS", "info", f"Top missingness predictors: {list(regression_coefs.keys())}", count=0))
    details = {
        "imputation": imputation_report,
        "regression_coefs": regression_coefs,
        "missing_by_column": missing_by_column,
        "pattern_counts": pattern_counts


    }
    findings.append(Finding(f"{MODULE_ID}.SUMMARY", "info", "Module summary", count=0, details=details))
        
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
        rows_dropped=rows_dropped,
        rows_flagged=int(out[[c for c in out.columns if c.startswith("flag__")]].any(axis=1).sum()) if any(c.startswith("flag__") for c in out.columns) else 0,
        columns_added=sorted(list(set(out.columns) - set(df.columns))),
        columns_modified=[c for c in df.columns if c in out.columns and not df[c].equals(out[c])],
        params_effective=cfg.model_dump(),
        findings=findings,
        artifacts={},
        context_updates=["adjustment_set", "outcome_observed_column"]
    )
    
    return StepResult(data=out, report=report, context_updates={"adjustment_set": L, "outcome_observed_column": "c_outcome_observed"})


# I'll just append it? No, I need to insert it before details.
