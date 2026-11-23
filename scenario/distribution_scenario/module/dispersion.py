"""
Nhóm 3 - Độ phân tán: kỳ vọng mọi biến = 0, chỉ phương sai của X2 thay đổi, X1 ~ N(0;1) cố định.
DispersionSimulation kế thừa Simulation (generate, summary, ate...).

Quy ước: N(0; v) với v là PHƯƠNG SAI (như nhóm 1, 2). Kịch bản: v = 1, 0.5, 2, 5, 10.
Vì X2 đối xứng quanh 0 nên gamma0 hiệu chỉnh cho P(A=1)=50% luôn xấp xỉ 0 ở mọi kịch bản
(khác nhóm 2, không cần cố định gamma0).
"""
from __future__ import annotations
from typing import Dict, Optional, Tuple, Union
import numpy as np
import pandas as pd
from .distribution import Simulation, Sampler


def _normal_var(var: float = 1.0) -> Sampler:
    sd = np.sqrt(var)
    return lambda rng, n: rng.normal(0.0, sd, n)


# (sampler X1, sampler X2, mô tả, var2)
DISPERSION_SCENARIOS: Dict[str, Tuple[Sampler, Sampler, str, float]] = {
    f"disp_v{str(v).replace('.', '')}": (_normal_var(1), _normal_var(v), f"X1~N(0;1), X2~N(0;{v:g})", float(v))
    for v in (1, 0.5, 2, 5, 10)
}
DISPERSION_IDS: Dict[int, str] = {i + 1: k for i, k in enumerate(DISPERSION_SCENARIOS)}


def dispersion_name(var2: float) -> str:
    """Đăng ký (nếu chưa có) kịch bản X2~N(0;var2) và trả về tên, dùng để quét lưới phương sai."""
    for k, v in DISPERSION_SCENARIOS.items():
        if v[3] == float(var2):
            return k
    name = f"disp_v{str(var2).replace('.', '')}"
    DISPERSION_SCENARIOS[name] = (_normal_var(1), _normal_var(var2), f"X1~N(0;1), X2~N(0;{var2:g})", float(var2))
    return name


class DispersionSimulation(Simulation):
    def __init__(self, name: Union[str, int], n: int = 1000, gamma: Tuple[float, float] = (0.5, 0.5),
                 beta: Tuple[float, float, float] = (0.0, 0.5, 0.5), tau0: float = 2.0, sigma: float = 1.0,
                 target_treated: Optional[float] = 0.5, seed: Optional[int] = None):
        if isinstance(name, int):
            if name not in DISPERSION_IDS:
                raise ValueError(f"Số thứ tự kịch bản phải trong 1..{len(DISPERSION_IDS)}")
            name = DISPERSION_IDS[name]
        if name not in DISPERSION_SCENARIOS:
            raise ValueError(f"Kịch bản '{name}' không tồn tại. Chọn một trong: {list(DISPERSION_SCENARIOS)}")
        self.name, self.n, self.seed = name, n, seed
        self.gamma1, self.gamma2 = gamma
        self.beta0, self.beta1, self.beta2 = beta
        self.tau0, self.sigma, self.target_treated = tau0, sigma, target_treated
        self._draw_x1, self._draw_x2, self.description, self.var2 = DISPERSION_SCENARIOS[name]
        self.rng = np.random.default_rng(seed)
        self.gamma0 = self._calibrate_gamma0()

    @staticmethod
    def list_scenarios() -> pd.DataFrame:
        return pd.DataFrame([(i + 1, k, v[2], v[3]) for i, (k, v) in enumerate(list(DISPERSION_SCENARIOS.items())[:5])],
                            columns=["id", "name", "description", "var2"])
