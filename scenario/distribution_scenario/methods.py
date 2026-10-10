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

from typing import Optional, Sequence

import numpy as np
import pandas as pd
# Lọc biến nhiễu nếu không đề cập
from balance import infer_covariates


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


def estimate_ps(df: pd.DataFrame, covariates: Optional[Sequence[str]] = None,
                treatment: str = "A", max_iter: int = 100, ridge: float = 1e-8) -> np.ndarray:
    """
    Ước lượng propensity score bằng hồi quy logistic.
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


def _get_ps(df: pd.DataFrame, covariates: Sequence[str], treatment: str, 
            ps: str, use_estimated_ps: bool, trim: Optional[float]) -> np.ndarray:
    e = estimate_ps(df, covariates, treatment) if use_estimated_ps else df[ps].to_numpy(dtype=float)
    lo = 1e-12 if trim is None else trim
    return np.clip(e, lo, 1 - lo)

# ----------------------------------------------------------------------
# 4 phương pháp ước lượng ATE
# ----------------------------------------------------------------------
def naive(df: pd.DataFrame, treatment: str = "A", outcome: str = "Y") -> float:
    """Naive: chênh lệch trung bình Y giữa nhóm A=1 và A=0 (bỏ qua nhiễu)."""
    a, y = df[treatment].to_numpy(), df[outcome].to_numpy(dtype=float)
    return float(y[a == 1].mean() - y[a == 0].mean())


def ols(df: pd.DataFrame, covariates: Optional[Sequence[str]] = None, 
        treatment: str = "A", outcome: str = "Y") -> float:
    """OLS hiệu chỉnh: hệ số của A trong hồi quy Y ~ 1 + A + X."""
    covariates = list(covariates) if covariates is not None else infer_covariates(df, treatment, outcome)
    X = np.column_stack([np.ones(len(df)), df[treatment].to_numpy(dtype=float), df[covariates].to_numpy(dtype=float)])
    beta = _ols_fit(X, df[outcome].to_numpy(dtype=float))
    return float(beta[1])


def iptw(df: pd.DataFrame, covariates: Optional[Sequence[str]] = None, treatment: str = "A",
         outcome: str = "Y", ps: str = "e", use_estimated_ps: bool = False, trim: Optional[float] = None,
         normalize: bool = True) -> float:
    """
    IPTW cho ATE.
    :param normalize: True -> ước lượng Hajek (chuẩn hóa trọng số, ổn định hơn);
                      False -> Horvitz-Thompson.
    :param trim: clip e(X) về [trim, 1-trim]
    """
    covariates = list(covariates) if covariates is not None else infer_covariates(df, treatment, outcome, ps)
    e = _get_ps(df, covariates, treatment, ps, use_estimated_ps, trim)
    a, y = df[treatment].to_numpy(dtype=float), df[outcome].to_numpy(dtype=float)
    w1, w0 = a / e, (1 - a) / (1 - e)
    if normalize:
        return float((w1 * y).sum() / w1.sum() - (w0 * y).sum() / w0.sum())
    return float((w1 * y).mean() - (w0 * y).mean())


def aipw(df: pd.DataFrame, covariates: Optional[Sequence[str]] = None, treatment: str = "A",
         outcome: str = "Y", ps: str = "e", use_estimated_ps: bool = False, trim: Optional[float] = None) -> float:
    """
    AIPW (doubly robust): mô hình outcome OLS riêng cho từng nhóm (mu1, mu0)
    kết hợp trọng số nghịch đảo propensity score.
        tau = mean[ mu1 - mu0 + A(Y-mu1)/e - (1-A)(Y-mu0)/(1-e) ]
    """
    covariates = list(covariates) if covariates is not None else infer_covariates(df, treatment, outcome, ps)
    e = _get_ps(df, covariates, treatment, ps, use_estimated_ps, trim)
    a, y = df[treatment].to_numpy(dtype=float), df[outcome].to_numpy(dtype=float)
    X = _design(df, covariates)

    mu1 = X @ _ols_fit(X[a == 1], y[a == 1])
    mu0 = X @ _ols_fit(X[a == 0], y[a == 0])
    psi = mu1 - mu0 + a * (y - mu1) / e - (1 - a) * (y - mu0) / (1 - e)
    return float(psi.mean())

def estimate_all(df: pd.DataFrame, covariates: Optional[Sequence[str]] = None, 
                 treatment: str = "A", outcome: str = "Y", ps: str = "e",
                 use_estimated_ps: bool = False, trim: Optional[float] = None) -> pd.Series:
    """Chạy cả 4 phương pháp và trả về ATE của từng phương pháp (Series)."""
    covariates = list(covariates) if covariates is not None else infer_covariates(df, treatment, outcome, ps)
    kw = dict(covariates=covariates, treatment=treatment, outcome=outcome)
    ps_kw = dict(ps=ps, use_estimated_ps=use_estimated_ps, trim=trim)
    return pd.Series(
        {
            "naive": naive(df, treatment, outcome),
            "ols": ols(df, **kw),
            "iptw": iptw(df, **kw, **ps_kw),
            "aipw": aipw(df, **kw, **ps_kw),
        }
    )