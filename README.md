# ra_causal — pipeline end-to-end cho bài toán cover cropping → yield (CIAT)

Ước lượng tác động nhân quả của **cover cropping** lên **năng suất khoai tây** từ dữ liệu khảo sát nông hộ nhiều quốc gia, nhiều năm.

> **Trạng thái:** khối **tiền xử lý (P01–P09)** đã chạy được end-to-end, 116 test xanh. Có giao diện **Run Viewer** ([`ui/`](ui/README.md)) để xem một lượt chạy và bối cảnh dữ liệu. Các khối sinh dữ liệu, xử lý nhân quả, ước lượng và đánh giá **còn để trống**, sẽ làm dần.

---

## 1. Yêu cầu

| Thành phần | Phiên bản | Ghi chú |
|---|---|---|
| Python | **3.11** (khuyến nghị, đã kiểm tra) · 3.10–3.12 đều được | Chưa kiểm tra trên 3.13+. `pyproject.toml` yêu cầu ≥ 3.10 |
| pandas | **2.x** (`>=2.0,<3.0`) | pandas 3 đổi hành vi ép kiểu và cấm gán `NaN` vào cột bool/int → gãy P01, P03 và test |
| pydantic | **2.x** | Code dùng API v2 (`model_dump`), không chạy với pydantic 1 |
| numpy, pyarrow, pyyaml, scikit-learn | xem `requirements.txt` | pyarrow để đọc/ghi parquet |
| Node.js | 20 hoặc 22 LTS | **Chỉ cần nếu mở giao diện** — xem [`ui/README.md`](ui/README.md) |

`requirements.txt` là nguồn sự thật về phiên bản; `pyproject.toml` và `uv.lock` khớp với nó.

---

## 2. Cài đặt

Mọi lệnh chạy từ thư mục gốc `ra_causal/`. Có hai cách, chọn **một**:
- **pip + venv**: có sẵn trong Python.
- **uv**: nhanh hơn, cài đúng phiên bản đã khóa trong `uv.lock`.

### 2.1 macOS

```bash
# Kiểm tra Python (macOS dùng lệnh python3, không phải python)
python3 --version            # cần 3.10–3.12; chưa có: brew install python@3.11  hoặc cài từ python.org

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

- **Mac chip Apple (M1/M2/M3…)**: kiểm tra Python là bản arm64, không chạy qua Rosetta:
  `python3 -c "import platform; print(platform.machine())"` phải in `arm64`. Nếu in `x86_64`, pip có thể phải biên dịch pyarrow từ mã nguồn — cài lại Python bản arm64 (Homebrew ở `/opt/homebrew` hoặc bộ cài python.org "universal2").
- Python do Homebrew cài chặn `pip install` ra ngoài venv (lỗi `externally-managed-environment`): luôn kích hoạt `.venv` trước khi `pip install`.

### 2.2 Windows

Dùng **PowerShell** (hoặc Windows Terminal).

```powershell
# Kiểm tra Python; chưa có: winget install Python.Python.3.11  hoặc cài từ python.org (tick "Add python.exe to PATH")
py -3.11 --version

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

- PowerShell báo *"running scripts is disabled on this system"* khi kích hoạt venv: chạy một lần
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, hoặc dùng Command Prompt với `.venv\Scripts\activate.bat`.
- **Bật UTF-8 cho Python** (thông báo, tên lỗi và báo cáo có tiếng Việt). Nếu không bật, ghi log ra file có thể gặp `UnicodeEncodeError`:
  ```powershell
  $env:PYTHONUTF8 = "1"                           # chỉ phiên hiện tại
  [Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")   # vĩnh viễn
  ```
- Lệnh `py` không có: cài Python từ python.org (có kèm "Python Launcher"), hoặc dùng `python` thay cho `py -3.11`.
- Thư mục dự án nên nằm ở đường dẫn ngắn (vd `C:\work\ra_causal`) để tránh giới hạn 260 ký tự của Windows khi cài gói.

### 2.3 Linux (Ubuntu/Debian, Fedora, WSL)

```bash
python3 --version
# Ubuntu/Debian: gói venv tách riêng
sudo apt install python3-venv          # hoặc python3.11-venv nếu dùng bản 3.11 riêng
# Fedora: sudo dnf install python3.11

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

- Ubuntu 24.04 trở lên chặn `pip install` ngoài venv (`externally-managed-environment`): luôn kích hoạt `.venv` trước.
- **WSL**: nên để dự án trong hệ thống file Linux (`~/…`), không để ở `/mnt/c/…` — cài gói và chạy test chậm hơn nhiều lần khi đọc qua ổ Windows.

### 2.4 Cách khác: uv (mọi hệ điều hành)

```bash
# Cài uv: macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

uv sync --extra test        # tạo .venv và cài đúng phiên bản trong uv.lock (kể cả pytest)
uv run pytest -q            # chạy lệnh trong .venv mà không cần kích hoạt
```

uv tự tải đúng bản Python nếu máy chưa có (`uv python install 3.11`).

### 2.5 Kiểm tra cài đặt

```bash
python -c "import pandas, pydantic; print(pandas.__version__, pydantic.__version__)"   # phải là 2.x và 2.x
python -m pytest -q                                                                  # 116 passed
```

Dấu hiệu cài sai phiên bản:

| Triệu chứng | Nguyên nhân | Sửa |
|---|---|---|
| `LossySetitemError`, test P01/P03 đỏ | Đang dùng pandas 3.x | `pip install "pandas>=2.0,<3.0"` |
| `AttributeError: ... has no attribute 'model_dump'` | pydantic 1.x | `pip install "pydantic>=2.5,<3.0"` |
| pip chạy rất lâu, in `Building wheel for pyarrow` / `numpy` | Không có wheel cho tổ hợp máy + Python này (thường là Python quá mới) | Dùng Python 3.11 hoặc 3.12 |
| `ModuleNotFoundError: ra_causal` | Chưa `pip install -e .` hoặc chưa kích hoạt `.venv` | Kích hoạt venv rồi cài lại |

---

## 3. Chạy thử

Các lệnh dưới đây giả định **đã kích hoạt `.venv`** (hoặc thêm `uv run` phía trước).

**macOS / Linux**

```bash
# Sinh dữ liệu mẫu (sạch + bẩn có cài lỗi biết trước)
python generate_data.py

# Chạy cả chuỗi P01 → P09
python -m ra_causal.cli.run_pipeline \
    --config configs/pipeline.yaml --input data/raw/dirty.csv --output data/out

# Chạy đúng một module, thử một lựa chọn tham số
python -m ra_causal.cli.run_step P04 \
    --input data/out/interim/<run_id>/after_P03.parquet \
    --config configs/preprocess.yaml --output data/interim/manual/ \
    --set p04.action=winsorize

# Test
python -m pytest -q
```

**Windows (PowerShell)** — xuống dòng bằng dấu backtick `` ` `` thay cho `\`, đường dẫn dùng được cả `/`:

```powershell
python generate_data.py

python -m ra_causal.cli.run_pipeline `
    --config configs/pipeline.yaml --input data/raw/dirty.csv --output data/out

python -m ra_causal.cli.run_step P04 `
    --input data/out/interim/<run_id>/after_P03.parquet `
    --config configs/preprocess.yaml --output data/interim/manual/ `
    --set p04.action=winsorize

python -m pytest -q
```

Thay `<run_id>` bằng mã lượt chạy thật: tên thư mục mới nhất trong `data/out/interim/`, dạng `20260924-112145-95668ddd`. PowerShell báo lỗi nếu để nguyên dấu `<` `>`.

Kết quả một lần chạy nằm ở `data/out/processed/<run_id>/`: `analysis_ready.parquet`, `data_dictionary.csv`, `artifacts/`; báo cáo ở `data/out/reports/<run_id>/run_report.json`. Mã thoát: `0` chạy xong, `1` lỗi đối số/config/đọc dữ liệu, `2` một module lỗi kỹ thuật, `3` một module bị chặn vì dữ liệu vi phạm ngưỡng — chi tiết trong [cli/README](src/ra_causal/cli/README.md).

### Giao diện Run Viewer

Giao diện hiện hiển thị **một lượt chạy mẫu đóng gói sẵn** (dirty.csv, chạy đủ 9 bước); nó chưa tự đọc thư mục `data/out/` của bạn.

```bash
cd ui/run-viewer
npm ci          # lần đầu
npm run dev     # mở http://localhost:5173
```

Hướng dẫn đủ cho macOS, Windows, Linux ở [`ui/README.md`](ui/README.md).

---

## 4. Bản đồ thư mục

| Thư mục | Nội dung | Trạng thái | Tài liệu |
|---|---|---|---|
| `src/ra_causal/core` | Hợp đồng chung: `StepResult`, `StepReport`, lỗi, registry, schema, báo cáo | đang dùng | [README](src/ra_causal/core/README.md) |
| `src/ra_causal/io` | Đọc/ghi file, adapter cho dữ liệu thô | đang dùng | [README](src/ra_causal/io/README.md) |
| `src/ra_causal/preprocess` | **Chín module P01–P09** | đang dùng | [README](src/ra_causal/preprocess/README.md) |
| `src/ra_causal/pipeline` | Nối module, kiểm tra hợp đồng, định vị lỗi | đang dùng | [README](src/ra_causal/pipeline/README.md) |
| `src/ra_causal/cli` | Hai lệnh chạy | đang dùng | [README](src/ra_causal/cli/README.md) |
| `src/ra_causal/utils` | Ép kiểu theo schema, `jsonify` | đang dùng | [README](src/ra_causal/utils/README.md) |
| `tests` | 116 test + khung dữ liệu giả (`tests/fixtures/make_frames.py`) | đang dùng | [README](tests/README.md) |
| `configs` | `schema/canonical.yaml` (vai trò biến theo DAG v0), `schema/raw_assumed.yaml` (alias), `preprocess.yaml`, `pipeline.yaml` | đang dùng | — |
| `ui/run-viewer` | Giao diện xem lượt chạy + bối cảnh dữ liệu (React, dữ liệu mẫu) | đang dùng | [README](ui/README.md) |
| `generate_data.py` | Sinh `data/raw/clean.csv`, `data/raw/dirty.csv` | đang dùng | — |
| `src/ra_causal/simulate` | Sinh dữ liệu giả theo DAG | **để trống** | [thiết kế](../Mô%20phỏng%20dữ%20liệu/README.md) |
| `src/ra_causal/process` | Xử lý nhân quả K01–K10 (PS, trọng số, cân bằng) | **để trống** | — |
| `src/ra_causal/estimate` | Ước lượng và dự đoán tác động | **để trống** | — |
| `src/ra_causal/evaluate` | Đánh giá so với đáp án mô phỏng | **để trống** | — |
| `src/ra_causal/reporting` | Xuất bảng, hình, báo cáo cuối | **để trống** | — |

## 5. Tài liệu thiết kế

| File | Nội dung |
|---|---|
| [`docs/SPEC_preprocessing.md`](docs/SPEC_preprocessing.md) | Bản thiết kế thi công của khối tiền xử lý (hợp đồng, 9 module, tham số, cơ chế báo lỗi, chiến lược test) |
| [`docs/OPEN_QUESTIONS.md`](docs/OPEN_QUESTIONS.md) | Những chỗ code làm khác thiết kế (kèm lý do) và các câu hỏi cần nhóm/GVHD chốt |
| [`docs/ui/DESIGN_run_viewer.md`](docs/ui/DESIGN_run_viewer.md) | Thiết kế giao diện Run Viewer (bản gốc giao cho Antigravity; giao diện hiện tại đã được làm lại, xem `ui/README.md`) |
| [`docs/PROMPT_for_agent.md`](docs/PROMPT_for_agent.md) · [`docs/PROMPT_fix_round1.md`](docs/PROMPT_fix_round1.md) · [`docs/ui/PROMPT_antigravity.md`](docs/ui/PROMPT_antigravity.md) | Prompt giao việc cho agent lập trình |

---

## 6. Bốn nguyên tắc xuyên suốt

1. **Một module, một vấn đề** — chạy và test được độc lập.
2. **Gắn cờ, không xóa** — mặc định không loại dòng, không sửa giá trị; mọi thay đổi phải do người dùng bật trong config.
3. **Mọi quyết định nằm trong `run_report.json`** — tham số đã dùng, dòng bị loại, cột bị chặn, quần thể mục tiêu.
4. **Chạy lại cho kết quả y hệt** — cùng dữ liệu, cùng config, cùng seed.
