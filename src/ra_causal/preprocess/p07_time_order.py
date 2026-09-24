import pandas as pd
import numpy as np
from typing import Literal
from pydantic import BaseModel
import time

from ra_causal.core.contracts import StepResult, StepReport, Finding, Status, SYSTEM_COLUMNS
from ra_causal.core.context import PipelineContext
from ra_causal.core.registry import REGISTRY
from ra_causal.core.errors import ContractError

MODULE_ID = "P07"
MODULE_NAME = "time_order"
SPEC_VERSION = "1.0"

class P07Config(BaseModel):
    # Xác định cách xác định thời điểm đo của các biến trong dữ liệu.
    # Các tùy chọn:
    # - schema: sử dụng thông tin từ schema (default)
    # - name_suffix: sử dụng hậu tố tên cột (_post) để xác định
    # - both: sử dụng cả schema và hậu tố tên cột, ưu tiên schema
    time_source: Literal["schema", "name_suffix", "both"] = "schema"

    # Xử lý các cột không có trong schema (không xác định được thời điểm đo). Các tùy chọn:
    # - exclude: loại bỏ khỏi tập điều chỉnh (default)
    # - include: giữ lại trong tập điều chỉnh
    # - raise: ném lỗi và dừng pipeline
    unknown_action: Literal["exclude", "include", "raise"] = "exclude"
    strict: bool = True
    allow_post_precision_vars: bool = False
    allow_post_as_secondary_outcome: bool = True
    diagnostics_on_post_vars: bool = True

@REGISTRY.register(MODULE_ID, P07Config)
def run(df: pd.DataFrame, cfg: P07Config, ctx: PipelineContext) -> StepResult:
    start_time = time.time()
    out = df.copy()
    findings = []
    
    eligible = []
    blocked_post = []
    blocked_unknown = []
    precision_post = []
    
    column_time_table = []
    
    for col in out.columns:
        if col.startswith("flag__") or col in SYSTEM_COLUMNS:
            continue

        if col not in ctx.schema.columns:
            # Cột có trong dữ liệu nhưng KHÔNG khai trong schema: không biết đo lúc nào,
            # nên mặc định phải coi là không rõ thời điểm và xử lý theo unknown_action.
            # Bỏ qua im lặng sẽ để lọt một biến đo sau can thiệp vào tập điều chỉnh.
            if cfg.unknown_action == "raise":
                raise ContractError(MODULE_ID, "P07.UNKNOWN_TIMING",
                                    f"Cột '{col}' không có trong schema nên không xác định được thời điểm đo")
            if cfg.unknown_action == "include":
                eligible.append(col)
                is_eligible = True
            else:
                blocked_unknown.append(col)
                is_eligible = False
            findings.append(Finding("P07.UNKNOWN_TIMING", "warning",
                                    f"Cột '{col}' không khai trong schema, coi như không rõ thời điểm đo",
                                    count=1, column=col))
            column_time_table.append({
                "column": col, "measured_at": "unknown", "affected_by_treatment": None,
                "dag_role": "unknown", "eligible": is_eligible, "reason": "không có trong schema",
            })
            continue

        contract = ctx.schema.columns[col]
        measured_at = contract.measured_at
        
        has_post_suffix = col.endswith("_post")
        if cfg.time_source == "name_suffix":
            measured_at = "post" if has_post_suffix else "pre"
        elif cfg.time_source == "both":
            schema_is_post = (measured_at == "post")
            if schema_is_post != has_post_suffix:
                findings.append(Finding("P07.TIME_SOURCE_CONFLICT", "warning", f"Conflict in time source for {col}: schema={measured_at}, suffix={'post' if has_post_suffix else 'pre'}", count=1, column=col))
                # prioritize schema
            
        affected = contract.affected_by_treatment
        role = contract.dag_role
        
        is_eligible = False
        reason = ""
        
        if measured_at in ("pre", "at"):
            is_eligible = True
            eligible.append(col)
        elif measured_at == "post":
            if role == "outcome" and cfg.allow_post_as_secondary_outcome:
                is_eligible = True
                eligible.append(col)
                reason = "allowed secondary outcome"
                findings.append(Finding("P07.SECONDARY_OUTCOME_ALLOWED", "info", f"Allowed post-treatment outcome: {col}", count=1, column=col))
            elif affected is False:
                if cfg.allow_post_precision_vars:
                    is_eligible = True
                    precision_post.append(col)
                    reason = "allowed precision_post"
                    findings.append(Finding("P07.PRECISION_VAR_ALLOWED", "warning", f"Allowed post-treatment precision var: {col}", count=1, column=col))
                else:
                    blocked_post.append(col)
                    reason = "post-treatment precision"
            else:
                blocked_post.append(col)
                reason = "post-treatment affected"
        else: # unknown
            if cfg.unknown_action == "include":
                is_eligible = True
                eligible.append(col)
            elif cfg.unknown_action == "exclude":
                blocked_unknown.append(col)
            elif cfg.unknown_action == "raise":
                raise ContractError(MODULE_ID, "P07.UNKNOWN_TIMING", f"Column {col} has unknown timing")
                
        if col in blocked_post:
            findings.append(Finding("P07.BLOCKED_POST_TREATMENT", "info", f"Blocked post var {col}", count=1, column=col))
        if col in blocked_unknown:
            findings.append(Finding("P07.UNKNOWN_TIMING", "warning", f"Blocked unknown timing {col}", count=1, column=col))
            
        column_time_table.append({
            "column": col,
            "measured_at": measured_at,
            "affected_by_treatment": affected,
            "dag_role": role,
            "eligible": is_eligible,
            "reason": reason
        })
        
    blocked = blocked_post + blocked_unknown
    if not cfg.allow_post_precision_vars:
        blocked += precision_post
        
    eligible = sorted(eligible + (precision_post if cfg.allow_post_precision_vars else []))
    blocked = sorted(blocked)
        # Post-conditions
    must_block = ["soil_om_post_pct", "weed_pressure", "in_program"]
    if not cfg.allow_post_as_secondary_outcome:
        must_block.append("yield_t_ha")

    for mb in must_block:
        if mb in out.columns and mb not in blocked:
            if cfg.strict:
                raise ContractError(MODULE_ID, "P07.POST_VAR_NOT_BLOCKED", f"Must block {mb}")
            else:
                findings.append(Finding("P07.POST_VAR_NOT_BLOCKED", "error", f"Must block {mb}", count=1, column=mb))

    if cfg.diagnostics_on_post_vars and ctx.treatment_column in out.columns:
        # just for report
        pass
        
    status = Status.OK_WITH_WARNINGS if any(f.severity in ("warning", "error") for f in findings) else Status.OK

    details = {
        "column_time_table": column_time_table
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
        rows_flagged=0,
        columns_added=[],
        columns_modified=[],
        params_effective=cfg.model_dump(),
        findings=findings,
        artifacts={},
        context_updates=["blocked_columns", "eligible_columns"]
    )
    
    return StepResult(data=out, report=report, context_updates={"blocked_columns": blocked, "eligible_columns": eligible})

