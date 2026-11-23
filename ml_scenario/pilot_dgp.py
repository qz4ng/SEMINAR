"""
Pilot DGP (DESIGN.md mục 5): n = 10^6 mỗi kịch bản, ghi results/pilot_dgp.csv.
Chạy: python ml_scenario/pilot_dgp.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

from dgp import SCENARIOS, Simulation

N, CHUNK = 1_000_000, 100_000  # sinh theo khối để D1 (d=100) không chiếm vài GB RAM
OUT = Path(__file__).resolve().parent / "results" / "pilot_dgp.csv"


def pilot(code: str) -> dict:
    sim = Simulation(code)
    keep = ["A", "Y", "e", "mu0", "tau", "Y0"]
    df = pd.concat(
        [sim.generate(CHUNK, seed=ss)[keep] for ss in np.random.SeedSequence(2026).spawn(N // CHUNK)],
        ignore_index=True,
    )
    s = Simulation.summary(df, eps=0.05, ate=sim.ate)
    eta = (logit(df["e"]) - sim.gamma0) / sim.scenario.kappa  # η̃_e(Z), suy ngược từ e
    return {
        "code": code,
        "gamma0": sim.gamma0,
        "ate": sim.ate,
        "treated": s["treated_rate"],
        "e_outside_05": s["e_outside"],
        "max_weight": s["max_weight"],
        "ess_ratio": s["ess_ratio"],
        "naive_bias": s["naive_bias"],
        "cov_eta_mu0": np.cov(eta, df["mu0"])[0, 1],
        "r2_mu0": df["mu0"].var() / df["Y0"].var(),
    }


if __name__ == "__main__":
    res = pd.DataFrame([pilot(c) for c in SCENARIOS])
    OUT.parent.mkdir(exist_ok=True)
    res.to_csv(OUT, index=False)
    with pd.option_context("display.width", 200, "display.float_format", "{:.4f}".format):
        print(res.to_string(index=False))
    weak = res.loc[res["naive_bias"].abs() < 0.2, "code"].tolist()
    if weak:
        print(f"\nCẢNH BÁO: |naive_bias| < 0.2 ở {weak}: confounding quá yếu, cần đổi hàm.")
