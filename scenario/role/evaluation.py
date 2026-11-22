"""
evaluation.py - Các phương pháp ước lượng ATE (NAIVE, OLS, IPTW, AIPW) và mô phỏng Monte Carlo.

Mỗi phương pháp trả về (ước lượng, SE). Tập biến hiệu chỉnh được truyền riêng:
    ps_set   biến đưa vào mô hình propensity score (IPTW, AIPW)
    out_set  biến đưa vào mô hình outcome (OLS, AIPW)
để mô phỏng đúng các lựa chọn "hiệu chỉnh biến nào" (xem simulation.SCENARIOS[...]['strategies']).

    naive  chênh lệch trung bình Y giữa hai nhóm, SE Welch (bỏ qua mọi biến)
    ols    hệ số của A trong Y ~ 1 + A + X(out_set), SE robust HC1
    iptw   Hajek (trọng số chuẩn hóa), SE hiệu chỉnh cho việc ước lượng PS (utilities.hajek_se_ps_corrected)
    aipw   doubly robust: mu1, mu0 bằng OLS theo từng nhóm trên out_set, PS logistic trên ps_set; SE theo hàm ảnh hưởng
Tuỳ chọn thêm (methods=...): "iptw_plugin" (SE coi PS đã biết), "ow" (overlap weighting, ATO), "iptw_trim" (trim 0.05).
"""

from __future__ import annotations

from typing import Dict, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from utilities import (Z95, design_matrix, ess, estimate_ps, hajek_se_ps_corrected, ols_fit, ols_hc1,
                       overlap_weights, trim_mask)

CORE_METHODS = ("naive", "ols", "iptw", "aipw")


# ----------------------------------------------------------------------------------------------
# Các estimator trên mảng numpy
# ----------------------------------------------------------------------------------------------
def est_naive(a, y) -> Tuple[float, float]:
    y1, y0 = y[a == 1], y[a == 0]
    se = np.sqrt(y1.var(ddof=1) / len(y1) + y0.var(ddof=1) / len(y0))
    return float(y1.mean() - y0.mean()), float(se)


def est_ols(a, y, Xout) -> Tuple[float, float]:
    Z = np.column_stack([np.ones(len(y)), a, Xout])   # Xout có thể có 0 cột (không hiệu chỉnh)
    beta, se = ols_hc1(Z, y)
    return float(beta[1]), float(se[1])


def _hajek(a, y, w1, w0) -> Tuple[float, float]:
    m1, m0 = (w1 * y).sum() / w1.sum(), (w0 * y).sum() / w0.sum()
    psi = w1 * (y - m1) / w1.mean() - w0 * (y - m0) / w0.mean()
    return float(m1 - m0), float(psi.std(ddof=1) / np.sqrt(len(y)))


def est_iptw(a, y, e, Xps, correct_ps: bool = True) -> Tuple[float, float]:
    est, se_plug = _hajek(a, y, a / e, (1 - a) / (1 - e))
    return est, (hajek_se_ps_corrected(a, y, e, Xps) if correct_ps else se_plug)


def est_aipw(a, y, e, Dout) -> Tuple[float, float]:
    mu1 = Dout @ ols_fit(Dout[a == 1], y[a == 1])
    mu0 = Dout @ ols_fit(Dout[a == 0], y[a == 0])
    psi = mu1 - mu0 + a * (y - mu1) / e - (1 - a) * (y - mu0) / (1 - e)
    return float(psi.mean()), float(psi.std(ddof=1) / np.sqrt(len(y)))


def est_ow(a, y, e) -> Tuple[float, float]:
    return _hajek(a, y, a * (1 - e), (1 - a) * e)


# ----------------------------------------------------------------------------------------------
# Ước lượng trên một DataFrame
# ----------------------------------------------------------------------------------------------
def estimate(df: pd.DataFrame, ps_set: Sequence[str] = (), out_set: Optional[Sequence[str]] = None,
             methods: Sequence[str] = CORE_METHODS, trim: float = 0.05) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """
    Chạy các phương pháp trên một mẫu.
    :param ps_set: biến trong mô hình PS; out_set: biến trong mô hình outcome (None => dùng ps_set)
    :return: (bảng est/se/lo/hi theo phương pháp, dict chẩn đoán trọng số IPTW: ess_ratio, max_weight, e_outside, e_min, e_max)
    """
    out_set = list(ps_set) if out_set is None else list(out_set)
    a = df["A"].to_numpy(dtype=float)
    y = df["Y"].to_numpy(dtype=float)
    need_ps = any(m in methods for m in ("iptw", "iptw_plugin", "aipw", "ow", "iptw_trim"))
    if need_ps:
        e, Xps = estimate_ps(df, list(ps_set), return_X=True)
    Dout = design_matrix(df, out_set)
    res: Dict[str, Tuple[float, float]] = {}
    for m in methods:
        if m == "naive":
            res[m] = est_naive(a, y)
        elif m == "ols":
            res[m] = est_ols(a, y, Dout[:, 1:])
        elif m == "iptw":
            res[m] = est_iptw(a, y, e, Xps, True)
        elif m == "iptw_plugin":
            res[m] = est_iptw(a, y, e, Xps, False)
        elif m == "aipw":
            res[m] = est_aipw(a, y, e, Dout)
        elif m == "ow":
            res[m] = est_ow(a, y, e)
        elif m == "iptw_trim":
            k = trim_mask(e, trim)
            res[m] = est_iptw(a[k], y[k], e[k], Xps[k], True) if (a[k].sum() > 5 and (1 - a[k]).sum() > 5) else (np.nan, np.nan)
        else:
            raise ValueError(f"Phương pháp không có: {m}")
    tab = pd.DataFrame(res, index=["est", "se"]).T
    tab["lo"], tab["hi"] = tab["est"] - Z95 * tab["se"], tab["est"] + Z95 * tab["se"]
    diag: Dict[str, float] = {}
    if need_ps:
        w = np.where(a == 1, 1 / e, 1 / (1 - e))
        diag = {"ess_ratio": ess(w) / len(w), "max_weight": float(w.max()),
                "e_outside": float(((e < 0.01) | (e > 0.99)).mean()), "e_min": float(e.min()), "e_max": float(e.max())}
    return tab, diag


# ----------------------------------------------------------------------------------------------
# Monte Carlo
# ----------------------------------------------------------------------------------------------
def _run_chunk(sim, n: int, reps: int, strategies: Dict[str, dict], methods: Sequence[str], seed: int,
               trim: float) -> pd.DataFrame:
    sim.rng = np.random.default_rng(seed)
    rows = []
    for r in range(reps):
        df = sim.generate(n=n)
        for key, s in strategies.items():
            tab, dg = estimate(df, ps_set=s["adjust"], methods=methods, trim=trim)
            for m, row in tab.iterrows():
                rows.append((key, m, row["est"], row["se"], dg.get("ess_ratio", np.nan), dg.get("max_weight", np.nan),
                             dg.get("e_outside", np.nan)))
    return pd.DataFrame(rows, columns=["strategy", "method", "est", "se", "ess_ratio", "max_weight", "e_outside"])


def monte_carlo(sim, n: int = 2000, reps: int = 1000, methods: Sequence[str] = CORE_METHODS,
                strategies: Optional[Dict[str, dict]] = None, seed: int = 251, n_jobs: int = 2,
                trim: float = 0.05, truth: Optional[float] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Lặp reps lần: sinh dữ liệu -> chạy mọi (strategy x method).
    :param truth: giá trị đích; mặc định sim.true_ate (hiệu ứng TỔNG)
    :return: (summary, raw)
        summary: mỗi dòng một (strategy, method) với bias, sd, rmse, mean_se, coverage, ci_width, mc_se_bias,
                 ess_ratio, max_weight, e_outside (trung bình qua các lần lặp)
        raw: ước lượng từng lần lặp (cột rep, strategy, method, est, se) để vẽ boxplot
    """
    strategies = strategies or sim.strategies
    truth = sim.true_ate if truth is None else truth
    seeds = np.random.SeedSequence(seed).spawn(n_jobs)
    seeds = [int(s.generate_state(1)[0]) for s in seeds]
    base = reps // n_jobs
    sizes = [base + (1 if i < reps % n_jobs else 0) for i in range(n_jobs)]
    if n_jobs > 1:
        from joblib import Parallel, delayed
        parts = Parallel(n_jobs=n_jobs, backend="multiprocessing")(
            delayed(_run_chunk)(sim, n, sz, strategies, methods, sd, trim) for sz, sd in zip(sizes, seeds))
    else:
        parts = [_run_chunk(sim, n, reps, strategies, methods, seeds[0], trim)]
    raw = pd.concat(parts, ignore_index=True)
    raw["rep"] = raw.groupby(["strategy", "method"]).cumcount()
    raw["cover"] = ((raw["est"] - Z95 * raw["se"] <= truth) & (truth <= raw["est"] + Z95 * raw["se"])).astype(float)
    raw.loc[raw["se"].isna() | raw["est"].isna(), "cover"] = np.nan
    raw["width"] = 2 * Z95 * raw["se"]
    g = raw.groupby(["strategy", "method"], sort=False)
    summ = pd.DataFrame({
        "mean_est": g["est"].mean(),
        "bias": g["est"].mean() - truth,
        "sd": g["est"].std(ddof=1),
        "rmse": g["est"].apply(lambda x: float(np.sqrt(((x - truth) ** 2).mean()))),
        "mean_se": g["se"].mean(),
        "coverage": g["cover"].mean(),
        "ci_width": g["width"].mean(),
        "ess_ratio": g["ess_ratio"].mean(),
        "max_weight": g["max_weight"].mean(),
        "e_outside": g["e_outside"].mean(),
    })
    summ["mc_se_bias"] = summ["sd"] / np.sqrt(g["est"].count())
    summ = summ.reset_index()
    summ.insert(0, "n", n)
    summ.insert(0, "scenario", sim.name)
    raw.insert(0, "n", n)
    raw.insert(0, "scenario", sim.name)
    return summ, raw


def asymptotic_bias(sim, strategy_adjust: Sequence[str], method: str = "ols", n: int = 400_000, seed: int = 7,
                    truth: Optional[float] = None) -> float:
    """
    Bias tiệm cận (một mẫu rất lớn) của estimator với tập hiệu chỉnh cho trước, so với hiệu ứng TỔNG.
    Dùng làm đường tham chiếu lý thuyết: nếu bias mô phỏng ở n nhỏ khớp với giá trị này thì sai lệch là CHỆCH
    hệ thống (cấu trúc DAG), không phải nhiễu mẫu.
    """
    truth = sim.true_ate if truth is None else truth
    df = sim.generate(n=n, seed=seed)
    tab, _ = estimate(df, ps_set=list(strategy_adjust), methods=(method,))
    return float(tab.loc[method, "est"] - truth)
