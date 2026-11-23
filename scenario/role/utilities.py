"""
utilities.py - Hàm bổ trợ dùng chung và các kỹ thuật cải thiện ước lượng.

Nhóm 1: số học cơ bản          sigmoid, design_matrix, ols_fit, ols_hc1, fit_logit, estimate_ps
Nhóm 2: trọng số / overlap     iptw_weights, overlap_weights, trim_mask, clip_ps, ess
Nhóm 3: suy luận               hajek_se_ps_corrected (SE tính cả sai số ước lượng PS), bootstrap_se
Nhóm 4: vai trò biến từ DAG    ancestors, descendants, classify_roles, recommended_adjustment_set
"""

from __future__ import annotations

from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd

Z95 = 1.959963984540054


# Số học cơ bản

def sigmoid(z: np.ndarray) -> np.ndarray:
    z = np.clip(z, -500, 500)
    return 1.0 / (1.0 + np.exp(-z))


def design_matrix(df: pd.DataFrame, covariates: Sequence[str]) -> np.ndarray:
    """Ma trận thiết kế có cột chặn; covariates rỗng => chỉ cột chặn."""
    n = len(df)
    if len(covariates) == 0:
        return np.ones((n, 1))
    return np.column_stack([np.ones(n), df[list(covariates)].to_numpy(dtype=float)])


def ols_fit(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta


def ols_hc1(X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """OLS với sai số chuẩn robust HC1. Trả (beta, se)."""
    beta = ols_fit(X, y)
    r = y - X @ beta
    n, k = X.shape
    bread = np.linalg.inv(X.T @ X)
    meat = (X * (r ** 2)[:, None]).T @ X
    cov = bread @ meat @ bread * n / (n - k)
    return beta, np.sqrt(np.diag(cov))


def fit_logit(X: np.ndarray, a: np.ndarray, max_iter: int = 100, ridge: float = 1e-8) -> np.ndarray:
    """Logistic regression bằng IRLS (Newton). Bước bị chặn để ổn định khi gần tách hoàn toàn."""
    beta = np.zeros(X.shape[1])
    for _ in range(max_iter):
        p = sigmoid(X @ beta)
        w = np.clip(p * (1 - p), 1e-10, None)
        grad = X.T @ (a - p) - ridge * beta
        hess = X.T @ (X * w[:, None]) + ridge * np.eye(X.shape[1])
        step = np.clip(np.linalg.solve(hess, grad), -5, 5)
        beta = beta + step
        if np.max(np.abs(step)) < 1e-8:
            break
    return beta


def estimate_ps(df: pd.DataFrame, covariates: Sequence[str], treatment: str = "A",
                return_X: bool = False):
    """
    Propensity score ước lượng bằng logistic (hiệu ứng chính, tuyến tính trong covariates).
    covariates rỗng => PS hằng số = tỉ lệ treated (IPTW khi đó trùng naive).
    """
    X = design_matrix(df, covariates)
    e = sigmoid(X @ fit_logit(X, df[treatment].to_numpy(dtype=float)))
    e = np.clip(e, 1e-8, 1 - 1e-8)
    return (e, X) if return_X else e


# Trọng số, trimming, overlap

def iptw_weights(a: np.ndarray, e: np.ndarray, stabilized: bool = False) -> np.ndarray:
    """w = A/e + (1-A)/(1-e).
    stabilized: nhân với P(A=a) để trọng số trung bình ~= 1 (không đổi ước lượng Hajek)."""
    w = np.where(a == 1, 1.0 / e, 1.0 / (1.0 - e))
    if stabilized:
        pa = a.mean()
        w = w * np.where(a == 1, pa, 1 - pa)
    return w


def overlap_weights(a: np.ndarray, e: np.ndarray) -> np.ndarray:
    """Overlap weights (Li, Morgan & Zaslavsky 2018): treated (1-e), control e. Mục tiêu là ATO, trọng số bị chặn ≤ 1."""
    return np.where(a == 1, 1.0 - e, e)


def trim_mask(e: np.ndarray, trim: float) -> np.ndarray:
    """True với quan sát có e nằm trong [trim, 1-trim]."""
    return (e >= trim) & (e <= 1 - trim)


def clip_ps(e: np.ndarray, trim: float) -> np.ndarray:
    return np.clip(e, trim, 1 - trim)


def ess(w: np.ndarray) -> float:
    """Cỡ mẫu hiệu dụng Kish: (sum w)^2 / sum w^2."""
    w = np.asarray(w, dtype=float)
    s2 = (w ** 2).sum()
    return float(w.sum() ** 2 / s2) if s2 > 0 else float("nan")

# Suy luận cải thiện

def hajek_se_ps_corrected(a: np.ndarray, y: np.ndarray, e: np.ndarray, Xps: np.ndarray) -> float:
    """
    SE của ước lượng IPTW (Hajek) có tính SAI SỐ ƯỚC LƯỢNG PROPENSITY SCORE (M-estimation xếp chồng).

    Tham số θ = (mu1, mu0, gamma) giải đồng thời
        sum a/e (y - mu1) = 0,  sum (1-a)/(1-e) (y - mu0) = 0,  sum x (a - e) = 0.
    :param Xps: ma trận các biến thêm vào mô hình 
    :return: 
    """
    n, p = Xps.shape
    w1, w0 = a / e, (1 - a) / (1 - e) # tính trọng số cho từng quan sát
    m1, m0 = (w1 * y).sum() / w1.sum(), (w0 * y).sum() / w0.sum()   # ước lượng trung bình của Hajek
    # xây dựng ma trận influence function
    psi = np.column_stack([w1 * (y - m1), w0 * (y - m0), Xps * (a - e)[:, None]])
    # ma trận Jacobian
    B = np.zeros((p + 2, p + 2))
    # đạo hàm theo u_1 và u_0 
    B[0, 0], B[1, 1] = -w1.mean(), -w0.mean()
    # đạo hàm của treatment theo hệ số PS
    B[0, 2:] = (-(a * (y - m1) * (1 - e) / e)[:, None] * Xps).mean(axis=0)
    # đạo hàm của control 
    B[1, 2:] = (((1 - a) * (y - m0) * e / (1 - e))[:, None] * Xps).mean(axis=0)
    # đạo hàm của logistic score
    B[2:, 2:] = -(Xps.T * (e * (1 - e))) @ Xps / n
    inf = psi @ np.linalg.inv(B).T
    psi_tau = inf[:, 0] - inf[:, 1]
    return float(np.sqrt((psi_tau ** 2).sum()) / n)


def bootstrap_se(estimator: Callable[[pd.DataFrame], float], df: pd.DataFrame, B: int = 200,
                 seed: int = 0) -> float:
    """SE bootstrap không tham số (resample dòng). estimator nhận DataFrame trả về một số."""
    rng = np.random.default_rng(seed)
    n = len(df)
    vals = [estimator(df.iloc[rng.integers(0, n, n)]) for _ in range(B)]
    return float(np.std(vals, ddof=1))

### Vai trò của biến suy ra từ DAG

def _children(edges: Iterable[Tuple[str, str]]) -> Dict[str, Set[str]]:
    """
    Truy xuất quan hệ parents
    """
    ch: Dict[str, Set[str]] = {}
    for s, d in edges:
        ch.setdefault(s, set()).add(d)
        ch.setdefault(d, set())
    return ch


def descendants(edges: Iterable[Tuple[str, str]], node: str) -> Set[str]:
    """
    Xác định hậu duệ của một node trong DAG. 
    Ý tưởng: biến D là hậu duệ của X nếu có 1 đường hướng từ X đến D
    Ví dụ: X -> A -> M -> Y => A, M, Y là hậu duệ của X
    """
    ch, seen, stack = _children(edges), set(), [node]
    while stack:
        for c in ch.get(stack.pop(), ()):
            if c not in seen:
                seen.add(c)
                stack.append(c)
    return seen


def ancestors(edges: Iterable[Tuple[str, str]], node: str) -> Set[str]:
    """
    Lấy ancestors của một node trong DAG. Ngược lại với descendants()
    """
    return descendants([(d, s) for s, d in edges], node)


def classify_roles(edges: Sequence[Tuple], treatment: str = "A", outcome: str = "Y") -> Dict[str, str]:
    """
    Gán vai trò cho từng biến theo cấu trúc DAG.

    Hậu can thiệp (là hậu duệ của A):
        mediator   nằm trên đường từ A tới Y
        collider   là hậu quả của cả A và Y
        descendant   còn lại
    Tiền can thiệp:
        confounder   tổ tiên của A và của Y (đường tới Y không đi qua A)
        instrument   chỉ là tổ tiên của A
        precision    chỉ là tổ tiên của Y
        collider (M-bias)   không gây ra A, Y nhưng có cha là nguyên nhân của A và cha là nguyên nhân của Y
        proxy        con của một confounder
        nhiễu        còn lại
    """
    e2 = [(x[0], x[1]) for x in edges]
    nodes = {n for s, d in e2 for n in (s, d)}
    desc_A = descendants(e2, treatment)
    no_A = [(s, d) for s, d in e2 if treatment not in (s, d)]
    anc_A = ancestors(e2, treatment)
    anc_Y_noA = ancestors(no_A, outcome)
    parents = {n: {s for s, d in e2 if d == n} for n in nodes}
    roles: Dict[str, str] = {treatment: "treatment", outcome: "outcome"}
    for v in nodes - {treatment, outcome}:
        if v in desc_A:
            if outcome in descendants(e2, v):
                roles[v] = "mediator"
            elif {treatment, outcome} <= parents[v] | ancestors(e2, v):
                roles[v] = "collider (hậu can thiệp)"
            else:
                roles[v] = "descendant của A"
        else:
            a_, y_ = v in anc_A, v in anc_Y_noA
            if a_ and y_:
                roles[v] = "confounder"
            elif a_:
                roles[v] = "instrument"
            elif y_:
                roles[v] = "precision"
            else:
                pa = parents[v]
                if any(p in anc_A and p not in anc_Y_noA for p in pa) and any(p in anc_Y_noA and p not in anc_A for p in pa):
                    roles[v] = "collider (M-bias)"
                elif any(p in anc_A and p in anc_Y_noA for p in pa):
                    roles[v] = "proxy của confounder"
                else:
                    roles[v] = "nhiễu"
    return roles


def recommended_adjustment_set(edges: Sequence[Tuple], observed: Sequence[str]) -> List[str]:
    """Tập hiệu chỉnh gợi ý: confounder + precision quan sát được (không instrument, mediator, collider)."""
    roles = classify_roles(edges)
    return [v for v in observed if roles.get(v) in ("confounder", "precision")]
