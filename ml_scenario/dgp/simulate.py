"""
Ghép DGP chung (xem README.md mục 1–2):
    Z ~ N_d(0, Σ),  X = h(Z)
    e(Z) = sigmoid(gamma0 + kappa * η̃_e(Z)),  A ~ Bernoulli(e)
    Y = μ̃0(Z) + A * τ(Z) + eps,  eps ~ N(0, sigma^2)
Người phân tích chỉ được dùng X1..Xd, A, Y. Các cột còn lại là giá trị thật cho metrics.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Literal, Optional, Union

import numpy as np
import pandas as pd

from .covariates import draw_z, transform
from .nuisance import make_nuisance

Seed = Union[int, np.random.SeedSequence, None]


@dataclass(frozen=True)
class Scenario:
    code: str
    h: Literal["identity", "ks"]
    eta_e: Literal["lin", "nl"]
    mu0: Literal["lin", "nl"]
    tau: Literal["const", "lin", "nl"]
    kappa: float = 1.0
    d: int = 10
    rho: float = 0.3
    sigma: float = 1.0
    target_treated: float = 0.5
    question: str = ""


def _sc(code, h, eta_e, mu0, tau, kappa=1.0, d=10, question=""):
    return Scenario(code, h, eta_e, mu0, tau, kappa=kappa, d=d, question=question)


# Bảng mục 2 của README
SCENARIOS: Dict[str, Scenario] = {
    s.code: s
    for s in [
        _sc("L0", "identity", "lin", "lin", "const",
            question="mốc: Mô hình dự đoán đúng dạng, ML mất bao nhiêu hiệu quả?"),
        _sc("L1", "ks", "lin", "lin", "const",
            question="Kang–Schafer: Mô hình dự doán sai dạng cả hai; ML + cross-fit có cứu được không?"),
        _sc("N1", "identity", "nl", "lin", "const",
            question="chỉ PS sai dạng: double robustness của AIPW/TMLE/DML"),
        _sc("N2", "identity", "lin", "nl", "const",
            question="chỉ outcome sai dạng"),
        _sc("N3", "identity", "nl", "nl", "const",
            question="cả hai phi tuyến: cần ML; so sánh có và không cross-fitting"),
        _sc("O1", "identity", "nl", "nl", "const", kappa=2.0,
            question="overlap yếu: IPTW nổ, TMLE so với AIPW khi trọng số cực đoan"),
        _sc("H1", "identity", "nl", "nl", "lin",
            question="CATE với τ đơn giản, μ0 phức tạp"),
        _sc("H2", "identity", "nl", "lin", "nl",
            question="CATE với τ phức tạp, μ0 đơn giản"),
        _sc("H3", "identity", "nl", "nl", "nl",
            question="cả hai phức tạp"),
        _sc("D1", "identity", "nl", "nl", "lin", d=100,
            question="cao chiều, 95 biến thừa: sparsity, lasso/GBM, DML"),
    ]
}


def _sigmoid(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, -500, 500)
    return 1.0 / (1.0 + np.exp(-x))


class Simulation:
    def __init__(self, scenario: Union[str, Scenario], seed: Seed = None):
        """
        :param scenario: mã kịch bản (L0, L1, ...) hoặc một Scenario tự định nghĩa
        :param seed: int | SeedSequence - khởi tạo RNG chính cho generate()
        """
        if isinstance(scenario, str):
            if scenario not in SCENARIOS:
                raise ValueError(f"Kịch bản '{scenario}' không tồn tại. Chọn một trong: {list(SCENARIOS)}")
            scenario = SCENARIOS[scenario]
        self.scenario = scenario
        self.rng = np.random.default_rng(seed)
        self.eta_e, self.mu0, self.tau = make_nuisance(scenario)
        self.gamma0 = self._calibrate_gamma0()
        self.ate = self._true_ate()

    # ------------------------------------------------------------------
    @staticmethod
    def list_scenarios() -> pd.DataFrame:
        """Bảng các kịch bản hiện có."""
        return pd.DataFrame([asdict(s) for s in SCENARIOS.values()])

    # ------------------------------------------------------------------
    def _calibrate_gamma0(self, n_ref: int = 200_000) -> float:
        """
        Chọn gamma0 sao cho P(A=1) ~ target_treated trên mẫu tham chiếu, bằng chia đôi.
        RNG riêng để không ảnh hưởng chuỗi ngẫu nhiên chính. d = 5 vì η_e chỉ dùng 5 cột đầu.
        """
        s = self.scenario
        lin = s.kappa * self.eta_e(draw_z(np.random.default_rng(12345), n_ref, 5, s.rho))
        lo, hi = -50.0, 50.0
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if _sigmoid(mid + lin).mean() < s.target_treated:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    def _true_ate(self) -> float:
        """
        ATE = E[τ(Z)] bằng dạng đóng (README 1.4), không Monte Carlo.
        t-nl: E[max(S, 0)] = sqrt(v / 2π) với S ~ N(0, v); S1 = Z1+Z2+Z3, S2 = Z4+Z5.
        """
        tau, rho = self.scenario.tau, self.scenario.rho
        if tau in ("const", "lin"):
            return 1.0
        if tau == "nl":
            v1, v2 = 3 + 2 * (2 * rho + rho**2), 2 + 2 * rho
            return float(1 + np.sqrt(v1 / (2 * np.pi)) - np.sqrt(v2 / (2 * np.pi)))
        raise NotImplementedError(f"Chưa có dạng đóng cho ATE của tau='{tau}'")

    # ------------------------------------------------------------------
    def generate(self, n: int, seed: Seed = None) -> pd.DataFrame:
        """
        Sinh một bộ dữ liệu.
        :param n: cỡ mẫu
        :param seed: int | SeedSequence - nếu có thì đặt lại RNG; không có thì tiếp tục chuỗi hiện tại
        :return: DataFrame gồm
            X1..Xd     biến quan sát h(Z)         (estimator)
            A, Y       điều trị, kết quả          (estimator)
            e          propensity score thật      (metrics)
            mu0, tau   μ̃0(Z), τ(Z) thật; μ1 = mu0 + tau  (metrics)
            Y0, Y1     kết quả tiềm năng          (kiểm tra)
        """
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        rng, s = self.rng, self.scenario

        # Thứ tự gọi RNG cố định: Z, A, eps
        z = draw_z(rng, n, s.d, s.rho)
        x = transform(z, s.h)
        e = _sigmoid(self.gamma0 + s.kappa * self.eta_e(z))
        a = rng.binomial(1, e)
        mu0 = self.mu0(z)
        tau = self.tau(z)
        eps = rng.normal(0.0, s.sigma, n)
        y0 = mu0 + eps
        y1 = mu0 + tau + eps
        y = np.where(a == 1, y1, y0)

        df = pd.DataFrame(x, columns=[f"X{j + 1}" for j in range(s.d)])
        df["A"], df["Y"], df["e"], df["mu0"], df["tau"], df["Y0"], df["Y1"] = a, y, e, mu0, tau, y0, y1
        return df

    # ------------------------------------------------------------------
    @staticmethod
    def summary(df: pd.DataFrame, eps: float = 0.05, ate: Optional[float] = None) -> pd.Series:
        """
        Chẩn đoán overlap / độ cực đoan của dữ liệu đã sinh.
        - treated_rate: tỉ lệ A=1
        - e_outside: tỉ lệ e nằm ngoài [eps, 1-eps]
        - max_weight: trọng số IPTW lớn nhất
        - ess_ratio: ESS / n của trọng số IPTW
        - naive_bias: mean(Y|A=1) - mean(Y|A=0) - ate (chỉ khi truyền ate)
        """
        e, a, y = df["e"].to_numpy(), df["A"].to_numpy(), df["Y"].to_numpy()
        e_safe = np.clip(e, 1e-12, 1 - 1e-12)  # tránh chia cho 0 khi e làm tròn về 0/1
        w = np.where(a == 1, 1 / e_safe, 1 / (1 - e_safe))
        out = {
            "n": len(df),
            "treated_rate": a.mean(),
            "e_min": e.min(),
            "e_max": e.max(),
            "e_outside": ((e < eps) | (e > 1 - eps)).mean(),
            "max_weight": w.max(),
            "ess_ratio": w.sum() ** 2 / (w**2).sum() / len(df),
        }
        if ate is not None:
            out["naive_bias"] = y[a == 1].mean() - y[a == 0].mean() - ate
        return pd.Series(out)
