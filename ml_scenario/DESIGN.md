# Thiết kế cài đặt `ml_scenario` — phần 1: gói `dgp/`

Tài liệu này là đặc tả để cài đặt. Kịch bản và công thức gốc nằm ở [README.md](README.md); khi hai tài liệu lệch nhau thì README là nguồn đúng về mặt toán, file này là nguồn đúng về mặt giao diện code. Các phần `learners.py`, `estimators/`, `metrics.py`, `run.py` để trống, làm sau khi `dgp/` chạy và pilot đạt.

Quy ước chung:

- Python ≥ 3.10, chỉ dùng `numpy`, `pandas`, `scipy`. Không thêm dependency.
- Phong cách theo `scenario/distribution_scenario/distribution.py`: docstring tiếng Việt, `np.random.Generator`, hiệu chỉnh $\gamma_0$ bằng chia đôi trên mẫu tham chiếu với RNG riêng.
- Mọi hàm nuisance nhận `z: ndarray (n, d)` và trả `ndarray (n,)`. Không nhận DataFrame.
- Người phân tích chỉ được dùng các cột `X1..Xd, A, Y`. Các cột còn lại là giá trị thật, chỉ dùng cho `metrics.py`.

```
ml_scenario/
  dgp/
    __init__.py       # export Simulation, SCENARIOS, Scenario
    covariates.py
    nuisance.py
    simulate.py
  tests/test_dgp.py
  pilot_dgp.py        # chạy một lần, ghi results/pilot_dgp.csv
```

---

## 1. `dgp/covariates.py`

```python
def draw_z(rng: np.random.Generator, n: int, d: int, rho: float) -> np.ndarray
```

$Z \sim N_d(0, \Sigma)$, $\Sigma_{jk} = \rho^{|j-k|}$. Cài: `L = cholesky(toeplitz(rho ** arange(d)))`, `Z = rng.standard_normal((n, d)) @ L.T`. Với $\rho = 0$ trả thẳng `standard_normal`. Yêu cầu `d >= 5`, raise `ValueError` nếu không.

```python
def transform(z: np.ndarray, mode: Literal["identity", "ks"]) -> np.ndarray
```

Trả bản sao `x` cùng shape. `identity`: `x = z`. `ks` chỉ đổi 4 cột đầu:

$$
X_1 = e^{Z_1/2},\quad X_2 = \frac{Z_2}{1+e^{Z_1}} + 10,\quad X_3 = \Big(\frac{Z_1 Z_3}{25} + 0.6\Big)^3,\quad X_4 = (Z_2 + Z_4 + 20)^2
$$

Không chuẩn hóa $X$ sau biến đổi. Thang đo lệch nhau (X₄ cỡ 400, X₃ cỡ 0.2) là chủ ý của Kang–Schafer; learner tự lo scaling.

---

## 2. `dgp/nuisance.py`

### 2.1 Hàm thô

Ba registry, key là mã trong README:

```python
ETA_E: dict[str, Callable[[np.ndarray], np.ndarray]]   # "lin", "nl"
MU0:   dict[str, Callable[[np.ndarray], np.ndarray]]   # "lin", "nl"
TAU:   dict[str, Callable[[np.ndarray], np.ndarray]]   # "const", "lin", "nl"
```

Với $U_j = \Phi(Z_j)$ dùng `scipy.special.ndtr`.

| Registry | Key | Công thức trên $z$ |
|---|---|---|
| `ETA_E` | `lin` | $z_1 - 0.5 z_2 + 0.25 z_3 + 0.1 z_4$ (Kang–Schafer đổi dấu, xem README 1.2) |
| `ETA_E` | `nl` | $z_1 + 0.5 z_1 z_2 + 0.5 (z_3^2 - 1) + \mathbb 1\{z_4 > 0\} - 0.5$ |
| `MU0` | `lin` | $z_1 + 0.5 z_2 + 0.5 z_3 + 0.5 z_4$ |
| `MU0` | `nl` | $\sin(\pi u_1 u_2) + 2(u_3 - 0.5)^2 + u_4 + 0.5 u_5$ |
| `TAU` | `const` | $1$ (trả `np.ones(n)`) |
| `TAU` | `lin` | $1 + 0.5(z_1 + z_2)$ |
| `TAU` | `nl` | $1 + \max(z_1 + z_2 + z_3, 0) - \max(z_4 + z_5, 0)$ |

Chỉ số cột 0-based trong code: $z_1$ là `z[:, 0]`.

### 2.2 Chuẩn hóa

```python
def standardizer(kind: Literal["eta_e", "mu0"], key: str, rho: float,
                 n_ref: int = 1_000_000, seed: int = 12345) -> tuple[float, float]
```

Trả `(mean, sd)` của hàm thô trên mẫu tham chiếu $Z$ với $d = 5$ (các hàm chỉ dùng 5 cột đầu, nên hằng số **không phụ thuộc $d$**, chỉ phụ thuộc $\rho$). Cache bằng `functools.lru_cache`. `TAU` **không** chuẩn hóa.

```python
def make_nuisance(scenario) -> tuple[Callable, Callable, Callable]
```

Trả `(eta_e_std, mu0_std, tau)` đã đóng gói: `eta_e_std(z) = (ETA_E[key](z) - mean) / sd`, tương tự `mu0_std`. Đây là $\tilde\eta_e$, $\tilde\mu_0$ trong README.

---

## 3. `dgp/simulate.py`

### 3.1 Kịch bản

```python
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
```

`SCENARIOS: dict[str, Scenario]` gồm đúng 10 mã L0, L1, N1, N2, N3, O1, H1, H2, H3, D1 với tham số theo bảng mục 2 của README. Cột `question` chép từ README để `list_scenarios()` in ra được.

### 3.2 `Simulation`

```python
class Simulation:
    def __init__(self, scenario: str | Scenario, seed: int | None = None): ...
    gamma0: float          # hiệu chỉnh lúc __init__
    ate: float             # giá trị thật, tính lúc __init__
    def generate(self, n: int, seed: int | None = None) -> pd.DataFrame: ...
    @staticmethod
    def summary(df: pd.DataFrame, eps: float = 0.05) -> pd.Series: ...
    @staticmethod
    def list_scenarios() -> pd.DataFrame: ...
```

**`__init__`**

1. Tra `SCENARIOS` nếu truyền `str`.
2. `self.eta_e, self.mu0, self.tau = make_nuisance(scenario)`.
3. Hiệu chỉnh $\gamma_0$: mẫu tham chiếu `n_ref = 200_000`, `default_rng(12345)`, chia đôi 80 vòng trên $[-50, 50]$ để `mean(sigmoid(gamma0 + kappa * eta_e(z))) ≈ target_treated`. Y hệt `_calibrate_gamma0` của `distribution.py`.
4. ATE thật bằng **dạng đóng** (README 1.4): `const`, `lin` trả `1.0`; `nl` trả $1 + \sqrt{v_1/2\pi} - \sqrt{v_2/2\pi}$ với $v_1 = 3 + 2(2\rho+\rho^2)$, $v_2 = 2 + 2\rho$. Không Monte Carlo, để sai số MC không lẫn vào bias ước lượng.

**`generate(n, seed)`**

```
z   = draw_z(rng, n, d, rho)
x   = transform(z, h)
e   = sigmoid(gamma0 + kappa * eta_e(z))      # sigmoid có clip ±500
A   = rng.binomial(1, e)
mu0 = mu0(z);  tau = tau(z)
eps = rng.normal(0, sigma, n)
Y0  = mu0 + eps;  Y1 = mu0 + tau + eps;  Y = where(A == 1, Y1, Y0)
```

Thứ tự gọi RNG cố định như trên để `seed` tái lập được. Trả DataFrame cột:

| Cột | Ý nghĩa | Ai dùng |
|---|---|---|
| `X1..Xd` | biến quan sát $h(Z)$ | estimator |
| `A`, `Y` | điều trị, kết quả | estimator |
| `e` | $e(Z)$ thật | metrics (RMSE của $\hat e$, overlap) |
| `mu0`, `tau` | $\tilde\mu_0(Z)$, $\tau(Z)$ thật; $\mu_1 = $ `mu0 + tau` | metrics (RMSE của $\hat\mu_a$, PEHE) |
| `Y0`, `Y1` | kết quả tiềm năng | kiểm tra |

**Không** trả $Z$. Nếu cần debug thì thêm `return_z: bool = False`, mặc định tắt.

**`summary(df, eps=0.05)`**: giống `distribution.py` nhưng `eps` mặc định 0.05 theo README, thêm `naive_bias = mean(Y|A=1) - mean(Y|A=0) - ate` (truyền `ate` vào, hoặc làm instance method).

### 3.3 Seed cho mô phỏng lặp

Một lần chạy $(\text{scenario}, n)$ với $R$ lần lặp dùng `np.random.SeedSequence(base_seed).spawn(R)`, lần lặp $r$ gọi `generate(n, seed=child[r])`. `run.py` sẽ dùng quy ước này; ghi ở đây để `generate` nhận được `SeedSequence` hoặc `int`.

---

## 4. Kiểm tra: `tests/test_dgp.py`

Chạy bằng `pytest`, mỗi test dưới 5 giây.

| # | Kiểm tra | Ngưỡng |
|---|---|---|
| 1 | cùng `seed` → hai `generate` cho DataFrame bằng nhau | `assert_frame_equal` |
| 2 | `Y == where(A==1, Y1, Y0)` và `Y1 - Y0 == tau` | exact |
| 3 | tỉ lệ treated ở $n = 10^5$, mọi kịch bản | $|\bar A - 0.5| < 0.01$ |
| 4 | phương sai của `eta_e_std(z)`, `mu0_std(z)` ở $n = 10^5$, $\rho = 0.3$ | $|\mathrm{Var} - 1| < 0.03$ |
| 5 | `ate` của `t-const` | `== 1.0` |
| 6 | `ate` của `t-lin` | `== 1.0`; MC $10^6$ khớp trong 0.005 |
| 7 | `ate` của `t-nl` là dạng đóng; kiểm tra chéo bằng `mean(tau(z))` Monte Carlo $10^6$ | $|\text{MC} - \text{ate}| < 0.005$; `ate` $\approx 1.1916$ tại $\rho = 0.3$ |
| 8 | `ks`: mọi giá trị hữu hạn; `X2` trung bình trong $[9.5, 10.5]$; `X4 > 0` | |
| 9 | D1 ($d = 100$): hoán vị ngẫu nhiên các cột $Z_6..Z_{100}$ không đổi `e, mu0, tau` | exact (cùng seed, so sánh qua `return_z`) hoặc kiểm tra gián tiếp qua hàm nuisance |
| 10 | overlap: `e_outside(0.05)` của O1 lớn hơn của N3 | strict |

Test 7 là mốc độc lập với code: $E[\max(S, 0)] = \sqrt{v/2\pi}$ với $S \sim N(0, v)$.

---

## 5. Pilot: `pilot_dgp.py`

Chạy một lần sau khi test xanh, $n = 10^6$ mỗi kịch bản, ghi `results/pilot_dgp.csv` một dòng mỗi mã:

```
code | gamma0 | ate | treated | e_outside_05 | max_weight | ess_ratio | naive_bias | cov_eta_mu0 | r2_mu0
```

- `cov_eta_mu0` $= \mathrm{Cov}(\tilde\eta_e, \tilde\mu_0)$: độ mạnh confounding thực, cùng tinh thần lưu ý ở `variable_scenario`. Nếu một kịch bản có $|\text{naive\_bias}| < 0.2$ thì confounding quá yếu để phân biệt phương pháp, cần đổi hàm.
- `r2_mu0` $= \mathrm{Var}(\tilde\mu_0) / \mathrm{Var}(Y_0)$, kỳ vọng $\approx 0.5$.
- Số liệu pilot được chép vào README mục 5 và **khóa** tham số trước khi viết estimator.

---

## 6. Các phần để trống

```
learners.py       # TODO sau pilot
estimators/       # ra.py iptw.py aipw.py tmle.py dml.py meta.py — TODO
metrics.py        # TODO
run.py            # TODO; dùng quy ước seed ở mục 3.3 và long format ở README mục 4
```
