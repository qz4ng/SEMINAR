"""
Kiểm tra balance trước và sau khi áp dụng phương pháp gán trọng số
Input: (pd.DataFrame) các trường dữ liệu: [X], A, Y, e(X)
Output: (pd.DataFrame) SMD; VR và True/False của các biến trước và sau khi gán trọng số
với True là đã cân bằng

Tiêu chí cân bằng (mặc định):
    |SMD| < 0.1         SMD = (mean_1 - mean_0) / sqrt((var_1 + var_0) / 2)
    0.5 <= VR <= 2.0    VR  = var_1 / var_0
Một biến được xem là cân bằng khi thỏa CẢ HAI tiêu chí.
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

import numpy as np
import pandas as pd

# Các cột không phải biến nhiễu (kể cả các cột "thật" do Simulation sinh ra)
RESERVED_COLUMNS = {"A", "Y", "e", "Y0", "Y1", "m", "tau"}

def infer_covariates(df: pd.DataFrame, treatment: str = "A", outcome: str = "Y", ps: str = "e") -> list:
    """Lấy danh sách biến nhiễu X = mọi cột không thuộc nhóm A, Y, e, Y0, Y1, m, tau."""
    reserved = RESERVED_COLUMNS | {treatment, outcome, ps}
    return [c for c in df.columns if c not in reserved]


def iptw_weights(df: pd.DataFrame, treatment: str = "A",
                 ps: str = "e", trim: Optional[float] = None) -> np.ndarray:
    """
    Trọng số IPTW cho ATE: w = A/e + (1-A)/(1-e).
    :param trim: nếu có, clip e về [trim, 1 - trim] trước khi tính trọng số.
    """
    a = df[treatment].to_numpy()
    e = df[ps].to_numpy(dtype=float)
    low = 1e-12 if trim is None else trim
    e = np.clip(e, low, 1 - low)
    return np.where(a == 1, 1.0 / e, 1.0 / (1.0 - e))


def _weighted_mean_var(x: np.ndarray, w: np.ndarray) -> Tuple[float, float]:
    """Trung bình và phương sai có trọng số (hiệu chỉnh kiểu reliability weights)."""
    v1, v2 = w.sum(), (w**2).sum()
    mean = (w * x).sum() / v1
    denom = v1 - v2 / v1
    var = (w * (x - mean) ** 2).sum() / denom if denom > 0 else np.nan
    return mean, var


def _smd_vr(x: np.ndarray, a: np.ndarray, w: np.ndarray, sd_ref: float) -> Tuple[float, float]:
    m1, v1 = _weighted_mean_var(x[a == 1], w[a == 1])
    m0, v0 = _weighted_mean_var(x[a == 0], w[a == 0])
    smd = (m1 - m0) / sd_ref if sd_ref > 0 else np.nan
    vr = v1 / v0 if v0 > 0 else np.nan
    return smd, vr


def check_balance(df: pd.DataFrame, covariates: Optional[Sequence[str]] = None, treatment: str = "A",
                  ps: str = "e", weights: Optional[Sequence[float]] = None, trim: Optional[float] = None, 
                  smd_threshold: float = 0.1, vr_bounds: Tuple[float, float] = (0.5, 2.0)) -> pd.DataFrame:
    """
    So sánh độ cân bằng của các biến nhiễu giữa nhóm A=1 và A=0, trước và sau gán trọng số.

    :param df: DataFrame chứa [X], A, Y, e(X)
    :param covariates: danh sách biến nhiễu; None thì tự suy ra từ các cột còn lại
    :param treatment: tên cột can thiệp (0/1)
    :param ps: tên cột propensity score e(X)
    :param weights: trọng số tự cung cấp (độ dài n). None thì dùng IPTW từ cột ps
    :param trim: clip e(X) về [trim, 1-trim] khi tính IPTW (bỏ qua nếu truyền weights)
    :param smd_threshold: ngưỡng |SMD|
    :param vr_bounds: khoảng chấp nhận của VR
    :return: DataFrame, index là biến nhiễu, gồm các cột
        smd_before, vr_before, balanced_before,
        smd_after,  vr_after,  balanced_after
    """
    covariates = list(covariates) if covariates is not None else infer_covariates(df, treatment, ps=ps)
    if not covariates:
        raise ValueError("Không tìm thấy biến nhiễu nào để kiểm tra.")

    a = df[treatment].to_numpy()
    # Kiểm tra giá trị của A
    if set(np.unique(a)) - {0, 1}:
        raise ValueError(f"Cột '{treatment}' phải chỉ chứa 0/1.")

    if weights is None:
        # Nếu không có weights thì tính từ iptw bằng cột PS
        w_after = iptw_weights(df, treatment, ps, trim)
    else:
        w_after = np.asarray(weights, dtype=float)
        if len(w_after) != len(df):
            raise ValueError("weights phải có độ dài bằng số dòng của df.")
    # Trước khi làm gán weight thì weight bằng 1
    w_before = np.ones(len(df))

    # Ngưỡng chấp nhận của VR
    lo, hi = vr_bounds
    rows = {}
    for c in covariates:
        # Tính SMD và VR của từng biến nhiễu
        x = df[c].to_numpy(dtype=float)
        # SD gộp của mẫu gốc làm mẫu số chung
        _, v1 = _weighted_mean_var(x[a == 1], w_before[a == 1])
        _, v0 = _weighted_mean_var(x[a == 0], w_before[a == 0])
        sd_ref = np.sqrt((v1 + v0) / 2)

        smd_b, vr_b = _smd_vr(x, a, w_before, sd_ref)
        smd_a, vr_a = _smd_vr(x, a, w_after, sd_ref)
        rows[c] = {
            "smd_before": smd_b,
            "vr_before": vr_b,
            "balanced_before": bool(abs(smd_b) < smd_threshold and lo <= vr_b <= hi),
            "smd_after": smd_a,
            "vr_after": vr_a,
            "balanced_after": bool(abs(smd_a) < smd_threshold and lo <= vr_a <= hi),
        }
    return pd.DataFrame(rows).T.astype(
        {"balanced_before": bool, "balanced_after": bool, "smd_before": float, "smd_after": float,
         "vr_before": float, "vr_after": float}
    )


def summarize(table: pd.DataFrame) -> pd.Series:
    """Tóm tắt bảng balance: số biến cân bằng và |SMD| lớn nhất trước/sau."""
    return pd.Series(
        {
            "n_covariates": len(table),
            "n_balanced_before": int(table["balanced_before"].sum()),
            "n_balanced_after": int(table["balanced_after"].sum()),
            "max_abs_smd_before": table["smd_before"].abs().max(),
            "max_abs_smd_after": table["smd_after"].abs().max(),
            "all_balanced_after": bool(table["balanced_after"].all()),
        }
    )