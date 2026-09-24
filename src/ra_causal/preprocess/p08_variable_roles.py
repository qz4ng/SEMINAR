import pandas as pd
import numpy as np
from typing import Literal
from pydantic import BaseModel, Field
import time

from ra_causal.core.contracts import StepResult, StepReport, Finding, Status
from ra_causal.core.context import PipelineContext
from ra_causal.core.registry import REGISTRY
from ra_causal.core.errors import ConfigError, ContractError, DependencyError

MODULE_ID = "P08"
MODULE_NAME = "variable_roles"
SPEC_VERSION = "1.0"

class BasisConfig(BaseModel):
    continuous: Literal["linear", "quadratic", "spline"] = "quadratic"
    spline_df: int = 4

class P08Config(BaseModel):
    # xác định vai trò của biến từ schema, danh sách thủ công hoặc dựa trên dữ liệu.
    # Vai trò của biến được xác định dựa trên schema nếu source = "schema_roles",
    #  dựa trên danh sách thủ công nếu source = "manual" 
    #  hoặc dựa trên dữ liệu nếu source = "data_driven".
    source: Literal["schema_roles", "manual", "data_driven"] = "schema_roles"
    allow_data_driven: bool = False
    manual_list: list[str] = Field(default_factory=list)
    include_roles: list[str] = Field(default_factory=lambda: ["confounder"])
    include_precision_vars: bool = True

    # Vai trò của biến
    # Các vai trò có thể được bao gồm trong include_roles hoặc exclude_roles:
    # - confounder: biến gây nhiễu  
    # - mediator: biến trung gian
    # - collider: biến va chạm
    # - instrument: biến công cụ
    # - outcome_predictor: biến dự đoán kết quả
    # - noise: biến nhiễu (có thể có nhiều loại, ví dụ: noise1, noise2, ...)
    # - outcome: biến kết quả
    # - treatment: biến điều trị
    # - treatment_version: biến phiên bản điều trị  
    exclude_roles: list[str] = Field(default_factory=lambda: ["mediator", "collider", "instrument", "noise", "outcome", "treatment", "treatment_version", "id"])
   
    # Các biến có vai trò "ambiguous" (mơ hồ) trong schema có thể được xử lý theo các cách khác nhau:
        # - both: tạo ra hai biến thể của tập điều chỉnh, một biến thể coi các biến mơ hồ là confounder, biến thể kia coi chúng là mediator. Cả hai biến thể sẽ được lưu trong context. (default)
        # - include: coi các biến mơ hồ là confounder và đưa vào tập điều chỉnh.
        # - exclude: loại bỏ các biến mơ hồ khỏi tập điều chỉnh.
    ambiguous_action: Literal["both", "include", "exclude"] = "both"
    basis: BasisConfig = BasisConfig()
    interactions: list[list[str]] = Field(default_factory=lambda: [["country", "*"]])
    rare_level_action: Literal["group", "keep", "drop"] = "group"
    rare_level_threshold: float = 0.01
    min_variation: float = 1e-12

@REGISTRY.register(MODULE_ID, P08Config)
def run(df: pd.DataFrame, cfg: P08Config, ctx: PipelineContext) -> StepResult:
    start_time = time.time()
    out = df.copy()
    findings = []
    
    eligible = ctx.eligible_columns if hasattr(ctx, "eligible_columns") and ctx.eligible_columns else list(out.columns)
    
    if cfg.source == "data_driven" and not cfg.allow_data_driven:
        raise ConfigError(MODULE_ID, "P08.DATA_DRIVEN_USED", "allow_data_driven is false")
        
    variants = {}
    if cfg.source == "manual":
        L = [c for c in cfg.manual_list if c in eligible]
    else:
        L = []
        ambiguous_cols = []
        for col in eligible:
            if col not in ctx.schema.columns:
                continue
            role = ctx.schema.columns[col].dag_role
            if role in cfg.include_roles:
                L.append(col)
            elif cfg.include_precision_vars and role == "outcome_predictor":
                L.append(col)
            elif role == "ambiguous":
                ambiguous_cols.append(col)
                
        if cfg.ambiguous_action == "include":
            L.extend(ambiguous_cols)
        elif cfg.ambiguous_action == "both" and ambiguous_cols:
            variants["O_as_confounder"] = sorted(L + ambiguous_cols)
            variants["O_as_mediator"] = sorted(L)
            L.extend(ambiguous_cols)
            findings.append(Finding("P08.AMBIGUOUS_ROLE", "warning", f"Created variants for {ambiguous_cols}", count=len(ambiguous_cols), details={"ambiguous": ambiguous_cols}))
    # Remove excluded roles
    exclude_roles = set(cfg.exclude_roles)
    L = [c for c in L if ctx.schema.columns.get(c) and ctx.schema.columns[c].dag_role not in exclude_roles]
    L = sorted(list(set(L)))
    
    # Check forbidden (safety net)
    forbidden = []
    for c in out.columns:
        contract = ctx.schema.columns.get(c)
        if contract:
            role = contract.dag_role
            meas_time = contract.measured_at
            if role in ("mediator", "collider", "instrument", "outcome", "treatment", "treatment_version") or role.startswith("noise"):
                forbidden.append(c)
            elif meas_time == "post" and role != "outcome_predictor":
                # Assuming post-treatment predictors can be precision vars
                forbidden.append(c)
                
    for f in forbidden:
        if f in L:
            raise ContractError(MODULE_ID, "P08.FORBIDDEN_COLUMN_IN_L", f"Forbidden column {f} in L")

            
    # Min variation & Rare levels
    final_L = []
    for col in L:
        if col not in out.columns:
            continue
        if pd.api.types.is_numeric_dtype(out[col]) and not pd.api.types.is_bool_dtype(out[col]):
            # var() của cột nullable (Float32/Int16) trả pd.NA khi cột trống hoặc chỉ có
            # một giá trị; so sánh `pd.NA < x` rồi đưa vào `if` sẽ ném
            # "boolean value of NA is ambiguous". Coi như không biến thiên.
            var = out[col].var()
            if pd.isna(var) or var < cfg.min_variation:
                findings.append(Finding("P08.ZERO_VARIANCE_DROPPED", "warning", f"Dropped {col} due to low variance", count=1, column=col))
                continue
        elif isinstance(out[col].dtype, pd.CategoricalDtype) or pd.api.types.is_object_dtype(out[col]):
            if out[col].nunique() <= 1:
                findings.append(Finding("P08.ZERO_VARIANCE_DROPPED", "warning", f"Dropped {col} due to zero variance", count=1, column=col))
                continue
            if cfg.rare_level_action == "group":
                counts = out[col].value_counts(normalize=True)
                rare = counts[counts < cfg.rare_level_threshold].index
                if len(rare) > 0:
                    if isinstance(out[col].dtype, pd.CategoricalDtype):
                        out[col] = out[col].cat.add_categories(["other"])
                    out.loc[out[col].isin(rare), col] = "other"
                    findings.append(Finding("P08.RARE_LEVEL_GROUPED", "info", f"Grouped rare levels in {col}", count=len(rare), column=col))
        final_L.append(col)
        
    L = sorted(final_L)
    findings.append(Finding("P08.ADJUSTMENT_SET_BUILT", "info", f"Built L with {len(L)} columns", count=len(L), details={"columns": L}))
    
    if cfg.source == "data_driven":
        findings.append(Finding("P08.DATA_DRIVEN_USED", "warning", "Data driven variable selection was used", count=0))

    # Data dictionary artifact
    dict_rows = []
    for col in out.columns:
        if col in ctx.schema.columns:
            contract = ctx.schema.columns[col]
            dict_rows.append({
                "column": col,
                "dtype": contract.dtype,
                "measured_at": contract.measured_at,
                "affected_by_treatment": contract.affected_by_treatment,
                "dag_role": contract.dag_role,
                "in_L": col in L,
                "variant_membership": [k for k, v in variants.items() if col in v] if variants else [],
                "reason": ""
            })
    data_dict = pd.DataFrame(dict_rows)
    ps_basis_spec = {
        "basis": cfg.basis.model_dump(),
        "interactions": cfg.interactions
    }
    
    status = Status.OK_WITH_WARNINGS if any(f.severity in ("warning", "error") for f in findings) else Status.OK

    details = {
        "ps_basis_spec": ps_basis_spec
    }
    findings.append(Finding(f"{MODULE_ID}.SUMMARY", "info", "Module summary", count=0, details=details))

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
        artifacts={"data_dictionary": "data_dictionary.csv"},
        context_updates=["adjustment_set", "adjustment_set_variants", "ps_basis_spec"]
    )
    
    return StepResult(data=out, report=report, artifacts={"data_dictionary": data_dict}, context_updates={"adjustment_set": L, "adjustment_set_variants": variants, "ps_basis_spec": ps_basis_spec})


