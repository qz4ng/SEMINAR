"""
simulation.py - Sinh dữ liệu mô phỏng để kiểm tra VAI TRÒ của biến nhiễu (confounder, instrument,
mediator, collider, ...) lên ước lượng ATE bao gồm 9 kịch bản.

Ý tưởng chính       
-------------
Một mô hình cấu trúc tuyến tính-logistic DUY NHẤT chứa mọi loại biến; mỗi kịch bản chỉ là một bộ tham số
"bật/tắt" các cạnh của đồ thị nhân quả (DAG). Cạnh có hệ số 0 thì không tồn tại. Nhờ vậy:
  * mọi kịch bản có cùng thang đo (biến ngoại sinh ~ N(0,1), nhiễu outcome sigma = 1);
  * "all" (mô hình đầy đủ) là phép hợp của các kịch bản đơn lẻ;
  * DAG, vai trò từng biến (utilities.classify_roles) và đáp án lý thuyết đều suy ra được từ tham số.

Mô hình (A = can thiệp 0/1, Y = kết quả)
-----------------------------------------
  ngoại sinh  : C1, C2, Z, P, U, V1, V2 ~ N(0,1) độc lập
  proxy       : W  = C1 + w_noise * N(0,1)                 (đo C1 có sai số)
  M-bias      : K0 = k0_v1*V1 + k0_v2*V2 + k0_noise*N(0,1) (collider trước can thiệp)
  can thiệp   : logit e = g0 + g_c1*C1 + g_c2*C2 + g_z*Z + g_u*U + g_v1*V1 ;  A ~ Bernoulli(e)
  mediator    : M  = a_m*A + m_noise*N(0,1)
  outcome     : Y  = tau_d*A + b_c1*C1 + b_c2*C2 + b_p*P + b_u*U + b_v2*V2 + b_m*M + sigma*N(0,1)
  collider    : K  = k_a*A + k_y*Y + k_noise*N(0,1)        (hậu quả của cả A và Y)

Hiệu ứng tổng của A lên Y (ATE, cái cần ước lượng) = tau_d + a_m*b_m   (trực tiếp + gián tiếp qua M).
Hiệu ứng trực tiếp = tau_d.

Vì mọi parents của A đều đối xứng quanh 0 nên g0 = 0 cho đúng ~50% treated ở mọi kịch bản.

Ví dụ nông nghiệp (A = áp dụng kỹ thuật tưới tiết kiệm, Y = năng suất):
  C1 chất lượng đất, C2 kinh nghiệm nông hộ (confounder) | Z khoảng cách tới trạm khuyến nông (instrument)
  P lượng mưa (chỉ ảnh hưởng năng suất) | U động lực/năng lực nông hộ không đo được (confounder ẩn)
  M độ ẩm đất sau can thiệp (mediator) | K được chọn vào danh sách hỗ trợ/khảo sát sau vụ mùa (collider)
  V1 tiếp cận tín dụng, V2 khả năng thích ứng thời tiết, K0 mức sống đo được (M-bias)
"""

from __future__ import annotations

import copy
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from utilities import sigmoid

# 1. Tham số

BASE_PARAMS: Dict[str, Optional[float]] = dict(
    tau_d=2.0, sigma=1.0, g0=0.0,
    # cạnh vào A (propensity)
    g_c1=0.0, g_c2=0.0, g_z=0.0, g_u=0.0, g_v1=0.0,
    # cạnh vào Y (outcome)
    b_c1=0.0, b_c2=0.0, b_p=0.0, b_u=0.0, b_v2=0.0, b_m=0.0,
    # mediator
    a_m=0.0, m_noise=1.0,
    # collider tiền can thiệp (M-bias)
    k0_v1=0.0, k0_v2=0.0, k0_noise=1.0,
    # collider hậu can thiệp
    k_a=0.0, k_y=0.0, k_noise=1.0,
    # proxy của C1 (None = không có proxy)
    w_noise=None,
)

# Mô tả ngắn từng tham số của BASE_PARAMS (dùng cho bảng giải thích trong notebook)
PARAM_DOC = {
    "tau_d": "Hiệu ứng trực tiếp của A lên Y",
    "sigma": "Độ lệch chuẩn nhiễu outcome",
    "g0": "Hệ số chặn của logit e(X); 0 => P(A=1)=50%",
    "g_c1": "C1 -> A", "g_c2": "C2 -> A", "g_z": "Z -> A (instrument)", "g_u": "U -> A (confounder ẩn)",
    "g_v1": "V1 -> A (M-bias)",
    "b_c1": "C1 -> Y", "b_c2": "C2 -> Y", "b_p": "P -> Y (precision)", "b_u": "U -> Y (confounder ẩn)",
    "b_v2": "V2 -> Y (M-bias)", "b_m": "M -> Y (mediator)",
    "a_m": "A -> M (mediator)", "m_noise": "Nhiễu của M",
    "k0_v1": "V1 -> K0", "k0_v2": "V2 -> K0", "k0_noise": "Nhiễu của K0",
    "k_a": "A -> K (collider hậu can thiệp)", "k_y": "Y -> K (collider hậu can thiệp)", "k_noise": "Nhiễu của K",
    "w_noise": "SD sai số đo của proxy W = C1 + w_noise*N(0,1)",
}

# các ví dụ về các biến trong nông nghiệp
VAR_LABELS = {
    "A": "A: áp dụng kỹ thuật", "Y": "Y: năng suất",
    "C1": "C1: chất lượng đất", "C2": "C2: kinh nghiệm", "Z": "Z: khoảng cách\ntrạm khuyến nông",
    "P": "P: lượng mưa", "U": "U: động lực\n(không đo)", "V1": "V1: tiếp cận\ntín dụng",
    "V2": "V2: thích ứng\nthời tiết", "K0": "K0: mức sống\n(đo được)", "M": "M: độ ẩm đất\nsau can thiệp",
    "K": "K: được chọn vào\nkhảo sát sau vụ", "W": "W: chất lượng đất\n(đo có sai số)",
}

# Vị trí các nút khi vẽ DAG (x, y); A bên trái, Y bên phải
NODE_POS = {
    "A": (0.0, 0.0), "Y": (4.0, 0.0),
    "C1": (1.3, 1.7), "C2": (2.7, 1.7), "U": (2.0, 3.1), "Z": (-1.3, 1.5), "P": (5.2, 1.5),
    "M": (2.0, -1.3), "K": (2.0, -2.6),
    "V1": (-1.3, -1.6), "V2": (5.2, -1.6), "K0": (2.0, -4.0),
    "W": (3.6, 3.1),
}

# 2. Kịch bản
def _S(label: str, adjust: Sequence[str], note: str = "") -> dict:
    return {"label": label, "adjust": list(adjust), "note": note}


SCENARIOS: Dict[str, dict] = {
    "confounder": dict(
        title="Confounder (C1 -> A, C1 -> Y)",
        role="confounder",
        params=dict(g_c1=1.0, b_c1=1.0),
        observed=["C1"],
        strategies={
            "none": _S("Không hiệu chỉnh", []),
            "C1": _S("Hiệu chỉnh C1", ["C1"], "đúng theo backdoor"),
        },
    ),
    "instrument": dict(
        title="Instrument (Z -> A, không tác động Y) cạnh một confounder quan sát được",
        role="instrument",
        params=dict(g_c1=1.0, b_c1=1.0, g_z=1.5),
        observed=["C1", "Z"],
        strategies={
            "none": _S("Không hiệu chỉnh", []),
            "C1": _S("{C1}", ["C1"], "đủ để chặn backdoor"),
            "C1+Z": _S("{C1, Z}", ["C1", "Z"], "thêm instrument"),
        },
    ),
    "precision": dict(
        title="Precision / risk factor (P -> Y, không tác động A)",
        role="precision",
        params=dict(g_c1=1.0, b_c1=1.0, b_p=1.5),
        observed=["C1", "P"],
        strategies={
            "none": _S("Không hiệu chỉnh", []),
            "C1": _S("{C1}", ["C1"]),
            "C1+P": _S("{C1, P}", ["C1", "P"], "thêm biến chỉ ảnh hưởng Y"),
        },
    ),
    "mediator": dict(
        title="Mediator (A -> M -> Y); ATE tổng = trực tiếp + gián tiếp",
        role="mediator",
        params=dict(g_c1=1.0, b_c1=1.0, tau_d=1.0, a_m=1.0, b_m=1.0),
        observed=["C1", "M"],
        strategies={
            "none": _S("Không hiệu chỉnh", []),
            "C1": _S("{C1}", ["C1"], "ước lượng hiệu ứng TỔNG"),
            "C1+M": _S("{C1, M}", ["C1", "M"], "chặn đường qua M -> chỉ còn hiệu ứng trực tiếp"),
        },
    ),
    "collider": dict(
        title="Collider hậu can thiệp (A -> K <- Y)",
        role="collider",
        params=dict(g_c1=1.0, b_c1=1.0, k_a=1.0, k_y=1.0),
        observed=["C1", "K"],
        strategies={
            "none": _S("Không hiệu chỉnh", []),
            "C1": _S("{C1}", ["C1"]),
            "C1+K": _S("{C1, K}", ["C1", "K"], "điều kiện hóa trên collider"),
        },
    ),
    "m_bias": dict(
        title="M-bias (V1 -> A, V2 -> Y, cả hai -> K0 đo được; không có confounding)",
        role="collider tiền can thiệp",
        params=dict(g_v1=1.0, b_v2=1.0, k0_v1=1.0, k0_v2=1.0),
        observed=["K0"],
        strategies={
            "none": _S("Không hiệu chỉnh", [], "đúng: không có backdoor mở"),
            "K0": _S("{K0}", ["K0"], "mở đường A <- V1 -> K0 <- V2 -> Y"),
        },
    ),
    "amplification": dict(
        title="Bias amplification (Z -> A là instrument, U ẩn là confounder)",
        role="instrument + confounder ẩn",
        params=dict(g_z=1.5, g_u=0.5, b_u=1.0),
        observed=["Z"],
        strategies={
            "none": _S("Không hiệu chỉnh", [], "vẫn chệch do U"),
            "Z": _S("{Z}", ["Z"], "hiệu chỉnh instrument"),
        },
    ),
    "proxy": dict(
        title="Proxy của confounder (C1 ẩn, chỉ đo được W = C1 + nhiễu)",
        role="proxy của confounder",
        params=dict(g_c1=1.0, b_c1=1.0, w_noise=1.0),
        observed=["W"],
        strategies={
            "none": _S("Không hiệu chỉnh", []),
            "W": _S("{W}", ["W"], "giảm một phần confounding"),
        },
    ),
    "all": dict(
        title="Kịch bản tổng hợp (mọi vai trò cùng xuất hiện)",
        role="tất cả",
        params=dict(
            g_c1=0.7, b_c1=0.7, g_c2=0.5, b_c2=0.5,            # 2 confounder
            g_z=0.8, b_p=1.0,                                  # instrument, precision
            tau_d=1.0, a_m=1.0, b_m=1.0,                       # mediator (ATE tổng = 2)
            k_a=1.0, k_y=1.0,                                  # collider hậu can thiệp
            g_v1=0.5, b_v2=0.5, k0_v1=0.8, k0_v2=0.8,          # M-bias
        ),
        observed=["C1", "C2", "Z", "P", "K0", "M", "K"],
        strategies={
            "none": _S("Không hiệu chỉnh", []),
            "conf": _S("Chỉ confounder", ["C1", "C2"], "tập tối thiểu theo backdoor"),
            "conf+P": _S("+ precision", ["C1", "C2", "P"], "tập khuyến nghị"),
            "conf+P+Z": _S("+ instrument", ["C1", "C2", "P", "Z"]),
            "pre-all": _S("Mọi biến trước can thiệp", ["C1", "C2", "P", "Z", "K0"], "kể cả collider M-bias"),
            "conf+M": _S("confounder + mediator", ["C1", "C2", "M"]),
            "conf+K": _S("confounder + collider", ["C1", "C2", "K"]),
            "all": _S("Tất cả", ["C1", "C2", "P", "Z", "K0", "M", "K"], "'cứ có biến là đưa vào'"),
        },
    ),
}
SCENARIO_ORDER = list(SCENARIOS)

# Quét độ nhạy: kịch bản -> (nhãn trục x, danh sách (giá trị trục x, ghi đè tham số))
SWEEPS = {
    "instrument": ("g_z (độ mạnh Z -> A)", [(v, {"g_z": v}) for v in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0)]),
    "precision": ("b_p (độ mạnh P -> Y)", [(v, {"b_p": v}) for v in (0.0, 0.5, 1.0, 1.5, 2.0, 3.0)]),
    "mediator": ("a_m (A -> M, với b_m = 1)", [(v, {"a_m": v}) for v in (0.0, 0.5, 1.0, 1.5, 2.0)]),
    "collider": ("s = k_a = k_y (độ mạnh collider)", [(v, {"k_a": v, "k_y": v}) for v in (0.0, 0.25, 0.5, 1.0, 1.5, 2.0)]),
    "m_bias": ("s = k0_v1 = k0_v2 (độ mạnh M-bias)", [(v, {"k0_v1": v, "k0_v2": v}) for v in (0.0, 0.5, 1.0, 1.5, 2.0, 3.0)]),
    "amplification": ("g_z (độ mạnh instrument)", [(v, {"g_z": v}) for v in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0)]),
    "proxy": ("w_noise (sai số đo; reliability = 1/(1+w_noise²))", [(v, {"w_noise": v}) for v in (0.0, 0.25, 0.5, 1.0, 2.0, 4.0)]),
}

# 3. Lớp sinh dữ liệu
class RoleSimulation:
    """
    Sinh dữ liệu theo kịch bản vai trò biến.

    :param name: tên kịch bản trong SCENARIOS
    :param n: cỡ mẫu mặc định
    :param seed: seed RNG
    :param overrides: ghi đè tham số, ví dụ RoleSimulation("collider", k_a=2.0, k_y=2.0)
    """

    def __init__(self, name: str, n: int = 1000, seed: Optional[int] = None, **overrides):
        if name not in SCENARIOS:
            raise ValueError(f"Kịch bản '{name}' không tồn tại. Chọn: {SCENARIO_ORDER}")
        unknown = set(overrides) - set(BASE_PARAMS)
        if unknown:
            raise ValueError(f"Tham số không hợp lệ: {sorted(unknown)}. Hợp lệ: {sorted(BASE_PARAMS)}")
        self.name, self.n, self.seed = name, n, seed
        self.info = copy.deepcopy(SCENARIOS[name])
        self.p = {**BASE_PARAMS, **self.info["params"], **overrides}
        self.overrides = dict(overrides)
        self.observed: List[str] = list(self.info["observed"])
        self.strategies: Dict[str, dict] = self.info["strategies"]
        self.rng = np.random.default_rng(seed)

    # ước lượng lý thuyết
    @property
    def true_ate(self) -> float:
        """Hiệu ứng tổng của A lên Y = trực tiếp + gián tiếp qua M."""
        return float(self.p["tau_d"] + self.p["a_m"] * self.p["b_m"])

    @property
    def direct_effect(self) -> float:
        return float(self.p["tau_d"])

    @property
    def variables(self) -> List[str]:
        """
        Danh sách biến có mặt (thứ tự sinh cố định), kể cả biến ẩn; không gồm A, Y, e.
        Biến có mặt nếu được tham số nào đó dùng tới hoặc nằm trong danh sách quan sát (để quét tham số về 0 vẫn còn cột).
        """
        p, obs = self.p, set(self.observed)
        used = {
            "C1": bool(p["g_c1"] or p["b_c1"] or p["w_noise"] is not None),
            "C2": bool(p["g_c2"] or p["b_c2"]),
            "Z": bool(p["g_z"]), "P": bool(p["b_p"]), "U": bool(p["g_u"] or p["b_u"]),
            "V1": bool(p["g_v1"] or p["k0_v1"]), "V2": bool(p["b_v2"] or p["k0_v2"]),
            "W": p["w_noise"] is not None,
            "K0": bool(p["k0_v1"] or p["k0_v2"]),
            "M": bool(p["a_m"] or p["b_m"]),
            "K": bool(p["k_a"] or p["k_y"]),
        }
        return [v for v in ("C1", "C2", "Z", "P", "U", "V1", "V2", "W", "K0", "M", "K") if used[v] or v in obs]

    @property
    def latent(self) -> List[str]:
        return [v for v in self.variables if v not in self.observed]

    #  DAG 
    def edges(self) -> List[Tuple[str, str, float]]:
        """Danh sách cạnh (parents, con, hệ số) với hệ số khác 0."""
        p = self.p
        cand = [
            ("C1", "A", p["g_c1"]), ("C2", "A", p["g_c2"]), ("Z", "A", p["g_z"]), ("U", "A", p["g_u"]),
            ("V1", "A", p["g_v1"]),
            ("C1", "Y", p["b_c1"]), ("C2", "Y", p["b_c2"]), ("P", "Y", p["b_p"]), ("U", "Y", p["b_u"]),
            ("V2", "Y", p["b_v2"]), ("A", "Y", p["tau_d"]),
            ("A", "M", p["a_m"]), ("M", "Y", p["b_m"]),
            ("V1", "K0", p["k0_v1"]), ("V2", "K0", p["k0_v2"]),
            ("A", "K", p["k_a"]), ("Y", "K", p["k_y"]),
        ]
        e = [(s, d, float(c)) for s, d, c in cand if c]
        if p["w_noise"] is not None:
            e.append(("C1", "W", 1.0))
        return e

    def dag(self) -> dict:
        nodes = ["A", "Y"] + self.variables
        return {"nodes": {v: {"pos": NODE_POS[v], "latent": v in self.latent, "label": VAR_LABELS[v]} for v in nodes},
                "edges": self.edges()}

    #  sinh dữ liệu 
    def generate(self, n: Optional[int] = None, seed: Optional[int] = None) -> pd.DataFrame:
        """
        Sinh một bộ dữ liệu đầy đủ (gồm cả biến ẩn). Dùng observed_view(df) để chỉ lấy phần nhìn thấy.
        Cột: các biến có mặt, e (PS thật theo mọi parents của A), A, Y.
        """
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        n = n or self.n
        p, rng = self.p, self.rng
        d: Dict[str, np.ndarray] = {}
        present = self.variables
        for v in ("C1", "C2", "Z", "P", "U", "V1", "V2"):
            if v in present:
                d[v] = rng.normal(size=n)
        zero = np.zeros(n)
        g = lambda k: d.get(k, zero)
        if p["w_noise"] is not None:
            d["W"] = d["C1"] + p["w_noise"] * rng.normal(size=n)
        if "K0" in present:
            d["K0"] = p["k0_v1"] * g("V1") + p["k0_v2"] * g("V2") + p["k0_noise"] * rng.normal(size=n)

        logit = (p["g0"] + p["g_c1"] * g("C1") + p["g_c2"] * g("C2") + p["g_z"] * g("Z")
                 + p["g_u"] * g("U") + p["g_v1"] * g("V1"))
        e = sigmoid(logit)
        a = rng.binomial(1, e)

        if "M" in present:
            d["M"] = p["a_m"] * a + p["m_noise"] * rng.normal(size=n)
        y = (p["tau_d"] * a + p["b_c1"] * g("C1") + p["b_c2"] * g("C2") + p["b_p"] * g("P")
             + p["b_u"] * g("U") + p["b_v2"] * g("V2") + p["b_m"] * g("M") + p["sigma"] * rng.normal(size=n))
        if "K" in present:
            d["K"] = p["k_a"] * a + p["k_y"] * y + p["k_noise"] * rng.normal(size=n)
        d["e"], d["A"], d["Y"] = e, a, y
        return pd.DataFrame(d)

    def observed_view(self, df: pd.DataFrame) -> pd.DataFrame:
        """Phần dữ liệu thực sự có: biến quan sát được + A + Y (không có biến ẩn, không có e thật)."""
        return df[self.observed + ["A", "Y"]]

    # tiện ích 
    def describe(self) -> pd.Series:
        return pd.Series({"kịch bản": self.name, "ATE tổng": self.true_ate, "hiệu ứng trực tiếp": self.direct_effect,
                          "biến quan sát": ", ".join(self.observed), "biến ẩn": ", ".join(self.latent) or "-"})

    @staticmethod
    def list_scenarios() -> pd.DataFrame:
        rows = []
        for k, v in SCENARIOS.items():
            s = RoleSimulation(k)
            rows.append({"kịch bản": k, "vai trò khảo sát": v["role"], "ATE tổng": s.true_ate,
                         "quan sát": ", ".join(s.observed), "ẩn": ", ".join(s.latent) or "-",
                         "tham số khác 0": ", ".join(f"{a}={b:g}" for a, b in v["params"].items())})
        return pd.DataFrame(rows)
