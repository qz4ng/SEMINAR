"""
Các hàm tính toán của các phương pháp được sử dụng:
1. Naive
2. OLS
3. IPTW
4. AIPW
Input: (pd.DataFrame) gồm [X], A, Y và (tuỳ chọn) e(X)
Output: ATE của từng phương pháp ước lượng
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple
from .balance import _validate_trim, check_groups, infer_covariates, overlap_mask

import numpy as np
import pandas as pd
# Lọc biến nhiễu nếu không đề cập
from .balance import infer_covariates


# ----------------------------------------------------------------------
# Tiện ích
# ----------------------------------------------------------------------
def _design(df: pd.DataFrame, covariates: Sequence[str]) -> np.ndarray:
    """Ma trận thiết kế có cột chặn."""
    x = df[list(covariates)].to_numpy(dtype=float)
    return np.column_stack([np.ones(len(df)), x])
 
 
def _ols_fit(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta
 
 
def estimate_ps(
    df: pd.DataFrame,
    covariates: Optional[Sequence[str]] = None,
    treatment: str = "A",
    max_iter: int = 100,
    ridge: float = 1e-8,
) -> np.ndarray:
    """
    Ước lượng propensity score bằng hồi quy logistic (IRLS, chỉ dùng numpy).
    :return: mảng e_hat độ dài n
    """
    covariates = list(covariates) if covariates is not None else infer_covariates(df, treatment)
    X = _design(df, covariates)
    a = df[treatment].to_numpy(dtype=float)
    beta = np.zeros(X.shape[1])
    for _ in range(max_iter):
        p = 1.0 / (1.0 + np.exp(-np.clip(X @ beta, -30, 30)))
        w = np.clip(p * (1 - p), 1e-10, None)
        grad = X.T @ (a - p) - ridge * beta
        hess = X.T @ (X * w[:, None]) + ridge * np.eye(X.shape[1])
        step = np.linalg.solve(hess, grad)
        step = np.clip(step, -5, 5)  # tránh bước quá lớn khi gần tách hoàn toàn
        beta = beta + step
        if np.max(np.abs(step)) < 1e-8:
            break
    return 1.0 / (1.0 + np.exp(-np.clip(X @ beta, -30, 30)))
 
 
def _prepare(
    df: pd.DataFrame,
    covariates: Sequence[str],
    treatment: str,
    ps: str,
    use_estimated_ps: bool,
    trim: Optional[float],
    trim_mode: str,
) -> Tuple[pd.DataFrame, np.ndarray]:
    """
    Lấy e(X) (thật hoặc ước lượng trên TOÀN mẫu) rồi áp dụng trimming.
    :return: (d, e) - d là DataFrame dùng để ước lượng (đã loại quan sát nếu trim_mode="drop"),
             e là propensity score tương ứng từng dòng của d.
    """
    _validate_trim(trim, trim_mode)
    check_groups(df, treatment)
    e = estimate_ps(df, covariates, treatment) if use_estimated_ps else df[ps].to_numpy(dtype=float)
    d = df
    if trim is not None:
        if trim_mode == "drop":
            keep = overlap_mask(e, trim)
            d, e = df[keep], e[keep]
            n1, n0 = int((d[treatment] == 1).sum()), int((d[treatment] == 0).sum())
            if n1 == 0 or n0 == 0:
                raise ValueError(
                    f"Sau trimming không còn quan sát nào ở một nhóm (A=1: {n1}, A=0: {n0}). Hãy giảm trim."
                )
        else:
            e = np.clip(e, trim, 1 - trim)
    return d, np.clip(e, 1e-12, 1 - 1e-12)
 
 
def trim_sample(
    df: pd.DataFrame,
    trim: float,
    covariates: Optional[Sequence[str]] = None,
    treatment: str = "A",
    outcome: str = "Y",
    ps: str = "e",
    use_estimated_ps: bool = False,
    trim_mode: str = "drop",
) -> pd.DataFrame:
    """
    Trả về DataFrame sau trimming; cột ps được thay bằng e(X) đã dùng (thật, ước lượng hoặc đã clip).
    Có thể đưa thẳng vào check_balance, effective_sample_size hoặc các hàm ước lượng với trim=None.
    """
    covariates = list(covariates) if covariates is not None else infer_covariates(df, treatment, outcome, ps)
    d, e = _prepare(df, covariates, treatment, ps, use_estimated_ps, trim, trim_mode)
    return d.assign(**{ps: e})
 
 
# ----------------------------------------------------------------------
# 4 phương pháp ước lượng ATE
# ----------------------------------------------------------------------
def naive(df: pd.DataFrame, treatment: str = "A", outcome: str = "Y") -> float:
    """Naive: chênh lệch trung bình Y giữa nhóm A=1 và A=0 (bỏ qua nhiễu)."""
    check_groups(df, treatment)
    a, y = df[treatment].to_numpy(), df[outcome].to_numpy(dtype=float)
    return float(y[a == 1].mean() - y[a == 0].mean())
 
 
def ols(
    df: pd.DataFrame,
    covariates: Optional[Sequence[str]] = None,
    treatment: str = "A",
    outcome: str = "Y",
) -> float:
    """OLS hiệu chỉnh: hệ số của A trong hồi quy Y ~ 1 + A + X."""
    check_groups(df, treatment)
    covariates = list(covariates) if covariates is not None else infer_covariates(df, treatment, outcome)
    X = np.column_stack([np.ones(len(df)), df[treatment].to_numpy(dtype=float), df[covariates].to_numpy(dtype=float)])
    beta = _ols_fit(X, df[outcome].to_numpy(dtype=float))
    return float(beta[1])
 
 
def iptw(
    df: pd.DataFrame,
    covariates: Optional[Sequence[str]] = None,
    treatment: str = "A",
    outcome: str = "Y",
    ps: str = "e",
    use_estimated_ps: bool = False,
    trim: Optional[float] = None,
    trim_mode: str = "drop",
    normalize: bool = True,
) -> float:
    """
    IPTW cho ATE.
    :param normalize: True -> ước lượng Hajek (chuẩn hóa trọng số, ổn định hơn);
                      False -> Horvitz-Thompson.
    :param trim: giữ e(X) trong [trim, 1-trim]
    :param trim_mode: "drop" = trimming (loại quan sát ngoài vùng); "clip" = clipping
    """
    covariates = list(covariates) if covariates is not None else infer_covariates(df, treatment, outcome, ps)
    d, e = _prepare(df, covariates, treatment, ps, use_estimated_ps, trim, trim_mode)
    a, y = d[treatment].to_numpy(dtype=float), d[outcome].to_numpy(dtype=float)
    w1, w0 = a / e, (1 - a) / (1 - e)
    if normalize:
        return float((w1 * y).sum() / w1.sum() - (w0 * y).sum() / w0.sum())
    return float((w1 * y).mean() - (w0 * y).mean())
 
 
def aipw(
    df: pd.DataFrame,
    covariates: Optional[Sequence[str]] = None,
    treatment: str = "A",
    outcome: str = "Y",
    ps: str = "e",
    use_estimated_ps: bool = False,
    trim: Optional[float] = None,
    trim_mode: str = "drop",
) -> float:
    """
    AIPW (doubly robust): mô hình outcome OLS riêng cho từng nhóm (mu1, mu0)
    kết hợp trọng số nghịch đảo propensity score.
        tau = mean[ mu1 - mu0 + A(Y-mu1)/e - (1-A)(Y-mu0)/(1-e) ]
    Với trim_mode="drop", cả mô hình outcome lẫn phần trung bình đều chỉ dùng quan sát còn lại.
    """
    covariates = list(covariates) if covariates is not None else infer_covariates(df, treatment, outcome, ps)
    d, e = _prepare(df, covariates, treatment, ps, use_estimated_ps, trim, trim_mode)
    a, y = d[treatment].to_numpy(dtype=float), d[outcome].to_numpy(dtype=float)
    X = _design(d, covariates)
 
    mu1 = X @ _ols_fit(X[a == 1], y[a == 1])
    mu0 = X @ _ols_fit(X[a == 0], y[a == 0])
    psi = mu1 - mu0 + a * (y - mu1) / e - (1 - a) * (y - mu0) / (1 - e)
    return float(psi.mean())
 
 
# ----------------------------------------------------------------------
def estimate_all(
    df: pd.DataFrame,
    covariates: Optional[Sequence[str]] = None,
    treatment: str = "A",
    outcome: str = "Y",
    ps: str = "e",
    use_estimated_ps: bool = False,
    trim: Optional[float] = None,
    trim_mode: str = "drop",
) -> pd.Series:
    """
    Chạy cả 4 phương pháp và trả về ATE của từng phương pháp (Series).
    Trimming (trim_mode="drop") được áp dụng MỘT lần và cả 4 phương pháp dùng cùng mẫu đã trim,
    để sai khác giữa các phương pháp không đến từ việc dùng hai quần thể khác nhau.
    """
    covariates = list(covariates) if covariates is not None else infer_covariates(df, treatment, outcome, ps)
    d, e = _prepare(df, covariates, treatment, ps, use_estimated_ps, trim, trim_mode)
    d = d.assign(**{ps: e})  # e đã dùng (thật / ước lượng / clip) nằm cùng dòng với d
    kw = dict(covariates=covariates, treatment=treatment, outcome=outcome)
    return pd.Series(
        {
            "naive": naive(d, treatment, outcome),
            "ols": ols(d, **kw),
            "iptw": iptw(d, **kw, ps=ps),  # d đã trim và đã có e cuối cùng nên không trim thêm
            "aipw": aipw(d, **kw, ps=ps),
        }
    )