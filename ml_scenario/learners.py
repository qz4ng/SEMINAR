"""
Thư viện learner dùng chung cho nuisance (README mục 3.2) và cross-fitting (README 1.5, 6).
Mọi estimator lấy learner từ đây, nên khác biệt giữa estimator không lẫn với khác biệt cấu hình.

Dùng:
    from dgp import Simulation
    from learners import LEARNER_CODES, fit_nuisance, make

    sim = Simulation("H3")
    df, df_test = sim.generate(1000, seed=1), sim.generate(2000, seed=2)
    nu = fit_nuisance(df, "gbm", seed=1)                       # e_hat, mu0_hat, mu1_hat, m_hat, fold (ngoài mẫu)
    nu, nu_test = fit_nuisance(df, "gbm", seed=1, test=df_test) # thêm dự đoán trên mẫu test (PEHE, README 4)
    nu_in = fit_nuisance(df, "gbm", crossfit=False)             # không cross-fit (biến thể N3)
    reg = make("rf", "reg")                                     # learner mới cho bước 2 của S/X/R/DR-learner
    reg.fit(X, pseudo_y, sample_weight=w)                       # mọi learner nhận sample_weight (R-learner cần)

Mã: glm, lasso, rf, gbm, sl, oracle. `oracle` trả nuisance thật (cận trên), không fit.
`clf` ước lượng e(X) = P(A=1|X); `reg` ước lượng μ_a(X) và m(X) = E[Y|X].
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd
import sklearn
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, StackingClassifier, StackingRegressor
from sklearn.linear_model import LassoCV, LinearRegression, LogisticRegression, LogisticRegressionCV
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


class _Scaled(Pipeline):
    """StandardScaler + mô hình, nhận fit(X, y, sample_weight) như estimator thường (Pipeline gốc thì không)."""

    def fit(self, X, y, sample_weight=None):
        kw = {} if sample_weight is None else {f"{self.steps[-1][0]}__sample_weight": sample_weight}
        return super().fit(X, y, **kw)


def _scaled(model):
    return _Scaled([("scale", StandardScaler()), ("model", model)])


def _gbm(model, scoring):
    # "tuning nhẹ bằng CV" (README 3.2): 4 tổ hợp x 3 fold, refit trên toàn phần train.
    # LightGBM n_jobs=1, song song ở GridSearchCV: với n vài nghìn nhanh hơn cho LightGBM tự chia luồng.
    return GridSearchCV(model, {"n_estimators": [100, 300], "num_leaves": [4, 15]},
                        cv=3, scoring=scoring, n_jobs=-1)


_LGBM = dict(learning_rate=0.05, n_jobs=1, random_state=0, verbose=-1)
_RF = dict(n_estimators=300, min_samples_leaf=5, n_jobs=-1, random_state=0)
# sklearn >= 1.8 bỏ penalty= và dùng l1_ratios; bản 1.7 (Python 3.10 trong uv.lock) bỏ qua l1_ratios nếu thiếu penalty="l1"
_L1 = (dict(l1_ratios=(1.0,), use_legacy_attributes=False)
       if tuple(map(int, sklearn.__version__.split(".")[:2])) >= (1, 8) else dict(penalty="l1"))

_BASE = {
    "glm": {
        # C=inf: logistic không phạt; StandardScaler chỉ giúp hội tụ (X4 cỡ 400 ở h = ks), không đổi nghiệm
        "clf": _scaled(LogisticRegression(C=np.inf, max_iter=2000)),
        "reg": LinearRegression(),
    },
    "lasso": {
        "clf": _scaled(LogisticRegressionCV(
            Cs=10, solver="saga", **_L1, scoring="neg_log_loss", cv=5, max_iter=2000, random_state=0)),
        "reg": _scaled(LassoCV(cv=5, max_iter=5000, random_state=0)),
    },
    "rf": {
        "clf": RandomForestClassifier(**_RF),
        "reg": RandomForestRegressor(max_features=1 / 3, **_RF),  # mtry = p/3 như randomForest (R); nhanh hơn ~2x
    },
    "gbm": {
        "clf": _gbm(LGBMClassifier(**_LGBM), "neg_log_loss"),
        "reg": _gbm(LGBMRegressor(**_LGBM), "neg_mean_squared_error"),
    },
}

LEARNERS = {
    **_BASE,
    # Super Learner: xếp chồng 4 learner trên, meta-learner fit trên dự đoán ngoài mẫu 5 fold;
    # regression dùng NNLS (LinearRegression positive=True) như SuperLearner của van der Laan.
    "sl": {
        "clf": StackingClassifier([(k, v["clf"]) for k, v in _BASE.items()],
                                  final_estimator=LogisticRegression(), cv=5),
        "reg": StackingRegressor([(k, v["reg"]) for k, v in _BASE.items()],
                                 final_estimator=LinearRegression(positive=True), cv=5),
    },
}
LEARNER_CODES = (*LEARNERS, "oracle")
COLUMNS = ["e_hat", "mu0_hat", "mu1_hat", "m_hat", "fold"]


def make(learner: str, task: Literal["clf", "reg"]):
    """Bản clone chưa fit của learner, để không ai sửa nhầm cấu hình gốc."""
    if learner not in LEARNERS:
        raise ValueError(f"Learner '{learner}' không tồn tại. Chọn một trong: {list(LEARNERS)}")
    return clone(LEARNERS[learner][task])


def _x(df: pd.DataFrame) -> np.ndarray:
    return df.filter(regex=r"^X\d+$").to_numpy(float)


def _oracle(df: pd.DataFrame) -> dict:
    e, mu0 = df["e"].to_numpy(float), df["mu0"].to_numpy(float)
    mu1 = mu0 + df["tau"].to_numpy(float)
    return {"e_hat": e, "mu0_hat": mu0, "mu1_hat": mu1, "m_hat": e * mu1 + (1 - e) * mu0}


def fit_nuisance(df: pd.DataFrame, learner: str, K: int = 5, seed=None, crossfit: bool = True,
                 test: pd.DataFrame | None = None):
    """
    Ước lượng ê(X), μ̂0(X), μ̂1(X), m̂(X) = E[Y|X] MỘT lần cho mỗi lần lặp; mọi estimator dùng chung.
    - crossfit=True: K fold phân tầng theo A, mỗi quan sát được dự đoán bởi mô hình không thấy nó.
      Cùng seed -> cùng phân hoạch, nên các learner trong một lần lặp dùng chung fold (README 1.5).
    - crossfit=False: fit và dự đoán trên toàn mẫu (biến thể minh họa ở N3); fold = 0.
    μ̂a fit trên nhóm A = a của phần train. Chỉ đọc X1..Xd, A, Y (oracle đọc thêm e, mu0, tau).
    Không clip ê: trimming là việc của estimator (vd IPTW cắt ở [0.01, 0.99]).
    :param seed: int | SeedSequence | None, quyết định phân hoạch fold
    :param test: mẫu test độc lập (tùy chọn); dự đoán trên test = trung bình K mô hình của các fold
    :return: DataFrame cùng index với df, cột COLUMNS; nếu có test thì trả (nu, nu_test)
    """
    if learner not in LEARNER_CODES:
        raise ValueError(f"Learner '{learner}' không tồn tại. Chọn một trong: {list(LEARNER_CODES)}")
    x, a, y = _x(df), df["A"].to_numpy(int), df["Y"].to_numpy(float)
    n = len(df)

    fold = np.zeros(n, dtype=int)
    if crossfit:
        rs = int(np.random.default_rng(seed).integers(2**31))  # StratifiedKFold không nhận SeedSequence
        for k, (_, te) in enumerate(StratifiedKFold(K, shuffle=True, random_state=rs).split(x, a)):
            fold[te] = k

    if learner == "oracle":
        pred, pred_test = _oracle(df), (None if test is None else _oracle(test))
    else:
        x_test = None if test is None else _x(test)
        # cột -> (task, nhóm quan sát dùng để fit, biến đích)
        spec = {"e_hat": ("clf", np.ones(n, bool), a), "mu0_hat": ("reg", a == 0, y),
                "mu1_hat": ("reg", a == 1, y), "m_hat": ("reg", np.ones(n, bool), y)}
        pred = {c: np.empty(n) for c in spec}
        pred_test = None if test is None else {c: np.zeros(len(test)) for c in spec}
        folds = np.unique(fold)
        for k in folds:
            te = fold == k
            tr = ~te if crossfit else te
            for c, (task, rows, target) in spec.items():
                g = tr & rows
                mdl = make(learner, task).fit(x[g], target[g])
                predict = (lambda X: mdl.predict_proba(X)[:, 1]) if task == "clf" else mdl.predict
                pred[c][te] = predict(x[te])
                if test is not None:
                    pred_test[c] += predict(x_test) / len(folds)

    nu = pd.DataFrame({**pred, "fold": fold}, index=df.index)
    return nu if test is None else (nu, pd.DataFrame(pred_test, index=test.index))
