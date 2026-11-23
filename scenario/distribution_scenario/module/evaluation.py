"""
Ước lượng kèm sai số chuẩn (SE) / CI 95% và mô phỏng lặp (Monte Carlo) cho nhóm 2.
tái sử dụng estimate_ps, _prepare, _design, _ols_fit từ methods.py.

Các estimator (đều trả về (ATE_hat, SE)):
    naive      chênh lệch trung bình, SE Welch
    ols        hệ số A trong Y ~ 1 + A + X, SE robust HC1
    iptw       Hajek (trọng số chuẩn hóa), SE theo hàm ảnh hưởng
    iptw_ht    Horvitz-Thompson (không chuẩn hóa)
    aipw       doubly robust
    iptw_trim  Hajek sau trimming (drop e ngoài [trim, 1-trim])
    aipw_trim  AIPW sau trimming
    ow         Overlap weighting (estimand ATO): w1 = 1-e, w0 = e
    match      1-NN matching theo logit(e_hat) có hoàn lại (không có SE)

Lưu ý SE: dùng e(X) ước lượng như plug-in và bỏ qua sai số của bước ước lượng PS
(thường hơi bảo thủ cho IPTW). Vì tau(X)=tau0 đồng nhất nên ATE, ATE trên vùng overlap và ATO đều = tau0.
"""

from __future__ import annotations

from typing import Callable, Dict, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .balance import infer_covariates, overlap_mask
from .methods import _design, _ols_fit, _prepare, estimate_ps

Z95 = 1.959963984540054
METHODS_ALL = ["naive", "ols", "iptw", "iptw_ht", "aipw", "iptw_trim", "aipw_trim", "ow", "match"]


def _se(psi: np.ndarray) -> float:
    return float(psi.std(ddof=1) / np.sqrt(len(psi)))


def _hajek(a, y, w1, w0) -> Tuple[float, float]:
    m1, m0 = (w1 * y).sum() / w1.sum(), (w0 * y).sum() / w0.sum()
    psi = w1 * (y - m1) / w1.mean() - w0 * (y - m0) / w0.mean()
    return float(m1 - m0), _se(psi)


def est_naive(a, y):
    y1, y0 = y[a == 1], y[a == 0]
    return float(y1.mean() - y0.mean()), float(np.sqrt(y1.var(ddof=1) / len(y1) + y0.var(ddof=1) / len(y0)))


def est_ols(a, y, X):
    Z = np.column_stack([np.ones(len(y)), a, X])
    beta = _ols_fit(Z, y)
    r = y - Z @ beta
    bread = np.linalg.inv(Z.T @ Z)
    meat = (Z * r[:, None] ** 2).T @ Z
    cov = bread @ meat @ bread * len(y) / (len(y) - Z.shape[1])
    return float(beta[1]), float(np.sqrt(cov[1, 1]))


def est_iptw(a, y, e):
    return _hajek(a, y, a / e, (1 - a) / (1 - e))


def est_iptw_ht(a, y, e):
    psi = a * y / e - (1 - a) * y / (1 - e)
    return float(psi.mean()), _se(psi)


def est_ow(a, y, e):
    """Overlap weighting: ước lượng ATO."""
    return _hajek(a, y, a * (1 - e), (1 - a) * e)


def est_aipw(a, y, e, D):
    mu1 = D @ _ols_fit(D[a == 1], y[a == 1])
    mu0 = D @ _ols_fit(D[a == 0], y[a == 0])
    psi = mu1 - mu0 + a * (y - mu1) / e - (1 - a) * (y - mu0) / (1 - e)
    return float(psi.mean()), _se(psi)


def est_match(a, y, e, caliper: float = 0.2):
    """
    Matching ATE: mỗi quan sát tìm 1 láng giềng gần nhất ở nhóm đối diện theo logit(e_hat), có hoàn lại.
    Caliper = caliper * SD(logit e). Quan sát không có đối sánh trong caliper bị loại.
    :return: (ate, tỉ lệ bị loại)
    """
    lg = np.log(e / (1 - e))
    cal = caliper * lg.std()
    idx1, idx0 = np.where(a == 1)[0], np.where(a == 0)[0]
    effects, kept = np.full(len(y), np.nan), np.zeros(len(y), bool)
    for src, pool in ((idx1, idx0), (idx0, idx1)):
        order = pool[np.argsort(lg[pool])]
        pl = lg[order]
        pos = np.clip(np.searchsorted(pl, lg[src]), 1, len(pl) - 1)
        left, right = pos - 1, pos
        pick = np.where(np.abs(pl[left] - lg[src]) <= np.abs(pl[right] - lg[src]), left, right)
        dist = np.abs(pl[pick] - lg[src])
        ok = dist <= cal
        ycf = y[order[pick]]
        eff = np.where(a[src] == 1, y[src] - ycf, ycf - y[src])
        effects[src[ok]] = eff[ok]
        kept[src[ok]] = True
    if kept.sum() == 0:
        return np.nan, 1.0
    return float(np.nanmean(effects)), float(1 - kept.mean())


def estimate_with_se(
    df: pd.DataFrame,
    covariates: Optional[Sequence[str]] = None,
    trim: float = 0.05,
    use_estimated_ps: bool = True,
    methods: Sequence[str] = METHODS_ALL,
    treatment: str = "A",
    outcome: str = "Y",
    ps: str = "e",
) -> pd.DataFrame:
    """
    Chạy các estimator trên MỘT bộ dữ liệu.
    :return: DataFrame index = phương pháp, cột est, se, lo, hi (CI 95% Wald); riêng 'match' có thêm cột discard.
    """
    covariates = list(covariates) if covariates is not None else infer_covariates(df, treatment, outcome, ps)
    a = df[treatment].to_numpy(float)
    y = df[outcome].to_numpy(float)
    X = df[covariates].to_numpy(float)
    e = estimate_ps(df, covariates, treatment) if use_estimated_ps else df[ps].to_numpy(float)
    e = np.clip(e, 1e-12, 1 - 1e-12)
    D = np.column_stack([np.ones(len(df)), X])

    out: Dict[str, Tuple[float, float]] = {}
    for m in methods:
        if m == "naive":
            out[m] = est_naive(a, y)
        elif m == "ols":
            out[m] = est_ols(a, y, X)
        elif m == "iptw":
            out[m] = est_iptw(a, y, e)
        elif m == "iptw_ht":
            out[m] = est_iptw_ht(a, y, e)
        elif m == "aipw":
            out[m] = est_aipw(a, y, e, D)
        elif m in ("iptw_trim", "aipw_trim"):
            k = overlap_mask(e, trim)
            if (a[k] == 1).sum() < 5 or (a[k] == 0).sum() < 5:
                out[m] = (np.nan, np.nan)
            elif m == "iptw_trim":
                out[m] = est_iptw(a[k], y[k], e[k])
            else:
                out[m] = est_aipw(a[k], y[k], e[k], D[k])
        elif m == "ow":
            out[m] = est_ow(a, y, e)
        elif m == "match":
            est, disc_rate = est_match(a, y, e)
            out[m] = (est, np.nan)
        else:
            raise ValueError(f"Phương pháp không có: {m}")
    res = pd.DataFrame(out, index=["est", "se"]).T
    res["lo"], res["hi"] = res["est"] - Z95 * res["se"], res["est"] + Z95 * res["se"]
    if "match" in out:
        res.loc["match", "discard"] = disc_rate
    return res


def diagnostics(df: pd.DataFrame, trim: float = 0.05, eps: float = 0.01, use_estimated_ps: bool = True) -> Dict[str, float]:
    """Chẩn đoán overlap trên một bộ dữ liệu: e thật ngoài [eps,1-eps], trọng số IPTW lớn nhất, ESS ratio, tỉ lệ treated, tỉ lệ bị trim."""
    a, et = df["A"].to_numpy(), df["e"].to_numpy()
    e = estimate_ps(df, infer_covariates(df)) if use_estimated_ps else et
    e = np.clip(e, 1e-12, 1 - 1e-12)
    w = np.where(a == 1, 1 / e, 1 / (1 - e))
    return {
        "treated_rate": a.mean(),
        "e_outside": float(((et < eps) | (et > 1 - eps)).mean()),
        "max_weight": float(w.max()),
        "ess_ratio": float(w.sum() ** 2 / (w ** 2).sum() / len(w)),
        "trim_drop": float(1 - overlap_mask(e, trim).mean()),
    }


def monte_carlo(
    sim,
    reps: int = 1000,
    n: Optional[int] = None,
    trim: float = 0.05,
    use_estimated_ps: bool = True,
    methods: Sequence[str] = METHODS_ALL,
    seed: Optional[int] = None,
    keep_raw: bool = False,
):
    """
    Lặp `reps` lần: sinh dữ liệu -> estimate_with_se + diagnostics.
    :param sim: đối tượng LocationSimulation / Simulation (dùng sim.ate làm giá trị thật)
    :return: (summary, diag) hoặc (summary, diag, raw) nếu keep_raw.
        summary: index = phương pháp; cột bias, sd, rmse, coverage, ci_width, mean_se, n_fail
        diag: Series trung bình các chỉ số chẩn đoán qua các lần lặp
    """
    if seed is not None:
        sim.rng = np.random.default_rng(seed)
    truth = sim.ate
    est, se, disc, diag = [], [], [], []
    for _ in range(reps):
        df = sim.generate(n=n)
        try:
            r = estimate_with_se(df, trim=trim, use_estimated_ps=use_estimated_ps, methods=methods)
        except Exception:  # ví dụ: một nhóm biến mất sau trimming
            r = pd.DataFrame(np.nan, index=list(methods), columns=["est", "se", "lo", "hi"])
        est.append(r["est"]); se.append(r["se"])
        if "discard" in r:
            disc.append(r["discard"].get("match", np.nan))
        diag.append(diagnostics(df, trim=trim, use_estimated_ps=use_estimated_ps))
    est, se = pd.DataFrame(est).reset_index(drop=True), pd.DataFrame(se).reset_index(drop=True)
    lo, hi = est - Z95 * se, est + Z95 * se
    cover = ((lo <= truth) & (truth <= hi)).astype(float).where(est.notna() & se.notna())
    summ = pd.DataFrame({
        "bias": est.mean() - truth,
        "sd": est.std(ddof=1),
        "rmse": np.sqrt(((est - truth) ** 2).mean()),
        "coverage": cover.mean(),
        "ci_width": (hi - lo).mean(),
        "mean_se": se.mean(),
        "n_fail": est.isna().sum(),
    })
    diag = pd.DataFrame(diag).mean()
    if disc:
        diag["match_discard"] = float(np.nanmean(disc))
    return (summ, diag, est) if keep_raw else (summ, diag)