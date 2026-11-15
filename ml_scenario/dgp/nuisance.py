"""
Các hàm nuisance theo mã trong README: η_e (logit PS), μ0 (baseline outcome), τ (CATE).
Mọi hàm nhận z: ndarray (n, d) và trả ndarray (n,). Chỉ dùng 5 cột đầu của z.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Callable, Dict, Literal, Tuple

import numpy as np
from scipy.special import ndtr

from .covariates import draw_z

Fn = Callable[[np.ndarray], np.ndarray]


def _u(z: np.ndarray, j: int) -> np.ndarray:
    """U_j = Φ(Z_j), j là chỉ số 0-based."""
    return ndtr(z[:, j])


ETA_E: Dict[str, Fn] = {
    # Kang–Schafer (2007) đã đổi dấu: Cov(η̃_e, μ̃0) > 0 như e-nl (README 1.2)
    "lin": lambda z: z[:, 0] - 0.5 * z[:, 1] + 0.25 * z[:, 2] + 0.1 * z[:, 3],
    "nl": lambda z: (
        z[:, 0] + 0.5 * z[:, 0] * z[:, 1] + 0.5 * (z[:, 2] ** 2 - 1) + (z[:, 3] > 0) - 0.5
    ),
}

MU0: Dict[str, Fn] = {
    "lin": lambda z: z[:, 0] + 0.5 * z[:, 1] + 0.5 * z[:, 2] + 0.5 * z[:, 3],
    "nl": lambda z: (
        np.sin(np.pi * _u(z, 0) * _u(z, 1)) + 2 * (_u(z, 2) - 0.5) ** 2 + _u(z, 3) + 0.5 * _u(z, 4)
    ),
}

TAU: Dict[str, Fn] = {
    "const": lambda z: np.ones(z.shape[0]),
    "lin": lambda z: 1 + 0.5 * (z[:, 0] + z[:, 1]),
    "nl": lambda z: (
        1 + np.maximum(z[:, 0] + z[:, 1] + z[:, 2], 0) - np.maximum(z[:, 3] + z[:, 4], 0)
    ),
}

_REGISTRY = {"eta_e": ETA_E, "mu0": MU0}


@lru_cache(maxsize=None)
def standardizer(
    kind: Literal["eta_e", "mu0"],
    key: str,
    rho: float,
    n_ref: int = 1_000_000,
    seed: int = 12345,
) -> Tuple[float, float]:
    """
    (mean, sd) của hàm thô trên mẫu tham chiếu Z với d = 5. Các hàm chỉ dùng
    5 cột đầu và Σ là Toeplitz, nên hằng số không phụ thuộc d, chỉ phụ thuộc rho.
    """
    f = _REGISTRY[kind][key]
    vals = f(draw_z(np.random.default_rng(seed), n_ref, 5, rho))
    return float(vals.mean()), float(vals.std())


def make_nuisance(scenario) -> Tuple[Fn, Fn, Fn]:
    """
    Trả (eta_e_std, mu0_std, tau): η̃_e, μ̃0 đã chuẩn hóa về trung bình 0,
    phương sai 1; τ giữ nguyên thang đo.
    """
    eta_raw, mu_raw, tau = ETA_E[scenario.eta_e], MU0[scenario.mu0], TAU[scenario.tau]
    m_e, s_e = standardizer("eta_e", scenario.eta_e, scenario.rho)
    m_m, s_m = standardizer("mu0", scenario.mu0, scenario.rho)

    def eta_e_std(z: np.ndarray) -> np.ndarray:
        return (eta_raw(z) - m_e) / s_e

    def mu0_std(z: np.ndarray) -> np.ndarray:
        return (mu_raw(z) - m_m) / s_m

    return eta_e_std, mu0_std, tau
