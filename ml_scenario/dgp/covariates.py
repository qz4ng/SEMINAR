"""
Biến nền Z ~ N_d(0, Σ), Σ_jk = rho^|j-k|, và biến quan sát X = h(Z).
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from scipy.linalg import cholesky, toeplitz


def draw_z(rng: np.random.Generator, n: int, d: int, rho: float) -> np.ndarray:
    """
    Sinh Z ~ N_d(0, Σ) với Σ_jk = rho^|j-k|.
    :param rng: np.random.Generator
    :param n: cỡ mẫu
    :param d: số chiều (>= 5 vì các hàm nuisance dùng 5 cột đầu)
    :param rho: tương quan giữa hai tọa độ kề nhau
    :return: ndarray (n, d)
    """
    if d < 5:
        raise ValueError(f"d phải >= 5, nhận {d}")
    z = rng.standard_normal((n, d))
    if rho == 0:
        return z
    L = cholesky(toeplitz(rho ** np.arange(d)), lower=True)
    return z @ L.T


def transform(z: np.ndarray, mode: Literal["identity", "ks"]) -> np.ndarray:
    """
    X = h(Z). 'identity': X = Z. 'ks': biến đổi Kang–Schafer (2007) cho 4 cột đầu,
    các cột còn lại giữ nguyên. Không chuẩn hóa sau biến đổi (thang đo lệch là chủ ý).
    :return: bản sao, cùng shape với z
    """
    x = z.copy()
    if mode == "identity":
        return x
    if mode != "ks":
        raise ValueError(f"mode phải là 'identity' hoặc 'ks', nhận {mode!r}")
    z1, z2, z3, z4 = z[:, 0], z[:, 1], z[:, 2], z[:, 3]
    x[:, 0] = np.exp(z1 / 2)
    x[:, 1] = z2 / (1 + np.exp(z1)) + 10
    x[:, 2] = (z1 * z3 / 25 + 0.6) ** 3
    x[:, 3] = (z2 + z4 + 20) ** 2
    return x
