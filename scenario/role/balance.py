"""
balance.py - Kiểm tra cân bằng (balance) và các chẩn đoán liên quan.

    smd, variance_ratio            độ chênh chuẩn hóa và tỉ số phương sai
    balance_table                  bảng SMD/VR trước và sau gán trọng số
    balance_after_strategy         cân bằng của MỌI biến quan sát khi PS chỉ dùng một tập hiệu chỉnh cho trước
    weight_diagnostics             ESS, trọng số lớn nhất, phân vị
    overlap_diagnostics            tỉ lệ e ngoài [0.01, 0.99], e_min, e_max theo nhóm
    role_diagnostics               những gì DỮ LIỆU "nhìn thấy" về mỗi biến (tương quan với A và với Y | A)

Tiêu chí cân bằng mặc định: |SMD| < 0.1 và 0.5 <= VR <= 2.
Lưu ý: SMD chỉ kiểm tra biến đã có trong dữ liệu; không phát hiện được confounder không đo, và với biến hậu can thiệp
(mediator, collider) việc "cân bằng" không có ý nghĩa nhân quả.
"""

from __future__ import annotations

from typing import Dict, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from utilities import ess, estimate_ps, iptw_weights


def _wmean_var(x: np.ndarray, w: np.ndarray) -> Tuple[float, float]:
    s1, s2 = w.sum(), (w ** 2).sum()
    m = (w * x).sum() / s1
    d = s1 - s2 / s1
    return m, ((w * (x - m) ** 2).sum() / d if d > 0 else np.nan)


def smd(x: np.ndarray, a: np.ndarray, w: Optional[np.ndarray] = None, sd_ref: Optional[float] = None) -> float:
    """SMD = (mean1 - mean0) / sqrt((var1_goc + var0_goc)/2); mẫu số lấy từ mẫu GỐC (chưa trọng số) để so sánh trước/sau."""
    w = np.ones(len(x)) if w is None else w
    if sd_ref is None:
        _, v1 = _wmean_var(x[a == 1], np.ones((a == 1).sum()))
        _, v0 = _wmean_var(x[a == 0], np.ones((a == 0).sum()))
        sd_ref = np.sqrt((v1 + v0) / 2)
    m1, _ = _wmean_var(x[a == 1], w[a == 1])
    m0, _ = _wmean_var(x[a == 0], w[a == 0])
    return float((m1 - m0) / sd_ref) if sd_ref > 0 else np.nan


def variance_ratio(x: np.ndarray, a: np.ndarray, w: Optional[np.ndarray] = None) -> float:
    w = np.ones(len(x)) if w is None else w
    _, v1 = _wmean_var(x[a == 1], w[a == 1])
    _, v0 = _wmean_var(x[a == 0], w[a == 0])
    return float(v1 / v0) if v0 > 0 else np.nan


def balance_table(df: pd.DataFrame, covariates: Sequence[str], weights: Optional[np.ndarray] = None,
                  smd_threshold: float = 0.1, vr_bounds: Tuple[float, float] = (0.5, 2.0)) -> pd.DataFrame:
    """Bảng cân bằng từng covariate: smd_before, vr_before, smd_after, vr_after, balanced_after (weights=None => chỉ 'before')."""
    a = df["A"].to_numpy()
    rows = {}
    for c in covariates:
        x = df[c].to_numpy(dtype=float)
        sb, vb = smd(x, a), variance_ratio(x, a)
        row = {"smd_before": sb, "vr_before": vb}
        if weights is not None:
            _, v1 = _wmean_var(x[a == 1], np.ones((a == 1).sum()))
            _, v0 = _wmean_var(x[a == 0], np.ones((a == 0).sum()))
            sa = smd(x, a, weights, sd_ref=np.sqrt((v1 + v0) / 2))
            va = variance_ratio(x, a, weights)
            row.update({"smd_after": sa, "vr_after": va,
                        "balanced_after": bool(abs(sa) < smd_threshold and vr_bounds[0] <= va <= vr_bounds[1])})
        rows[c] = row
    return pd.DataFrame(rows).T


def balance_after_strategy(df: pd.DataFrame, adjust: Sequence[str], check: Sequence[str]) -> pd.DataFrame:
    """
    Ước lượng PS chỉ từ `adjust`, tính trọng số IPTW rồi kiểm tra cân bằng của các biến trong `check`
    (thường là mọi biến quan sát). Cho thấy: biến nằm trong PS được cân bằng, biến bị bỏ qua có thể không.
    """
    e = estimate_ps(df, list(adjust))
    w = iptw_weights(df["A"].to_numpy(), e)
    t = balance_table(df, list(check), weights=w)
    t.insert(0, "trong_PS", [c in adjust for c in t.index])
    return t


def weight_diagnostics(a: np.ndarray, w: np.ndarray) -> pd.Series:
    return pd.Series({
        "n": len(w), "ess": ess(w), "ess_ratio": ess(w) / len(w),
        "ess_treated": ess(w[a == 1]), "ess_control": ess(w[a == 0]),
        "max_weight": float(w.max()), "p99_weight": float(np.quantile(w, 0.99)),
    })


def overlap_diagnostics(a: np.ndarray, e: np.ndarray, eps: float = 0.01) -> pd.Series:
    return pd.Series({
        "treated_rate": float(a.mean()), "e_min": float(e.min()), "e_max": float(e.max()),
        "e_outside": float(((e < eps) | (e > 1 - eps)).mean()),
        "e_mean_treated": float(e[a == 1].mean()), "e_mean_control": float(e[a == 0].mean()),
    })


def role_diagnostics(df: pd.DataFrame, covariates: Sequence[str]) -> pd.DataFrame:
    """
    Những gì dữ liệu cho thấy về từng biến X:
        smd_A       chênh chuẩn hóa của X giữa nhóm A=1 và A=0 (X có liên quan tới A không)
        corr_XY_A   tương quan riêng của X và Y sau khi loại ảnh hưởng của A (X có liên quan tới Y không)
    Confounder, mediator và collider hậu can thiệp thường cho cùng một "dấu vân tay" (liên quan cả A lẫn Y) nên
    KHÔNG thể phân biệt bằng dữ liệu: cần DAG / thứ tự thời gian.
    """
    a = df["A"].to_numpy(dtype=float)
    y = df["Y"].to_numpy(dtype=float)
    Z = np.column_stack([np.ones(len(a)), a])
    ry = y - Z @ np.linalg.lstsq(Z, y, rcond=None)[0]
    rows = {}
    for c in covariates:
        x = df[c].to_numpy(dtype=float)
        rx = x - Z @ np.linalg.lstsq(Z, x, rcond=None)[0]
        rows[c] = {"smd_A": smd(x, df["A"].to_numpy()),
                   "corr_XY_A": float(np.corrcoef(rx, ry)[0, 1]),
                   "corr_XA": float(np.corrcoef(x, a)[0, 1])}
    t = pd.DataFrame(rows).T
    t["liên quan A?"] = np.where(t["smd_A"].abs() > 0.1, "có", "không")
    t["liên quan Y|A?"] = np.where(t["corr_XY_A"].abs() > 0.1, "có", "không")
    return t
