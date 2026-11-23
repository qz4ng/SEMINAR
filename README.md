# ra_causal: thí nghiệm mô phỏng cho ước lượng nhân quả

Repo gồm hai khối:

- **Thí nghiệm mô phỏng** (`scenario/`, `ml_scenario/`): sinh dữ liệu có đáp án biết trước, rồi so sánh các phương pháp ước lượng ATE/CATE (Naive, OLS, IPTW, AIPW, sau này thêm TMLE, DML, Meta-learner, BCF).
- **Pipeline tiền xử lý** P01–P09 (`src/`, `tests/`, `configs/`, `ui/`) cho dữ liệu khảo sát cover cropping → năng suất khoai tây.

README này (branch `version_2.0`) **chỉ mô tả khối thí nghiệm**. Khối pipeline giữ nguyên như `version_1.0`, xem [mục 6](#6-khối-pipeline-tạm-chưa-cập-nhật).

---

## 1. Cấu trúc sau refactor

```
ra_causal/
├── requirements.txt                 # thư viện, chia nhóm (mục 2)
├── scenario/                        # nhóm thống kê: DGP tuyến tính, 2 confounder, X = Z
│   ├── baseline.ipynb               # kịch bản gốc, có SE cho cả 4 phương pháp
│   ├── distribution_scenario/       # đổi phân phối của biến nhiễu
│   │   ├── module/                  # package: distribution, location, dispersion, balance, methods, evaluation
│   │   ├── notebook/                # location_test, dispersion_test, shape_test (mỗi nhóm kịch bản một notebook)
│   │   ├── pic/                     # hình minh họa phân phối
│   │   └── run.ipynb, *.py          # bản phẳng cũ, giữ lại để run.ipynb chạy được
│   ├── variable_scenario/           # đổi kiểu biến, thêm biến, kịch bản bất lợi cho OLS
│   │   ├── variable_type.ipynb      # phần A: T0–T6
│   │   ├── add_variable.ipynb       # phần B: V0–V5
│   │   ├── ols_unfavorable.ipynb    # phần D: H0–H3, M1a–M1c
│   │   └── results/                 # CSV long format, bảng tổng hợp, hình figures_A/ B/ D/
│   └── role_scenario/               # vai trò của biến (confounder, instrument, mediator, collider...) và tập hiệu chỉnh
│       ├── roles_test.ipynb         # 9 kịch bản, Monte Carlo, quét tham số, kết luận
│       ├── simulation.py, evaluation.py, balance.py, utilities.py
│       └── DAG.png, README.md
└── ml_scenario/                     # nhóm học máy: DGP chung, Z ẩn, X = h(Z)
    ├── README.md                    # kịch bản, công thức, phương pháp, kỳ vọng
    ├── DESIGN.md                    # đặc tả giao diện code
    ├── dgp/                         # covariates.py, nuisance.py, simulate.py
    ├── learners.py                  # cấu hình learner dùng chung + cross-fitting (glm, lasso, rf, gbm, sl, oracle)
    ├── pilot_dgp.py                 # pilot n = 10^6, ghi results/pilot_dgp.csv
    └── tests/                       # test_dgp.py (21 test), test_learners.py (15 test)
```

`main` chưa có khối thí nghiệm; toàn bộ `scenario/` và `ml_scenario/` vào `main` qua PR của `version_2.0`. Các bước refactor:

| Thư mục | Bản đầu | Hiện tại |
|---|---|---|
| `distribution_scenario/` | 3 file `.py` phẳng + `run.ipynb`, 8 kịch bản | Code tách thành package `module/` (thêm `location.py`, `dispersion.py`, `evaluation.py`); mỗi nhóm kịch bản (vị trí, độ phân tán, hình dạng) một notebook trong `notebook/`. Bản phẳng cũ vẫn giữ |
| `variable_scenario/` | R = 200, seed 20261012, n ∈ {500, 2000} (T6 thêm 8000), phần D chưa có kết quả, báo cáo `BAO_CAO_KET_QUA.md` | R = 1000, seed 20261021, cùng lưới n = 250…8000 cho cả phần A, B, D. CSV long format thêm cột `truth`, `status`. Hình theo n tách vào `figures_A/B/D/`. Báo cáo cũ bỏ; kết quả đọc ở [`results/README.md`](scenario/variable_scenario/results/README.md) và `part_*_conclusions.md` |
| `role_scenario/` | chưa có | Mới (qz4ng): 9 kịch bản về vai trò của biến, so Naive/OLS/IPTW/AIPW khi hiệu chỉnh đúng hoặc sai tập biến; DGP riêng, SE của IPTW có hiệu chỉnh cho việc ước lượng PS. Notebook kèm quét tham số và quy tắc chọn biến. Tên cũ `role/` ở branch `version_1.0` |
| `ml_scenario/` | chưa có | Mới: DGP chung cho so sánh phương pháp học máy, 10 kịch bản (L0, L1, N1–N3, O1, H1–H3, D1). `dgp/` chỉ dùng numpy/scipy, có test và pilot đã khóa tham số. `learners.py` gom cấu hình learner về một chỗ cho mọi estimator. Chi tiết ở [`ml_scenario/README.md`](ml_scenario/README.md) |

Mỗi thư mục thí nghiệm có README riêng ghi DGP, tham số và kết quả:
[`distribution_scenario`](scenario/distribution_scenario/README.md) ·
[`variable_scenario`](scenario/variable_scenario/README.md) ·
[`role_scenario`](scenario/role_scenario/README.md) ·
[`ml_scenario`](ml_scenario/README.md).

---

## 2. Thư viện

Đã kiểm tra trên **Python 3.11.7** (Linux/WSL). Python 3.10–3.12 đều được; chưa kiểm tra 3.13+.

| Nhóm | Thư viện | Yêu cầu | Đã chạy | Dùng ở |
|---|---|---|---|---|
| Dùng chung | numpy | `>=1.24,<3.0` | 2.4.6 | mọi nơi |
| | pandas | `>=2.0,<3.0` | 2.3.3 | mọi nơi. **Không dùng pandas 3** |
| | scipy | `>=1.10` | 1.17.1 | notebook, `ml_scenario/dgp` |
| | scikit-learn | `>=1.3` | 1.9.1 | pipeline P09; `ml_scenario/learners.py` |
| Thí nghiệm | statsmodels | `>=0.14` | 0.15.0 | OLS/GLM/Logit trong notebook |
| | matplotlib | `>=3.7` | 3.11.2 | hình |
| | ipython, ipykernel | `>=8.0`, `>=6.0` | 9.17.1, 7.4.0 | chạy notebook trong VSCode/Jupyter |
| | lightgbm | `>=4.0` | 4.7.0 | learner `gbm` trong `ml_scenario/learners.py` |
| Test | pytest | `>=7.4` | 9.1.1 | `ml_scenario/tests` |
| Pipeline | pyarrow, pyyaml, pydantic | xem file | | chỉ khối pipeline |

`requirements.txt` là nguồn sự thật về phiên bản. `pyproject.toml` và `uv.lock` **không** có nhóm "Thí nghiệm", nên `uv sync` không cài statsmodels, matplotlib, ipykernel, lightgbm (xem cách dùng uv ở mục 3.4).

Khối thí nghiệm **không cần** `pip install -e .`: notebook và `ml_scenario` không import gói `ra_causal`.

---

## 3. Cài đặt

Mọi lệnh chạy từ thư mục gốc `ra_causal/`. Chọn **một** trong hai cách: pip + venv (3.1–3.3) hoặc uv (3.4).

### 3.1 macOS

```bash
python3 --version                  # cần 3.10–3.12; chưa có: brew install python@3.11
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

- **Mac chip Apple (M1/M2/M3…)**: `python3 -c "import platform; print(platform.machine())"` phải in `arm64`. Nếu in `x86_64` (Python chạy qua Rosetta), pip có thể phải tự biên dịch thư viện; cài lại Python bản arm64 (Homebrew ở `/opt/homebrew` hoặc bộ cài python.org "universal2").
- Python của Homebrew chặn `pip install` ngoài venv (`externally-managed-environment`): luôn kích hoạt `.venv` trước.

### 3.2 Windows (PowerShell)

```powershell
py -3.11 --version                 # chưa có: winget install Python.Python.3.11
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

- Báo *"running scripts is disabled on this system"* khi kích hoạt: chạy một lần `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, hoặc dùng Command Prompt với `.venv\Scripts\activate.bat`.
- Bật UTF-8 cho Python (notebook in và ghi file có tiếng Việt):
  `[Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")`, rồi mở lại terminal và VSCode.
- Không có lệnh `py`: cài Python từ python.org (tick "Add python.exe to PATH"), dùng `python` thay cho `py -3.11`.
- Để repo ở đường dẫn ngắn (vd `C:\work\ra_causal`) để tránh giới hạn 260 ký tự khi cài gói.

### 3.3 Linux (Ubuntu/Debian, Fedora, WSL)

```bash
python3 --version
sudo apt install python3-venv      # Ubuntu/Debian; Fedora: sudo dnf install python3.11
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

- Ubuntu 24.04+ chặn `pip install` ngoài venv: luôn kích hoạt `.venv` trước.
- **WSL**: để repo trong hệ thống file Linux (`~/…`), không để ở `/mnt/c/…`; đọc qua ổ Windows làm Monte Carlo và cài gói chậm hơn nhiều lần.

### 3.4 Cách khác: uv (mọi hệ điều hành)

```bash
# cài uv: macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

uv venv --python 3.11              # tạo .venv, tự tải Python 3.11 nếu máy chưa có
uv pip install -r requirements.txt
```

Dùng `uv pip install -r requirements.txt`, **không** dùng `uv sync`: `uv sync` chỉ cài theo `uv.lock` và gỡ các gói không có trong đó (statsmodels, matplotlib, ipykernel, lightgbm).

### 3.5 Kiểm tra cài đặt

```bash
python -c "import pandas, scipy, sklearn, statsmodels, matplotlib, ipykernel, lightgbm; print(pandas.__version__)"   # pandas phải là 2.x
python -m pytest ml_scenario/tests -q                                                                         # 36 passed, khoảng 40 s
```

---

## 4. Chạy thí nghiệm

**Chọn kernel**: trong VSCode mở notebook → *Select Kernel* → Python của `.venv` (vừa cài xong thì *Developer: Reload Window*). Notebook dùng thư mục chứa nó làm thư mục làm việc; VSCode mặc định như vậy.

| Thí nghiệm | Cách chạy | Ghi chú |
|---|---|---|
| `scenario/baseline.ipynb` | Run All | |
| `distribution_scenario/notebook/*.ipynb` | Run All | Notebook tự thêm thư mục cha vào `sys.path` để import `module.*` |
| `distribution_scenario/run.ipynb` | Run All | Import các file `.py` phẳng nằm cạnh notebook |
| `role_scenario/roles_test.ipynb` | Run All | Đặt `ROLES_REPS=20` để chạy thử nhanh (mặc định 1000); kết quả ghi vào `results/` cạnh notebook |
| `variable_scenario/*.ipynb` | Run All, **phần A trước** | Phần B, D đọc `results/T0.csv` của phần A. Phần B mất khoảng 10 phút ở R = 1000 |
| `ml_scenario/` | `python -m pytest ml_scenario/tests -q`<br>`python ml_scenario/pilot_dgp.py` | Pilot sinh 10^6 dòng mỗi kịch bản, ghi đè `ml_scenario/results/pilot_dgp.csv` |

Notebook của `variable_scenario` đọc ba biến môi trường. Phải đặt **trước khi** mở VSCode (kernel đọc lúc khởi động):

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `RA_VARIABLE_REPS` | 1000 | số lần lặp; chạy thử đặt 200 |
| `RA_VARIABLE_N` | `250,500,1000,2000,4000,8000` | lưới cỡ mẫu |
| `RA_VARIABLE_RUN_MC` | 1 | đặt 0 để chỉ đọc lại CSV, không chạy Monte Carlo |

```bash
# macOS / Linux
RA_VARIABLE_REPS=200 code .
```
```powershell
# Windows
$env:RA_VARIABLE_REPS = "200"; code .
```

Run All ghi đè CSV trong `results/`. Sao lưu thư mục này nếu muốn giữ kết quả cũ.

Dùng DGP của `ml_scenario` trong code của mình:

```python
import sys; sys.path.insert(0, "ml_scenario")       # hoặc chạy từ trong ml_scenario/
from dgp import Simulation

sim = Simulation("N3")                 # một trong 10 mã; Simulation.list_scenarios() để xem
df = sim.generate(1000, seed=1)        # X1..Xd, A, Y (cho estimator) + e, mu0, tau, Y0, Y1 (giá trị thật)
sim.ate                                # ATE thật, dạng đóng

from learners import fit_nuisance
nu = fit_nuisance(df, "gbm", seed=1)   # ê, μ̂0, μ̂1, m̂ cross-fit K = 5, dùng chung cho mọi estimator
```

Cấu hình từng learner và cách dùng đầy đủ: [`ml_scenario/README.md` mục 3.2](ml_scenario/README.md#32-thư-viện-learner).

---

## 5. Sự cố thường gặp

| Triệu chứng | Nguyên nhân | Sửa |
|---|---|---|
| `ModuleNotFoundError: statsmodels` / `matplotlib` / `IPython` / `lightgbm` | Kernel không phải `.venv`, hoặc cài bằng `uv sync` | Chọn lại kernel `.venv`; chạy `pip install -r requirements.txt` |
| `ModuleNotFoundError: module` ở `distribution_scenario/notebook/` | Thư mục làm việc không phải thư mục chứa notebook | Mở notebook bằng VSCode/Jupyter từ chính file đó, hoặc `os.chdir` về `notebook/` |
| `FileNotFoundError: .../T0.csv` ở phần B hoặc D | Chưa chạy phần A | Chạy `variable_type.ipynb` trước |
| `LossySetitemError`, kết quả ép kiểu lạ | Đang dùng pandas 3.x | `pip install "pandas>=2.0,<3.0"` |
| pip in `Building wheel for numpy` / `scipy` và chạy rất lâu | Không có wheel cho tổ hợp máy + Python (thường là Python quá mới) | Dùng Python 3.11 hoặc 3.12 |
| `UnicodeEncodeError` trên Windows | Chưa bật UTF-8 | Đặt `PYTHONUTF8=1` (mục 3.2) |

---

## 6. Khối pipeline (tạm chưa cập nhật)

Khối tiền xử lý P01–P09 và giao diện Run Viewer **không đổi** trong `version_2.0`. README này tạm bỏ qua phần đó. Cần chạy thì cài thêm `pip install -e .` rồi xem:

| Tài liệu | Nội dung |
|---|---|
| [`src/ra_causal/cli/README.md`](src/ra_causal/cli/README.md) | Lệnh `run_pipeline`, `run_step`, mã thoát |
| [`src/ra_causal/preprocess/README.md`](src/ra_causal/preprocess/README.md) | Chín module P01–P09 |
| [`docs/SPEC_preprocessing.md`](docs/SPEC_preprocessing.md) | Bản thiết kế khối tiền xử lý |
| [`ui/README.md`](ui/README.md) | Cài và chạy Run Viewer (Node.js 20/22) |

README đầy đủ của khối này nằm ở branch [`version_1.0`](https://github.com/qz4ng/SEMINAR/blob/version_1.0/README.md).
