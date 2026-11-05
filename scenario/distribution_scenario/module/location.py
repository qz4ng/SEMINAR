"""
Nhóm 2 - Vị trí phân phối: chỉ kỳ vọng của X2 thay đổi, X1 ~ N(0;1) cố định.

Điểm quan trọng về gamma0
-------------------------
Nếu hiệu chỉnh lại gamma0 ở MỖI kịch bản để P(A=1)=50% thì dịch chuyển kỳ vọng của X2 chỉ làm
gamma0 trượt đi (gamma0' = gamma0 - gamma2*mu) và e(X) có đúng phân phối như baseline -> mọi kịch bản
giống hệt nhau, không còn mất cân bằng nào để khảo sát. Vì vậy ở nhóm 2 mặc định
`fix_gamma0=True`: gamma0 được hiệu chỉnh MỘT lần ở baseline (P(A=1)=50%) rồi giữ nguyên,
nên khi mu thay đổi thì tỉ lệ treated và overlap thay đổi theo.
`fix_gamma0=False` giữ cách hiệu chỉnh của nhóm 1 (dùng để chứng minh điểm trên).
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple, Union

import numpy as np
import pandas as pd

from .distribution import Simulation, Sampler


def _normal_mu(mu: float = 0.0, var: float = 1.0) -> Sampler:
    """N(mu; var), var là phương sai."""
    sd = np.sqrt(var)
    return lambda rng, n: rng.normal(mu, sd, n)


# Mỗi kịch bản: (sampler X1, sampler X2, mô tả, mu2)
LOCATION_SCENARIOS: Dict[str, Tuple[Sampler, Sampler, str, float]] = {
    "loc_baseline": (_normal_mu(0), _normal_mu(0), "X1~N(0;1), X2~N(0;1)", 0.0),
    "loc_pos1": (_normal_mu(0), _normal_mu(1), "X1~N(0;1), X2~N(1;1)", 1.0),
    "loc_neg1": (_normal_mu(0), _normal_mu(-1), "X1~N(0;1), X2~N(-1;1)", -1.0),
    "loc_pos2": (_normal_mu(0), _normal_mu(2), "X1~N(0;1), X2~N(2;1)", 2.0),
    "loc_neg2": (_normal_mu(0), _normal_mu(-2), "X1~N(0;1), X2~N(-2;1)", -2.0),
    "loc_pos5": (_normal_mu(0), _normal_mu(7), "X1~N(0;1), X2~N(7;1)", 7.0),
}
LOCATION_IDS: Dict[int, str] = {i + 1: k for i, k in enumerate(LOCATION_SCENARIOS)}


def location_name(mu2: float) -> str:
    """Đăng ký (nếu chưa có) kịch bản X2~N(mu2;1) với tên 'loc_mu{mu2}' và trả về tên - dùng để quét lưới mu."""
    for k, v in LOCATION_SCENARIOS.items():
        if v[3] == float(mu2):
            return k
    name = f"loc_mu{mu2:+g}"
    LOCATION_SCENARIOS[name] = (_normal_mu(0), _normal_mu(mu2), f"X1~N(0;1), X2~N({mu2:g};1)", float(mu2))
    return name


class LocationSimulation(Simulation):
    def __init__(
        self,
        name: Union[str, int],
        n: int = 1000,
        gamma: Tuple[float, float] = (0.5, 0.5),
        beta: Tuple[float, float, float] = (0.0, 0.5, 0.5),
        tau0: float = 2.0,
        sigma: float = 1.0,
        target_treated: Optional[float] = 0.5,
        fix_gamma0: bool = True,
        seed: Optional[int] = None,
    ):
        """
        :param name: tên kịch bản (hoặc số 1-6) trong LOCATION_SCENARIOS
        :param fix_gamma0: True -> gamma0 hiệu chỉnh ở baseline rồi giữ nguyên (mặc định cho nhóm 2);
                           False -> hiệu chỉnh lại ở từng kịch bản như nhóm 1 (e(X) không đổi theo mu).
        Các tham số còn lại giống Simulation.
        """
        if isinstance(name, int):
            if name not in LOCATION_IDS:
                raise ValueError(f"Số thứ tự kịch bản phải trong 1..{len(LOCATION_IDS)}")
            name = LOCATION_IDS[name]
        if name not in LOCATION_SCENARIOS:
            raise ValueError(f"Kịch bản '{name}' không tồn tại. Chọn một trong: {list(LOCATION_SCENARIOS)}")

        self.name, self.n, self.seed = name, n, seed
        self.gamma1, self.gamma2 = gamma
        self.beta0, self.beta1, self.beta2 = beta
        self.tau0, self.sigma, self.target_treated = tau0, sigma, target_treated
        self.fix_gamma0 = fix_gamma0
        self._draw_x1, self._draw_x2, self.description, self.mu2 = LOCATION_SCENARIOS[name]
        self.rng = np.random.default_rng(seed)

        if fix_gamma0 and target_treated is not None:
            own = (self._draw_x1, self._draw_x2)
            self._draw_x1, self._draw_x2 = LOCATION_SCENARIOS["loc_baseline"][:2]
            self.gamma0 = self._calibrate_gamma0()
            self._draw_x1, self._draw_x2 = own
        else:
            self.gamma0 = self._calibrate_gamma0()

    @staticmethod
    def list_scenarios() -> pd.DataFrame:
        return pd.DataFrame(
            [(i + 1, k, v[2], v[3]) for i, (k, v) in enumerate(list(LOCATION_SCENARIOS.items())[:6])],
            columns=["id", "name", "description", "mu2"],
        )