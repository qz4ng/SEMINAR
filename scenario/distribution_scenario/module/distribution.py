"""
Mô phỏng dữ liệu theo các kịch bản phân phối của biến nhiễu (tham khảo thêm ở phần README.md)
Input: Tham số và kịch bản phân phối
Output: Dữ liệu mô phỏng cho từng phân phối

Mô hình sinh dữ liệu (DGP), chỉ phân phối của X1, X2 thay đổi giữa các kịch bản:
    e(X) = sigmoid(gamma0 + gamma1*X1 + gamma2*X2)
    A    ~ Bernoulli(e(X))
    m(X) = beta0 + beta1*X1 + beta2*X2
    tau(X) = tau0
    Y    = A*tau(X) + m(X) + eps,  eps ~ N(0, sigma^2)
"""

from __future__ import annotations

from typing import Callable, Dict, Optional, Tuple, Union

import numpy as np
import pandas as pd

Sampler = Callable[[np.random.Generator, int], np.ndarray]


# ----------------------------------------------------------------------
# Các bộ sinh biến nhiễu
# ----------------------------------------------------------------------
def _normal(var: float = 1.0) -> Sampler:
    """N(0; var), var là phương sai."""
    sd = np.sqrt(var)
    return lambda rng, n: rng.normal(0.0, sd, n)


def _t(df: float = 2.0) -> Sampler:
    """Student-t(df). Với df=2 phương sai vô hạn nên không chuẩn hóa được."""
    return lambda rng, n: rng.standard_t(df, n)


def _skewed() -> Sampler:
    """Exp(1) - 1: lệch phải, đã tâm hóa (trung bình 0, phương sai 1)."""
    return lambda rng, n: rng.exponential(1.0, n) - 1.0


def _bimodal(loc: float = 0.8, scale: float = 0.6) -> Sampler:
    """
    0.5*N(-loc; scale^2) + 0.5*N(loc; scale^2).
    Mặc định (0.8, 0.6) cho trung bình 0, phương sai 0.36 + 0.64 = 1.
    """

    def draw(rng: np.random.Generator, n: int) -> np.ndarray:
        comp = rng.integers(0, 2, n)
        centers = np.where(comp == 0, -loc, loc)
        return rng.normal(centers, scale)

    return draw


# Mỗi kịch bản: (sampler X1, sampler X2, mô tả)
SCENARIOS: Dict[str, Tuple[Sampler, Sampler, str]] = {
    "baseline": (_normal(1), _normal(1), "X1~N(0;1), X2~N(0;1)"),
    "outlier": (_normal(1), _t(2), "X1~N(0;1), X2~t(df=2)"),
    "skewed": (_normal(1), _skewed(), "X1~N(0;1), X2~Exp(1)"),
    "bimodal": (_normal(1), _bimodal(), "X1~N(0;1), X2~Bimodal"),
    "skewed_outlier": (_skewed(), _t(2), "X1~Exp(1), X2~t(df=2)"),
    "skewed_bimodal": (_skewed(), _bimodal(), "X1~Exp(1), X2~Bimodal"),
    "outlier_bimodal": (_t(2), _bimodal(), "X1~t(df=2), X2~Bimodal"),
}

# Cho phép gọi theo số thứ tự 1-7 như trong README
SCENARIO_IDS: Dict[int, str] = {i + 1: k for i, k in enumerate(SCENARIOS)}


def _sigmoid(z: np.ndarray) -> np.ndarray:
    z = np.clip(z, -500, 500)
    return 1.0 / (1.0 + np.exp(-z))


class Simulation:
    def __init__(
        self,
        name: Union[str, int],
        n: int = 1000,
        gamma: Tuple[float, float] = (0.5, 0.5),
        beta: Tuple[float, float, float] = (0.0, 0.5, 0.5),
        tau0: float = 2.0,
        sigma: float = 1.0,
        target_treated: Optional[float] = 0.5,
        seed: Optional[int] = None,
    ):
        """
        Khởi tạo
        :param name: str | int - tên kịch bản (hoặc số thứ tự 1-8)
        :param n: int - cỡ mẫu
        :param gamma: (gamma1, gamma2) - hệ số của X1, X2 trong propensity score
        :param beta: (beta0, beta1, beta2) - hệ số của m(X)
        :param tau0: float - hiệu ứng can thiệp đồng nhất (ATE thật)
        :param sigma: float - độ lệch chuẩn của nhiễu outcome
        :param target_treated: float | None - tỉ lệ treated mục tiêu, gamma0 được
            hiệu chỉnh để đạt tỉ lệ này ở mọi kịch bản. None thì gamma0 = 0.
        :param seed: int 
        """
        if isinstance(name, int):
            if name not in SCENARIO_IDS:
                raise ValueError(f"Số thứ tự kịch bản phải trong 1..{len(SCENARIO_IDS)}")
            name = SCENARIO_IDS[name]
        if name not in SCENARIOS:
            raise ValueError(f"Kịch bản '{name}' không tồn tại. Chọn một trong: {list(SCENARIOS)}")

        self.name = name
        self.n = n
        self.gamma1, self.gamma2 = gamma
        self.beta0, self.beta1, self.beta2 = beta
        self.tau0 = tau0
        self.sigma = sigma
        self.target_treated = target_treated
        self.seed = seed

        self._draw_x1, self._draw_x2, self.description = SCENARIOS[name]
        self.rng = np.random.default_rng(seed)
        self.gamma0 = self._calibrate_gamma0()

    # ------------------------------------------------------------------
    @staticmethod
    def list_scenarios() -> pd.DataFrame:
        """Bảng các kịch bản hiện có."""
        return pd.DataFrame(
            [(i + 1, k, v[2]) for i, (k, v) in enumerate(SCENARIOS.items())],
            columns=["id", "name", "description"],
        )

    @property
    def ate(self) -> float:
        """ATE thật (hiệu ứng đồng nhất nên bằng tau0)."""
        return self.tau0

    # ------------------------------------------------------------------
    def _calibrate_gamma0(self, n_ref: int = 200_000) -> float:
        """
        Chọn gamma0 sao cho P(A=1) ~ target_treated trên mẫu tham chiếu lớn,
        bằng chia đôi. Dùng RNG riêng để không ảnh hưởng chuỗi ngẫu nhiên chính.
        """
        if self.target_treated is None:
            return 0.0
        ref = np.random.default_rng(12345)
        lin = self.gamma1 * self._draw_x1(ref, n_ref) + self.gamma2 * self._draw_x2(ref, n_ref)
        lo, hi = -50.0, 50.0
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if _sigmoid(mid + lin).mean() < self.target_treated:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    # ------------------------------------------------------------------
    def generate(self, n: Optional[int] = None, seed: Optional[int] = None) -> pd.DataFrame:
        """
        Sinh một bộ dữ liệu.
        :param n: cỡ mẫu (mặc định dùng n lúc khởi tạo)
        :param seed: nếu có thì đặt lại RNG (để tái lập); không có thì tiếp tục chuỗi hiện tại
        :return: DataFrame gồm
            X1, X2          biến nhiễu
            e               propensity score thật
            A               biến can thiệp
            m, tau          m(X) và tau(X) thật
            Y0, Y1          kết quả tiềm năng (chỉ để kiểm tra, không dùng khi ước lượng)
            Y               kết quả quan sát
        """
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        n = n or self.n
        rng = self.rng

        x1 = self._draw_x1(rng, n)
        x2 = self._draw_x2(rng, n)

        e = _sigmoid(self.gamma0 + self.gamma1 * x1 + self.gamma2 * x2)
        a = rng.binomial(1, e)

        m = self.beta0 + self.beta1 * x1 + self.beta2 * x2
        tau = np.full(n, self.tau0)
        eps = rng.normal(0.0, self.sigma, n)

        y0 = m + eps
        y1 = m + tau + eps
        y = np.where(a == 1, y1, y0)

        return pd.DataFrame(
            {"X1": x1, "X2": x2, "e": e, "A": a, "m": m, "tau": tau, "Y0": y0, "Y1": y1, "Y": y}
        )

    # ------------------------------------------------------------------
    @staticmethod
    def summary(df: pd.DataFrame, eps: float = 0.01) -> pd.Series:
        """
        Chẩn đoán overlap / độ cực đoan của dữ liệu đã sinh.
        - treated_rate: tỉ lệ A=1
        - e_outside: tỉ lệ e(X) nằm ngoài [eps, 1-eps]
        - max_weight: trọng số IPTW lớn nhất
        - ess_ratio: ESS / n của trọng số IPTW (càng nhỏ càng kém)
        """
        e, a = df["e"].to_numpy(), df["A"].to_numpy()
        e_safe = np.clip(e, 1e-12, 1 - 1e-12)  # tránh chia cho 0 khi e làm tròn về 0/1
        w = np.where(a == 1, 1 / e_safe, 1 / (1 - e_safe))
        ess = w.sum() ** 2 / (w**2).sum()
        x2 = df["X2"]
        return pd.Series(
            {
                "n": len(df),
                "treated_rate": a.mean(),
                "e_min": e.min(),
                "e_max": e.max(),
                "e_outside": ((e < eps) | (e > 1 - eps)).mean(),
                "max_weight": w.max(),
                "ess_ratio": ess / len(df)
            }
        )

    @classmethod
    def compare(cls, n: int = 2000, seed: int = 0, **kwargs) -> pd.DataFrame:
        """Chạy cả 8 kịch bản với cùng tham số và trả về bảng chẩn đoán so sánh."""
        rows = {}
        for k in SCENARIOS:
            sim = cls(k, n=n, seed=seed, **kwargs)
            rows[k] = cls.summary(sim.generate())
        return pd.DataFrame(rows).T