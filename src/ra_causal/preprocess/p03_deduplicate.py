import hashlib

import pandas as pd
import numpy as np
from typing import Literal, Any, Optional
from pydantic import BaseModel, Field
import time

from ra_causal.core.contracts import StepResult, StepReport, Finding, Status
from ra_causal.core.context import PipelineContext
from ra_causal.core.registry import REGISTRY
from ra_causal.core.errors import ConfigError, ContractError

MODULE_ID = "P03"
MODULE_NAME = "deduplicate"
SPEC_VERSION = "1.0"

class P03Config(BaseModel):
    # Các cột dùng để xác định nhóm trùng lặp. Các cột này phải tồn tại trong dữ liệu đầu vào.
    #  Nếu có NaN trong các cột này thì sẽ được coi là không hợp lệ.
    key: list[str] = Field(default_factory=lambda: ["grower_id", "field_id", "year"])
    # Cách xử lý các bản ghi trùng lặp: "keep_most_complete" giữ bản ghi có ít NaN nhất, "keep_first" giữ bản ghi đầu tiên, "keep_last" giữ bản ghi cuối cùng (cần timestamp_column), "aggregate" gộp các bản ghi thành một bản ghi tổng hợp, "flag_only" chỉ đánh dấu mà không xóa.
    resolve: Literal["keep_most_complete", "keep_first", "keep_last", "aggregate", "flag_only"] = "keep_most_complete"
    timestamp_column: Optional[str] = None
    # Cách xử lý các bản ghi trùng lặp có xung đột: "review_list" đưa vào danh sách cần xem xét, "drop_group" loại bỏ cả nhóm, "resolve" áp dụng quy tắc resolve.2
    conflict_action: Literal["review_list", "drop_group", "resolve"] = "review_list"
    critical_columns: list[str] = Field(default_factory=lambda: ["cover_crop", "yield_t_ha", "country", "year"])
    numeric_tolerance: float = 1e-8
    aggregate_rules: dict[str, str] = Field(default_factory=lambda: {"numeric": "mean", "categorical": "mode", "boolean": "max"})

@REGISTRY.register(MODULE_ID, P03Config)
def run(df: pd.DataFrame, cfg: P03Config, ctx: PipelineContext) -> StepResult:
    start_time = time.time()
    out = df.copy()
    findings = []
    artifacts = {}
    
    if cfg.resolve == "keep_last" and not cfg.timestamp_column:
        raise ConfigError(MODULE_ID, "P03.CONFIG_ERROR", "timestamp_column required for keep_last")
        
    # Giữ lại dấu vết của lần chạy trước nếu có: "dòng này từng thuộc một nhóm trùng đã
    # được gộp" là thông tin lịch sử, chạy lại module trên dữ liệu đã gộp không thể suy ra
    # được nữa. Không giữ thì module mất tính "chạy lại không đổi".
    for col, default in (("dup_group_id", "NA"), ("flag__p03__duplicate", False), ("flag__p03__conflict", False)):
        if col not in out.columns:
            out[col] = default
    
    # Check for NaN in keys
    null_keys = out[cfg.key].isna().any(axis=1)
    if null_keys.any():
        findings.append(Finding("P03.NULL_KEY", "warning", "NaN in key columns", count=int(null_keys.sum())))
        
    # Group by key
    groups = out[~null_keys].groupby(cfg.key, dropna=False, observed=True)
    
    groups_by_type = {"exact": 0, "partial": 0, "conflict": 0}
    conflict_cols_freq = {}
    
    rows_to_drop = []
    review_list_indices = []
    
    group_idx = 1
    
    canonical_cols = list(ctx.schema.columns.keys())
    
    for key_val, idx in groups.groups.items():
        if len(idx) < 2:
            continue
            
        group_df = out.loc[idx]
        # Mã nhóm suy ra TỪ CHÍNH KHÓA, không đánh số theo thứ tự gặp: nếu đánh số
        # theo thứ tự thì chạy lại module (khi vài nhóm đã được gộp) sẽ đổi hết mã.
        key_repr = "|".join(str(v) for v in (key_val if isinstance(key_val, tuple) else (key_val,)))
        out.loc[idx, "dup_group_id"] = "g" + hashlib.sha1(key_repr.encode("utf-8")).hexdigest()[:6]
        out.loc[idx, "flag__p03__duplicate"] = True
        group_idx += 1
        
        # Compare columns
        diff_cols = []
        for col in canonical_cols:
            if col in group_df.columns:
                series = group_df[col]
                if pd.api.types.is_bool_dtype(series):
                    if series.dropna().nunique() > 1:
                        diff_cols.append(col)
                    elif series.isna().any() and series.notna().any():
                        diff_cols.append(col)
                elif pd.api.types.is_numeric_dtype(series):
                    non_na = series.dropna()
                    if len(non_na) > 0 and (non_na.max() - non_na.min()) > cfg.numeric_tolerance:
                        diff_cols.append(col)
                    elif series.isna().any() and series.notna().any():
                        diff_cols.append(col)
                else:
                    if series.dropna().nunique() > 1:
                        diff_cols.append(col)
                    elif series.isna().any() and series.notna().any():
                        diff_cols.append(col)
                        
        is_conflict = any(c in cfg.critical_columns for c in diff_cols)
        
        if len(diff_cols) == 0:
            groups_by_type["exact"] += 1
        elif is_conflict:
            groups_by_type["conflict"] += 1
            out.loc[idx, "flag__p03__conflict"] = True
            for c in diff_cols:
                if c in cfg.critical_columns:
                    conflict_cols_freq[c] = conflict_cols_freq.get(c, 0) + 1
        else:
            groups_by_type["partial"] += 1
            
        # Resolve
        if is_conflict and cfg.conflict_action == "review_list":
            review_list_indices.extend(idx)
            continue
        elif is_conflict and cfg.conflict_action == "drop_group":
            rows_to_drop.extend(idx)
            continue
            
        if cfg.resolve == "flag_only":
            continue
            
        # keep_most_complete
        if cfg.resolve == "keep_most_complete":
            na_counts = group_df[canonical_cols].isna().sum(axis=1)
            min_na = na_counts.min()
            best_idx = na_counts[na_counts == min_na].index
            if len(best_idx) > 1 and "record_id" in group_df.columns:
                best_idx = [group_df.loc[best_idx].sort_values("record_id").index[0]]
            
            to_drop = [i for i in idx if i != best_idx[0]]
            rows_to_drop.extend(to_drop)
        elif cfg.resolve == "keep_first":
            rows_to_drop.extend(idx[1:])
        elif cfg.resolve == "keep_last":
            sorted_idx = group_df.sort_values(cfg.timestamp_column).index
            rows_to_drop.extend(sorted_idx[:-1])
        elif cfg.resolve == "aggregate":
            na_counts = group_df[canonical_cols].isna().sum(axis=1)
            min_na = na_counts.min()
            best_idx = na_counts[na_counts == min_na].index
            if len(best_idx) > 1 and "record_id" in group_df.columns:
                best_idx = [group_df.loc[best_idx].sort_values("record_id").index[0]]
            best_idx = best_idx[0]
            
            agg_row = group_df.loc[best_idx].copy()
            for col in canonical_cols:
                if col not in group_df.columns or col == "record_id":
                    continue
                series = group_df[col]
                if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
                    if cfg.aggregate_rules.get("numeric", "mean") == "mean":
                        agg_row[col] = series.mean()
                elif pd.api.types.is_bool_dtype(series):
                    if cfg.aggregate_rules.get("boolean", "max") == "max":
                        agg_row[col] = series.max()
                else:
                    if cfg.aggregate_rules.get("categorical", "mode") == "mode":
                        mode_vals = series.mode()
                        if not mode_vals.empty:
                            agg_row[col] = mode_vals.sort_values().iloc[0]
                            
            if "flag__p03__aggregated" not in out.columns:
                out["flag__p03__aggregated"] = False
            
            out.loc[best_idx] = agg_row
            out.loc[best_idx, "flag__p03__aggregated"] = True
            
            to_drop = [i for i in idx if i != best_idx]
            rows_to_drop.extend(to_drop)
    if review_list_indices:
        rev_df = out.loc[review_list_indices].copy()
        artifacts["review_list"] = rev_df
        
    if rows_to_drop:
        out = out.drop(index=rows_to_drop)
        
    # Check post-condition
    if cfg.resolve != "flag_only" and cfg.conflict_action != "review_list":
        if out["record_id"].duplicated().any():
            raise ContractError(MODULE_ID, "P03.KEY_NOT_UNIQUE_AFTER_RESOLVE", "Duplicate record_id remains")

    if groups_by_type["exact"] > 0:
        findings.append(Finding("P03.EXACT_DUPLICATES", "info", "Exact duplicates found", count=groups_by_type["exact"]))
    if groups_by_type["partial"] > 0:
        findings.append(Finding("P03.PARTIAL_DUPLICATES", "warning", "Partial duplicates found", count=groups_by_type["partial"]))
    if groups_by_type["conflict"] > 0:
        findings.append(Finding("P03.CONFLICTING_DUPLICATES", "error", "Conflicting duplicates found", count=groups_by_type["conflict"]))

    details = {
        "groups_by_type": groups_by_type,
        "rows_removed": len(rows_to_drop),
        "conflict_columns_frequency": conflict_cols_freq
    }
    findings.append(Finding(f"{MODULE_ID}.SUMMARY", "info", "Module summary", count=0, details=details))

    status = Status.OK_WITH_WARNINGS if groups_by_type["partial"] > 0 or groups_by_type["conflict"] > 0 else Status.OK
    
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
        rows_dropped=len(rows_to_drop),
        rows_flagged=int(out[[c for c in out.columns if c.startswith("flag__")]].any(axis=1).sum()) if any(c.startswith("flag__") for c in out.columns) else 0,
        columns_added=sorted(list(set(out.columns) - set(df.columns))),
        columns_modified=[c for c in df.columns if c in out.columns and not df[c].equals(out[c])],
        params_effective=cfg.model_dump(),
        findings=findings,
        artifacts={k: f"{k}.parquet" for k in artifacts.keys()},
        context_updates=["duplicate_groups"]
    )
    
    return StepResult(data=out, report=report, artifacts=artifacts, context_updates={"duplicate_groups": sum(groups_by_type.values())})

