import pandas as pd
import numpy as np
from typing import Literal
from pydantic import BaseModel
import time
from sklearn.model_selection import StratifiedGroupKFold, GroupKFold

from ra_causal.core.contracts import StepResult, StepReport, Finding, Status
from ra_causal.core.context import PipelineContext
from ra_causal.core.registry import REGISTRY
from ra_causal.core.errors import ContractError

MODULE_ID = "P09"
MODULE_NAME = "clusters"
SPEC_VERSION = "1.0"

class P09Config(BaseModel):
    # Danh sách các cột để xác định cluster. Nếu nhiều cột được chỉ định, chúng sẽ được nối lại để tạo ra một khóa cluster duy nhất.
    # Nếu một mẫu có giá trị NaN trong bất kỳ cột nào được chỉ định, nó sẽ được gán cho một cluster riêng biệt (singleton).
    cluster_key: list[str] = ["grower_id"]

    # Xác định cách chia dữ liệu thành các fold cho cross-validation. Các tùy chọn:
    # - group_stratified: chia dữ liệu thành các fold sao cho mỗi fold có phân phối nhãn điều trị tương tự và không chia sẻ cluster giữa các fold.
    # - group: chia dữ liệu thành các fold sao cho không chia sẻ cluster giữa các fold, nhưng không đảm bảo phân phối nhãn điều trị.
    # - random: chia dữ liệu thành các fold ngẫu nhiên mà không quan tâm đến cluster hoặc phân phối nhãn điều trị.
    fold_strategy: Literal["group_stratified", "group", "random"] = "group_stratified"
    n_folds: int = 5
    seed: int = 20260921
    # Xác định cách xử lý các mẫu có năm (year) trong quá trình chia fold.
    # Các tùy chọn:
    # - fixed_effect: coi năm là hiệu ứng cố định, không chia fold theo năm
    # - second_cluster: coi năm là một cluster thứ hai, đảm bảo rằng các mẫu cùng năm không được chia vào các fold khác nhau
    # - ignore: bỏ qua năm trong quá trình chia fold, có thể dẫn đến việc các mẫu cùng năm được chia vào các fold khác
    year_handling: Literal["fixed_effect", "second_cluster", "ignore"] = "fixed_effect"
    large_cluster_warn: float = 0.05
    compute_icc: bool = True

@REGISTRY.register(MODULE_ID, P09Config)
def run(df: pd.DataFrame, cfg: P09Config, ctx: PipelineContext) -> StepResult:
    start_time = time.time()
    out = df.copy()
    findings = []
    
    # 1. cluster_id
    if len(cfg.cluster_key) == 1 and cfg.cluster_key[0] in out.columns:
        c_key = out[cfg.cluster_key[0]]
    else:
        # Simplification: join keys
        c_key = out[cfg.cluster_key].astype(str).agg('-'.join, axis=1)
        
    out["cluster_id"] = c_key.astype(str)
    
    # Missing cluster key
    if out["cluster_id"].isna().any() or (out["cluster_id"] == "nan").any():
        idx = out["cluster_id"].isna() | (out["cluster_id"] == "nan")
        if "record_id" in out.columns:
            out.loc[idx, "cluster_id"] = "singleton__" + out.loc[idx, "record_id"].astype(str)
        else:
            out.loc[idx, "cluster_id"] = "singleton__" + pd.Series(out.index[idx]).astype(str)
        findings.append(Finding("P09.MISSING_CLUSTER_KEY", "warning", "Missing cluster key", count=int(idx.sum())))
        
    # 2. Statistics
    cluster_counts = out["cluster_id"].value_counts()
    n_clusters = len(cluster_counts)
    
    large = cluster_counts[cluster_counts / len(out) > cfg.large_cluster_warn]
    if not large.empty:
        findings.append(Finding("P09.LARGE_CLUSTER", "warning", f"Large clusters found > {cfg.large_cluster_warn}", count=len(large)))
        
    # 3. Folds
    out["fold_id"] = -1
    A = ctx.treatment_column if hasattr(ctx, "treatment_column") else "cover_crop"
    
    if A in out.columns:
        valid_idx = out[out[A].notna()].index
        
        null_a = out[A].isna().sum()
        if null_a > 0:
            findings.append(Finding("P09.MISSING_TREATMENT", "info", "Missing treatment values assigned to fold -1", count=int(null_a)))
            
        if len(valid_idx) > 0:
            y_valid = out.loc[valid_idx, A].astype(int)
            groups_valid = out.loc[valid_idx, "cluster_id"]
            
            n_clusters_valid = groups_valid.nunique()
            class_counts = y_valid.value_counts()
            
            use_stratified = cfg.fold_strategy == "group_stratified"
            
            if use_stratified:
                if n_clusters_valid < cfg.n_folds:
                    findings.append(Finding("P09.FALLBACK_TO_GROUP_KFOLD", "warning", f"n_clusters ({n_clusters_valid}) < n_folds ({cfg.n_folds})", count=0))
                    use_stratified = False
                elif class_counts.min() < cfg.n_folds:
                    findings.append(Finding("P09.FALLBACK_TO_GROUP_KFOLD", "warning", f"min class samples ({class_counts.min()}) < n_folds ({cfg.n_folds})", count=0))
                    use_stratified = False
                    
            # Seed lấy TRỰC TIẾP từ cfg.seed, không rút từ ctx.rng: ctx.rng tiến trạng thái
            # sau mỗi lần gọi, nên chạy lại module sẽ cho cách chia fold khác — vi phạm
            # yêu cầu "chạy lại không đổi". Fold phải ổn định theo config, không theo lịch sử gọi.
            rng_seed = int(np.random.default_rng(cfg.seed).integers(0, 2**31 - 1))
            
            if use_stratified:
                cv = StratifiedGroupKFold(n_splits=cfg.n_folds, shuffle=True, random_state=rng_seed)
                for fold, (_, test_idx) in enumerate(cv.split(out.loc[valid_idx], y_valid, groups_valid)):
                    out.loc[valid_idx[test_idx], "fold_id"] = fold
            else:
                cv = GroupKFold(n_splits=cfg.n_folds)
                for fold, (_, test_idx) in enumerate(cv.split(out.loc[valid_idx], groups=groups_valid)):
                    out.loc[valid_idx[test_idx], "fold_id"] = fold
    # 4. Post condition
    fold_by_cluster = out[out["fold_id"] >= 0].groupby("cluster_id")["fold_id"].nunique()
    if (fold_by_cluster > 1).any():
        raise ContractError(MODULE_ID, "P09.CLUSTER_SPLIT_ACROSS_FOLDS", "Cluster split across folds")
        
    # 5. ICC
    icc = None
    if cfg.compute_icc and "yield_t_ha" in out.columns:
        y = out[["cluster_id", "yield_t_ha"]].dropna()
        if not y.empty:
            group_means = y.groupby("cluster_id")["yield_t_ha"].mean()
            global_mean = y["yield_t_ha"].mean()
            n_c = y.groupby("cluster_id").size()
            
            var_between = ((group_means - global_mean)**2 * n_c).sum() / (n_clusters - 1) if n_clusters > 1 else 0
            var_within = ((y["yield_t_ha"] - y["cluster_id"].map(group_means))**2).sum() / (len(y) - n_clusters) if len(y) > n_clusters else 0
            
            if var_between + var_within > 0:
                icc = var_between / (var_between + var_within)
                findings.append(Finding("P09.ICC_ESTIMATE", "info", f"ICC = {icc:.3f}", count=0, details={"icc": icc}))

    findings.append(Finding("P09.CLUSTER_SUMMARY", "info", f"Clusters: {n_clusters}", count=n_clusters))

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
        artifacts={},
        context_updates=["cluster_column", "fold_column", "year_handling"]
    )
    
    return StepResult(data=out, report=report, context_updates={"cluster_column": "cluster_id", "fold_column": "fold_id", "year_handling": cfg.year_handling})

