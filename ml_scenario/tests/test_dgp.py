"""Kiểm tra gói dgp/ theo DESIGN.md mục 4. Chạy: pytest ml_scenario/tests"""

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dgp import SCENARIOS, Simulation  # noqa: E402
from dgp.covariates import draw_z, transform  # noqa: E402
from dgp.nuisance import make_nuisance  # noqa: E402


def test_same_seed_same_data():
    sim = Simulation("H3")
    pd.testing.assert_frame_equal(sim.generate(500, seed=7), sim.generate(500, seed=7))
    ss = np.random.SeedSequence(1).spawn(2)[1]
    pd.testing.assert_frame_equal(sim.generate(500, seed=ss), Simulation("H3").generate(500, seed=ss))


def test_potential_outcomes_consistent():
    df = Simulation("H3").generate(2000, seed=1)
    assert (df["Y"] == np.where(df["A"] == 1, df["Y1"], df["Y0"])).all()
    np.testing.assert_allclose(df["Y1"] - df["Y0"], df["tau"], atol=1e-12)


@pytest.mark.parametrize("code", list(SCENARIOS))
def test_treated_rate(code):
    df = Simulation(code).generate(100_000, seed=2)
    assert abs(df["A"].mean() - 0.5) < 0.01


@pytest.mark.parametrize("key", [("lin", "lin"), ("nl", "nl")])
def test_standardized_variance(key):
    eta_e, mu0, _ = make_nuisance(replace(SCENARIOS["L0"], eta_e=key[0], mu0=key[1]))
    z = draw_z(np.random.default_rng(3), 100_000, 10, 0.3)
    assert abs(eta_e(z).var() - 1) < 0.03
    assert abs(mu0(z).var() - 1) < 0.03


def test_ate_const():
    assert Simulation("N3").ate == 1.0


def _mc_ate(sim, n=10**6):
    return sim.tau(draw_z(np.random.default_rng(54321), n, 5, sim.scenario.rho)).mean()


def test_ate_lin():
    sim = Simulation("H1")
    assert sim.ate == 1.0
    assert abs(_mc_ate(sim) - sim.ate) < 0.005


def test_ate_nl_closed_form():
    rho = 0.3
    v1, v2 = 3 + 2 * (2 * rho + rho**2), 2 + 2 * rho
    truth = 1 + np.sqrt(v1 / (2 * np.pi)) - np.sqrt(v2 / (2 * np.pi))
    assert abs(truth - 1.1916) < 1e-4
    sim = Simulation("H3")
    assert sim.ate == pytest.approx(truth, rel=1e-12)
    assert abs(_mc_ate(sim) - sim.ate) < 0.005


def test_e_lin_sign():
    # chốt hướng confounding: e-lin đã đổi dấu để Cov(η̃_e, μ̃0) > 0 như e-nl
    eta_e, mu0, _ = make_nuisance(SCENARIOS["L0"])
    z = draw_z(np.random.default_rng(9), 10**5, 5, 0.3)
    assert np.cov(eta_e(z), mu0(z))[0, 1] > 0


def test_ks_transform():
    x = transform(draw_z(np.random.default_rng(4), 100_000, 10, 0.3), "ks")
    assert np.isfinite(x).all()
    assert 9.5 <= x[:, 1].mean() <= 10.5
    assert (x[:, 3] > 0).all()


def test_noise_columns_irrelevant():
    z = draw_z(np.random.default_rng(5), 5000, 100, 0.3)
    zp = z.copy()
    zp[:, 5:] = zp[:, 5:][:, np.random.default_rng(6).permutation(95)]
    for f in make_nuisance(SCENARIOS["D1"]):
        assert (f(z) == f(zp)).all()


def test_weak_overlap():
    o1 = Simulation.summary(Simulation("O1").generate(100_000, seed=8))
    n3 = Simulation.summary(Simulation("N3").generate(100_000, seed=8))
    assert o1["e_outside"] > n3["e_outside"]
