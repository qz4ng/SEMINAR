"""Kiểm tra learners.py. Chạy: pytest ml_scenario/tests"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dgp import Simulation  # noqa: E402
from learners import COLUMNS, LEARNER_CODES, LEARNERS, fit_nuisance, make  # noqa: E402
from sklearn.linear_model import LinearRegression  # noqa: E402


@pytest.mark.parametrize("learner", [c for c in LEARNER_CODES if c != "sl"])  # sl ~1 phút/lần, chạy tay
def test_output_shape(learner):
    df = Simulation("N3").generate(400, seed=1)
    nu = fit_nuisance(df, learner, seed=1)
    assert list(nu.columns) == COLUMNS and nu.index.equals(df.index)
    assert np.isfinite(nu.to_numpy()).all()
    assert nu["e_hat"].between(0, 1).all()


def test_same_seed_same_folds_stratified():
    df = Simulation("N3").generate(1000, seed=2)
    f1 = fit_nuisance(df, "glm", seed=7)["fold"]
    assert (f1 == fit_nuisance(df, "oracle", seed=7)["fold"]).all()
    assert not (f1 == fit_nuisance(df, "glm", seed=8)["fold"]).all()
    assert df.groupby(f1)["A"].mean().sub(df["A"].mean()).abs().max() < 0.01


def test_oracle_is_truth():
    df = Simulation("H3").generate(300, seed=3)
    nu = fit_nuisance(df, "oracle")
    assert (nu["e_hat"] == df["e"]).all()
    np.testing.assert_allclose(nu["mu1_hat"] - nu["mu0_hat"], df["tau"], atol=1e-12)


def test_glm_correct_spec_recovers_e():
    # L0: logit đúng dạng -> ê gần e thật
    df = Simulation("L0").generate(5000, seed=4)
    nu = fit_nuisance(df, "glm", seed=4)
    assert np.sqrt(((nu["e_hat"] - df["e"]) ** 2).mean()) < 0.05


def test_crossfit_is_out_of_sample():
    # rf trong mẫu khớp Y tốt hơn hẳn ngoài mẫu; nếu cross-fit rò dữ liệu thì hai số gần nhau
    df = Simulation("N3").generate(500, seed=5)
    mse = lambda nu: ((df["Y"] - nu["m_hat"]) ** 2).mean()
    in_ = fit_nuisance(df, "rf", crossfit=False)
    assert (in_["fold"] == 0).all()
    assert mse(in_) < 0.8 * mse(fit_nuisance(df, "rf", seed=5))


def test_make_is_fresh_clone():
    m = make("rf", "reg")
    assert m is not LEARNERS["rf"]["reg"] and not hasattr(m, "estimators_")
    with pytest.raises(ValueError):
        make("xgb", "reg")


def test_test_predictions():
    sim = Simulation("H1")
    df, dt = sim.generate(400, seed=1), sim.generate(300, seed=2)
    nu, nt = fit_nuisance(df, "glm", seed=1, test=dt)
    assert list(nt.columns) == COLUMNS[:4] and nt.index.equals(dt.index)
    # không cross-fit: dự đoán test chính là một OLS fit trên nhóm A=1 của toàn mẫu
    x, xt, t = df.filter(regex=r"^X\d+$"), dt.filter(regex=r"^X\d+$"), df["A"] == 1
    _, nt_in = fit_nuisance(df, "glm", crossfit=False, test=dt)
    ols = LinearRegression().fit(x[t].to_numpy(), df.loc[t, "Y"].to_numpy())
    np.testing.assert_allclose(nt_in["mu1_hat"], ols.predict(xt.to_numpy()), atol=1e-10)
    _, ot = fit_nuisance(df, "oracle", test=dt)
    assert (ot["e_hat"] == dt["e"]).all()


@pytest.mark.parametrize("learner", [c for c in LEARNERS if c != "sl"])
def test_sample_weight_is_used(learner):
    # R-learner cần hồi quy có trọng số; Pipeline gốc của sklearn không nhận sample_weight
    df = Simulation("N3").generate(400, seed=6)
    x, y = df.filter(regex=r"^X\d+$").to_numpy(), df["Y"].to_numpy()
    w = np.where(df["A"] == 1, 1.0, 0.01)
    p_w, p = make(learner, "reg").fit(x, y, sample_weight=w).predict(x), make(learner, "reg").fit(x, y).predict(x)
    assert not np.allclose(p_w, p)
