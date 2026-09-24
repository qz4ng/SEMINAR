# SPEC — Khối tiền xử lý (preprocess P01–P09) cho dự án `ra_causal`

**Phiên bản spec:** 1.0 · **Ngày:** 2026-09-21 · **Trạng thái:** để triển khai

---

## 0. Đọc trước khi viết dòng code đầu tiên

Tài liệu này là **bản thiết kế thi công**, không phải gợi ý. Bạn (agent lập trình) hiện thực **đúng** những gì viết ở đây, không thêm, không bớt.

### 0.1 Sáu quy tắc chống bịa (bắt buộc)

1. **Không được bịa tên cột.** Toàn bộ tên cột hợp lệ nằm ở §5. Cột mới chỉ được tạo theo đúng quy ước đặt tên ở §4.6 và phải được liệt kê trong phần "Cột sinh ra" của module tương ứng.
2. **Không được bịa tham số.** Mọi tham số, kiểu, giá trị cho phép và giá trị mặc định nằm trong bảng tham số của từng module (§6). Không thêm tham số ngoài bảng. Không đặt số cứng (magic number) trong code — mọi ngưỡng đọc từ config.
3. **Không được thêm thư viện** ngoài danh sách ở §3.
4. **Không code phần ngoài phạm vi** (§1.2). Thư mục `process/`, `estimate/`, `evaluate/`, `simulate/` để trống (chỉ có `__init__.py` rỗng và `.gitkeep`).
5. **Khi spec thiếu hoặc mâu thuẫn:** KHÔNG tự quyết định im lặng. Ghi một mục vào `docs/OPEN_QUESTIONS.md` theo mẫu §12.2, hiện thực phương án tối thiểu an toàn (thường là *chỉ gắn cờ, không đổi dữ liệu*), và đánh dấu `# SPEC-GAP: <id câu hỏi>` ngay tại chỗ trong code.
6. **Không đọc file `truth*`** trong bất kỳ module nào của `preprocess/` (đó là đáp án của bộ mô phỏng, chỉ dành cho `evaluate/` và test của bộ sinh dữ liệu — chưa thuộc phạm vi này).

### 0.2 Triết lý thiết kế mà code phải phản ánh

- **Một module = một vấn đề dữ liệu.** Module chỉ được sửa đúng phạm vi vấn đề của nó.
- **Mặc định không phá dữ liệu:** không xóa dòng, không sửa giá trị, trừ khi người dùng bật tham số tương ứng. Mặc định là *gắn cờ và báo cáo*.
- **Mọi quyết định đều lộ ra trong báo cáo.** Nếu một module thay đổi dữ liệu mà không ghi vào report thì đó là bug.
- **Chạy lại cho kết quả y hệt.** Không dùng seed toàn cục, không dùng `set`/`dict` để sinh thứ tự, mọi tie-break phải có quy tắc xác định (§4.7).

---

## 1. Bối cảnh và phạm vi

### 1.1 Bối cảnh (đủ để hiểu, không cần đọc tài liệu khác)

Dự án ước lượng tác động nhân quả của **cover cropping** (biến can thiệp `cover_crop`, nhị phân) lên **năng suất khoai tây** (`yield_t_ha`) từ dữ liệu khảo sát nông hộ nhiều quốc gia, nhiều năm. Một dòng dữ liệu = **một ruộng trong một mùa vụ** (field-year). Dữ liệu thô là bản xuất khảo sát: tên cột không đồng nhất, đơn vị lẫn lộn, có dòng trùng, có ô trống, có giá trị vô lý.

Khối tiền xử lý biến dữ liệu thô đó thành **`analysis_ready`** — dữ liệu sạch theo schema chuẩn, kèm: định nghĩa biến can thiệp, tập biến điều chỉnh **L**, thông tin cụm, cờ quan sát được của outcome, và một **báo cáo ghi lại mọi quyết định**.

### 1.2 Phạm vi

**Làm ngay (in scope):**

| Nhóm | Nội dung |
|---|---|
| `core/` | Kiểu dữ liệu hợp đồng, lỗi, registry, context, báo cáo, logging, đọc schema |
| `io/` | Đọc/ghi CSV + Parquet + JSON, adapter khung cho dữ liệu thô |
| `preprocess/` | Chín module P01–P09 (§6) |
| `pipeline/` | Bộ chạy tuần tự, kiểm tra hợp đồng trước/sau mỗi bước, gom báo cáo, **định vị đúng module gây lỗi** |
| `cli/` | Hai lệnh: chạy cả chuỗi, và chạy **một module độc lập** |
| `configs/` | `schema/canonical.yaml`, `schema/raw_assumed.yaml`, `preprocess.yaml`, `pipeline.yaml` |
| `tests/` | Bộ test theo §10 |

**Không làm (out of scope, để trống):** `simulate/`, `process/` (K01–K10), `estimate/`, `evaluate/`, `reporting/`, `notebooks/`. Tạo thư mục + `__init__.py` rỗng + `.gitkeep`, không viết logic.

---

## 2. Cây thư mục bắt buộc

Thư mục gốc đã tồn tại: `/home/doan/Seminar/ra_causal/`. Không đổi tên, không di chuyển.

```text
ra_causal/
├── pyproject.toml                      [LÀM NGAY]
├── README.md                           [LÀM NGAY — ngắn: cách cài, cách chạy, trỏ tới spec]
├── configs/
│   ├── schema/canonical.yaml           [LÀM NGAY — nội dung ở §5]
│   ├── schema/raw_assumed.yaml         [LÀM NGAY — nội dung ở §5.4]
│   ├── preprocess.yaml                 [LÀM NGAY — nội dung ở §7]
│   ├── pipeline.yaml                   [LÀM NGAY — nội dung ở §8.5]
│   └── dgp/                            [ĐỂ TRỐNG]
├── data/{raw,external,simulated,interim,processed,reports}/   [ĐỂ TRỐNG, không commit dữ liệu]
├── docs/
│   ├── SPEC_preprocessing.md           [file này — không sửa]
│   ├── OPEN_QUESTIONS.md               [LÀM NGAY — agent ghi vào đây khi spec thiếu]
│   └── adr/                            [tuỳ chọn]
├── src/ra_causal/
│   ├── __init__.py
│   ├── core/
│   │   ├── contracts.py                [StepResult, StepReport, Finding, Status, ColumnContract]
│   │   ├── context.py                  [PipelineContext]
│   │   ├── errors.py                   [cây ngoại lệ + mã lỗi]
│   │   ├── registry.py                 [đăng ký module theo mã P01..P09]
│   │   ├── schema.py                   [đọc + kiểm tra canonical.yaml]
│   │   ├── reporting.py                [gom report, ghi JSON]
│   │   └── logging.py                  [logger có gắn module_id]
│   ├── io/
│   │   ├── loaders.py  ├── writers.py
│   │   └── adapters/{__init__.py, raw_assumed.py, ciat.py}   [ciat.py = stub NotImplementedError có docstring]
│   ├── preprocess/
│   │   ├── __init__.py                 [export 9 hàm run + REGISTRY entries]
│   │   ├── p01_schema_check.py   ├── p02_harmonize.py    ├── p03_deduplicate.py
│   │   ├── p04_outliers.py       ├── p05_treatment_define.py
│   │   ├── p06_missingness.py    ├── p07_time_order.py
│   │   ├── p08_variable_roles.py ├── p09_clusters.py
│   ├── pipeline/
│   │   ├── steps.py                    [bọc module thành bước, kiểm tra hợp đồng]
│   │   ├── runner.py                   [chạy chuỗi, bắt lỗi, định vị module]
│   │   ├── report.py                   [run_report.json]
│   │   └── gates.py                    [ĐỂ TRỐNG — chỉ docstring "dành cho tháng sau"]
│   ├── cli/{__init__.py, run_pipeline.py, run_step.py}
│   ├── utils/{__init__.py, pandas_tools.py}
│   ├── simulate/ process/ estimate/ evaluate/ reporting/   [ĐỂ TRỐNG: chỉ __init__.py]
└── tests/
    ├── conftest.py                     [factory dữ liệu giả, §10.2]
    ├── fixtures/make_frames.py         [factory + injector, §10.2]
    ├── core/        ├── preprocess/    ├── pipeline/   ├── integration/
```

---

## 3. Môi trường và phụ thuộc

- Python **≥ 3.10**, đóng gói theo `pyproject.toml`, layout `src/`.
- **Phụ thuộc chạy:** `pandas>=2.0`, `numpy>=1.24`, `pyarrow>=14`, `pyyaml>=6`, `pydantic>=2.5`, `scikit-learn>=1.3` (chỉ cho `GroupKFold`/`StratifiedGroupKFold` ở P09).
- **Phụ thuộc test:** `pytest>=7.4`, `pytest-cov`.
- **Cấm:** mọi thư viện khác (không `great_expectations`, không `pandera`, không `click`, không `typer`, không `rich`, không `loguru`). CLI dùng `argparse`, log dùng `logging`.
- Không gọi mạng. Không đọc/ghi ngoài `data/` và đường dẫn người dùng truyền vào.
- Docstring và comment viết **tiếng Việt**, ngắn gọn. Tên biến/hàm/tham số viết **tiếng Anh**, `snake_case`.
- Type hints đầy đủ cho mọi hàm public.

---

## 4. Hợp đồng chung (`core/`)

### 4.1 `Status`

```
class Status(str, Enum):
    OK = "ok"                      # chạy xong, không có gì đáng ngại
    OK_WITH_WARNINGS = "warning"   # chạy xong, có finding mức warning
    BLOCKED = "blocked"            # dừng có kiểm soát: điều kiện người dùng đặt ra không đạt
    FAILED = "failed"              # lỗi kỹ thuật / vi phạm hợp đồng
```

`BLOCKED` khác `FAILED`: `BLOCKED` là trường hợp module **hoạt động đúng** nhưng dữ liệu vi phạm ngưỡng người dùng đặt (ví dụ P04 gắn cờ quá `max_flag_rate`). `FAILED` là lỗi (thiếu cột bắt buộc, config sai kiểu, exception không lường trước).

### 4.2 `Finding` — đơn vị báo cáo nhỏ nhất

Mọi thứ module phát hiện đều là một `Finding`, không in ra màn hình, không `print`:

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `code` | str | Mã cố định, dạng `P0x.SNAKE_UPPER`, lấy từ bảng "Mã finding" của từng module. Không được bịa mã mới. |
| `severity` | `"info" \| "warning" \| "error" \| "blocking"` | |
| `message` | str | Một câu tiếng Việt, không chứa dữ liệu nhạy cảm |
| `column` | str \| None | |
| `count` | int | Số dòng/ô liên quan |
| `sample_ids` | list[str] | Tối đa **10** `record_id`, sắp xếp tăng dần (xác định) |
| `details` | dict | JSON-serializable, số liệu phụ |

### 4.3 `StepReport`

Trường bắt buộc, đúng tên, đúng thứ tự khi ghi JSON:

```
module_id, module_name, spec_version, status,
started_at (ISO-8601), duration_s (float, 3 chữ số),
n_rows_in, n_rows_out, n_cols_in, n_cols_out,
rows_dropped, rows_flagged,
columns_added (list[str]), columns_modified (list[str]),
params_effective (dict — toàn bộ tham số sau khi merge default, đã JSON-hóa),
findings (list[Finding]), artifacts (dict[str, str] — tên → đường dẫn tương đối),
context_updates (list[str] — tên khóa context mà module này ghi)
```

`StepReport.to_dict()` phải trả về dict thuần JSON (không `numpy.int64`, không `Timestamp`, không `NaN` — dùng `None`). Viết một hàm `utils.pandas_tools.jsonify(obj)` làm việc này và dùng ở mọi nơi.

### 4.4 `StepResult`

```
@dataclass(frozen=True)
class StepResult:
    data: pd.DataFrame
    report: StepReport
    artifacts: dict[str, pd.DataFrame] = field(default_factory=dict)   # vd: "quarantine", "review_list"
    context_updates: dict[str, Any] = field(default_factory=dict)
```

### 4.5 Chữ ký hàm module — **giống hệt nhau ở cả 9 module**

```
def run(df: pd.DataFrame, cfg: <ModuleConfig>, ctx: PipelineContext) -> StepResult
```

- `cfg` là một model pydantic riêng của module (ví dụ `P04Config`), **không phải dict**. Pipeline chịu trách nhiệm dựng `cfg` từ YAML và bắt lỗi validate.
- Module **không được** sửa `df` tại chỗ. Bắt đầu bằng `out = df.copy()`.
- Module **không được** đọc file, trừ `ctx.schema` đã nạp sẵn.
- Module **không được** `raise` ngoại lệ chung chung; chỉ `raise` các lớp ở §4.8.
- Mỗi module có hằng `MODULE_ID` (`"P04"`), `MODULE_NAME` (`"outliers"`), `SPEC_VERSION = "1.0"`.

### 4.6 Quy ước đặt tên cột sinh ra

| Loại | Mẫu | Ví dụ |
|---|---|---|
| Cờ (bool, mặc định `False`, không NaN) | `flag__<module_id_lower>__<reason>[__<col>]` | `flag__p04__outlier__yield_t_ha` |
| Cột dẫn xuất | `<col>__<transform>` | `yield_t_ha__winsorized`, `cover_crop__thr1` |
| Cột hệ thống | tên cố định, liệt kê ở §5.3 | `cluster_id`, `fold_id`, `c_outcome_observed` |

Không có cột sinh ra nào được trùng tên cột canonical. Trước khi thêm cột, module phải kiểm tra trùng và `raise ContractError` nếu trùng.

### 4.7 Quy tắc xác định (determinism)

- Mọi thao tác chọn "một dòng đại diện" phải sắp xếp trước theo `(<khóa nghiệp vụ>, record_id)` rồi mới chọn.
- Mọi danh sách trong report phải được `sorted()`.
- Nơi cần ngẫu nhiên (chỉ P09 chia fold) dùng `ctx.rng` (`numpy.random.Generator` do pipeline tạo từ `seed` trong config). Cấm `random`, cấm `np.random.seed`.
- Không lặp qua `set`. Không phụ thuộc thứ tự dict do người dùng nhập (luôn `sorted`).

### 4.8 Cây ngoại lệ (`core/errors.py`)

```
RaCausalError                      # gốc
├── ConfigError                    # config sai kiểu/giá trị không cho phép
├── SchemaError                    # dữ liệu không khớp schema (thiếu cột bắt buộc, sai kiểu không ép được)
├── ContractError                  # module vi phạm hợp đồng (trùng tên cột, mất dòng ngoài ý muốn...)
├── DataQualityError               # ngưỡng chất lượng người dùng đặt bị vượt → dẫn tới BLOCKED
└── DependencyError                # thiếu khóa context do module trước chưa chạy
```

Mọi ngoại lệ mang **bắt buộc**: `module_id`, `code` (cùng bảng mã finding), `message`, `details: dict`. Ví dụ:
`DataQualityError(module_id="P04", code="P04.MAX_FLAG_RATE_EXCEEDED", message="...", details={"rate": 0.18, "limit": 0.05})`.

### 4.9 `PipelineContext` (`core/context.py`)

Đối tượng truyền xuyên suốt, **chỉ pipeline được ghi**, module đọc và trả `context_updates`:

| Khóa | Kiểu | Do module nào ghi | Ý nghĩa |
|---|---|---|---|
| `run_id` | str | pipeline | `YYYYmmdd-HHMMSS-<8 hex>` |
| `schema` | `CanonicalSchema` | pipeline | §5 |
| `rng` | `np.random.Generator` | pipeline | |
| `paths` | `RunPaths` | pipeline | `interim`, `processed`, `reports` |
| `quarantined_ids` | list[str] | P01 | dòng bị tách ra |
| `unit_conversions` | dict | P02 | cột → hệ số đã áp dụng |
| `duplicate_groups` | int | P03 | |
| `treatment_column` | str | P05 | mặc định `cover_crop` |
| `treatment_definition` | dict | P05 | mô tả quy tắc nhị phân hóa |
| `blocked_columns` | list[str] | P07 | cột **bị cấm** vào L (đo sau can thiệp / không rõ thời điểm), lý do ghi trong report |
| `eligible_columns` | list[str] | P07 | cột **được phép** xét làm biến điều chỉnh; hai danh sách này rời nhau và hợp lại = mọi cột canonical có mặt |
| `adjustment_set` | list[str] | P08 | tập **L** chính |
| `adjustment_set_variants` | dict[str, list[str]] | P08 | ví dụ `{"O_as_confounder": [...], "O_as_mediator": [...]}` |
| `outcome_observed_column` | str | P06 | `c_outcome_observed` |
| `cluster_column` | str | P09 | `cluster_id` |
| `fold_column` | str | P09 | `fold_id` |

Module thiếu khóa cần thiết → `DependencyError` (không tự tính lại).

---

## 5. Schema chuẩn

### 5.1 Nguyên tắc

`configs/schema/canonical.yaml` là **nguồn sự thật duy nhất** về cột. Code không được hardcode danh sách cột (trừ tên cột hệ thống ở §5.3, được phép là hằng trong `core/contracts.py`).

Mỗi cột khai báo đủ **7** thuộc tính: `dtype`, `required`, `measured_at`, `dag_role`, `unit`, `range`, `allowed`.

- `measured_at`: `pre` (trước time zero) | `at` (tại time zero) | `post` (sau can thiệp) | `unknown`.
- `dag_role`: `id` | `cluster` | `confounder` | `treatment` | `treatment_version` | `mediator` | `outcome` | `outcome_predictor` | `collider` | `instrument` | `noise` | `ambiguous`.
- `affected_by_treatment`: bool — **chỉ cần khai khi `measured_at: post`**. Đây là trường quyết định ở P07: `season_rain_mm` đo trong mùa vụ (post) nhưng **không** chịu ảnh hưởng của can thiệp, nên được phép dùng làm biến tăng độ chính xác.

### 5.2 Bảng cột canonical (bản đầy đủ — đưa nguyên vào YAML)

| Cột | dtype | required | measured_at | dag_role | unit | range / allowed |
|---|---|---|---|---|---|---|
| `record_id` | string | ✔ | pre | id | — | duy nhất, không rỗng |
| `grower_id` | string | ✔ | pre | cluster | — | không rỗng |
| `field_id` | string | ✔ | pre | id | — | không rỗng |
| `country` | category | ✔ | pre | confounder | — | allowed: `[C1, C2, C3, C4]` |
| `year` | int16 | ✔ | at | confounder | năm | range `[2015, 2030]` |
| `rain_longterm_mm` | float32 | ✔ | pre | confounder | mm | `[0, 5000]` |
| `temp_longterm_c` | float32 | ✔ | pre | confounder | °C | `[-10, 45]` |
| `soil_om_baseline_pct` | float32 | ✔ | pre | confounder | % | `[0, 20]` |
| `field_size_ha` | float32 | ✔ | pre | confounder | ha | `(0, 500]` |
| `extension_access` | boolean | ✔ | pre | confounder | — | `{0,1}` |
| `contract` | category | ✖ | pre | confounder | — | allowed: `[none, informal, formal]` |
| `experience_yr` | int16 | ✖ | pre | confounder | năm | `[0, 60]` |
| `irrigation` | boolean | ✔ | pre | confounder | — | `{0,1}` |
| `no_till` | boolean | ✖ | pre | ambiguous | — | `{0,1}` |
| `organic_fert` | boolean | ✖ | pre | ambiguous | — | `{0,1}` |
| `rotation_len_yr` | int16 | ✖ | pre | ambiguous | năm | `[1, 10]` |
| `cover_crop` | boolean | ✔ | at | treatment | — | `{0,1}` |
| `cover_crop_months` | float32 | ✖ | at | treatment_version | tháng | `[0, 12]` |
| `cover_crop_type` | category | ✖ | at | treatment_version | — | allowed: `[none, legume, grass, mixed]` |
| `soil_om_post_pct` | float32 | ✖ | post (`affected_by_treatment: true`) | mediator | % | `[0, 20]` |
| `weed_pressure` | int8 | ✖ | post (`affected_by_treatment: true`) | mediator | thang 1–5 | `[1, 5]` |
| `season_rain_mm` | float32 | ✖ | post (`affected_by_treatment: false`) | outcome_predictor | mm | `[0, 5000]` |
| `buyer_incentive` | boolean | ✖ | pre | instrument | — | `{0,1}` |
| `noise_1` … `noise_5` | float32 | ✖ | pre | noise | — | không giới hạn |
| `yield_t_ha` | float32 | ✔ | post (`affected_by_treatment: true`) | outcome | t/ha | `[0, 120]` |
| `in_program` | boolean | ✖ | post (`affected_by_treatment: true`) | collider | — | `{0,1}` |

Ghi chú bắt buộc ghi vào YAML dưới dạng comment: *khoảng giá trị là ngưỡng "không thể", dùng để phát hiện lỗi nhập liệu, không phải khoảng "bình thường"*.

### 5.3 Tên cột hệ thống (hằng trong `core/contracts.py`)

`cluster_id`, `fold_id`, `c_outcome_observed`, `row_source`, `dup_group_id`.

### 5.4 `raw_assumed.yaml` — ánh xạ dữ liệu thô giả định

Khai báo cho adapter `raw_assumed`: `column_aliases` (tên thô → tên canonical), `country_aliases`, `boolean_aliases` (`{"Yes":1,"No":0,"Partial":null,"Có":1,"Không":0,"1":1,"0":0}`), `unit_declarations` (nguồn → đơn vị yield), `decimal_comma: true`.

**Cảnh báo cho agent:** định dạng thô thật của CIAT **chưa biết**. `raw_assumed.yaml` chỉ chứa các alias được liệt kê ở đây; **không tự nghĩ thêm alias** (ví dụ không tự thêm `"Y"`, `"yes "`, `"TRUE"` — việc chuẩn hóa hoa/thường/khoảng trắng do P02 làm trước khi tra alias).

---

## 6. Đặc tả chín module

Khuôn chung cho mọi module dưới đây: **Mục đích → Tiền điều kiện → Tham số → Thuật toán → Cột sinh ra → Report → Mã finding → Ca biên**.

Thứ tự chạy trong pipeline (**không đổi**):

```
P01 → P02 → P03 → P04 → P05 → P07 → P08 → P06 → P09
```

Lý do thứ tự (ghi vào docstring của `pipeline/runner.py`): P02 trước P04 vì phải quy về cùng đơn vị rồi mới xác định được bất thường; P03 trước P04/P06 vì dòng trùng làm lệch mọi thống kê ngưỡng; P04 trước P06 vì tuỳ chọn `to_na` của P04 sinh thêm ô trống; P05 trước mọi thống kê theo nhóm can thiệp; P07 trước P08; **P08 trước P06** vì chỉ điền thiếu cho biến thật sự dùng (L ∪ {A, Y}); P09 trước các bước mô hình hóa sau này.

---

### 6.1 P01 · `schema_check`

**Mục đích.** Chặn dữ liệu không đúng dạng cam kết ngay ở cửa vào, để lỗi không biến thành `NaN` âm thầm ở bước sau.

**Tiền điều kiện.** `df` vừa qua adapter (tên cột đã là canonical). `ctx.schema` đã nạp.

**Tham số** (`P01Config`):

| Tên | Kiểu / giá trị cho phép | Mặc định | Hành vi |
|---|---|---|---|
| `on_error` | `quarantine` \| `raise` \| `flag` | `quarantine` | `quarantine`: chuyển dòng lỗi sang artifact `quarantine`, bỏ khỏi `data`. `flag`: giữ dòng, thêm cờ. `raise`: `SchemaError` |
| `dtype_coercion` | `strict` \| `permissive` | `permissive` | `permissive`: thử `pd.to_numeric(errors="coerce")` / ép category; ô ép hỏng thành `NaN` và được đếm |
| `out_of_range` | `to_na` \| `flag` \| `clip` \| `raise` | `to_na` | Áp cho cột số có `range` |
| `unknown_columns` | `warn_keep` \| `drop` \| `raise` | `warn_keep` | |
| `duplicate_key_action` | `defer_to_p03` \| `raise` | `defer_to_p03` | P01 chỉ đếm, P03 mới xử lý |
| `required_id_columns` | list[str] | `["record_id"]` | Dòng thiếu các cột này luôn bị quarantine bất kể `on_error` |

**Thuật toán.**

1. Kiểm tra cột bắt buộc (`required: true`) có mặt. Thiếu → `SchemaError` ngay (không phụ thuộc `on_error`), code `P01.MISSING_REQUIRED_COLUMN`.
2. Cột lạ (không có trong schema, không khớp mẫu `noise_\d+`) → xử lý theo `unknown_columns`.
3. Ép kiểu từng cột theo `dtype`. Đếm số ô ép hỏng theo cột.
4. Kiểm tra `allowed` cho cột category: giá trị ngoài danh sách → đánh dấu ô lỗi (**không** tự sửa; P02 mới ánh xạ).
5. Kiểm tra `range` cho cột số → xử lý theo `out_of_range`.
6. Kiểm tra `record_id`: rỗng/trùng → dòng bị quarantine, code `P01.BAD_RECORD_ID`.
7. Tập hợp dòng "lỗi" = dòng có ít nhất một ô lỗi ở bước 3–6, xử lý theo `on_error`.
8. Không sắp xếp lại dòng; giữ nguyên thứ tự đầu vào.

**Cột sinh ra.** Khi `on_error = flag`: `flag__p01__schema_error` (bool) và `flag__p01__out_of_range__<col>` cho từng cột vi phạm.

**Report riêng** (trong `findings.details`): `errors_by_column` (dict cột → {coerce_failed, out_of_range, not_allowed}), `n_quarantined`, `schema_version`.

**Mã finding.** `P01.MISSING_REQUIRED_COLUMN` (error) · `P01.UNKNOWN_COLUMN` (warning) · `P01.COERCE_FAILED` (warning) · `P01.OUT_OF_RANGE` (warning) · `P01.NOT_ALLOWED_CATEGORY` (warning) · `P01.BAD_RECORD_ID` (error) · `P01.DUPLICATE_KEY_SEEN` (info).

**Ca biên.** `df` rỗng → trả về `df` rỗng, status `OK_WITH_WARNINGS`, finding `P01.EMPTY_INPUT` (warning). Cột toàn `NaN` → không phải lỗi schema, chỉ `info`.

---

### 6.2 P02 · `harmonize`

**Mục đích.** Cùng một thứ ghi nhiều kiểu (`"Country 1"`, `"c1 "`, `"C-1"`), đơn vị lẫn lộn (kg/ha vs t/ha), `"Yes/No/Partial"`. Nếu không xử lý: `country` từ 4 mức thành hàng chục mức, và 20% dòng ghi kg/ha sẽ bị P04 gắn cờ outlier hàng loạt.

**Tham số** (`P02Config`):

| Tên | Kiểu / cho phép | Mặc định | Hành vi |
|---|---|---|---|
| `string_normalize.trim` / `.lower` / `.strip_accents` / `.collapse_spaces` | bool | tất cả `true` | Áp cho mọi cột kiểu chuỗi/category trước khi tra alias |
| `category_mapping_mode` | `explicit` \| `fuzzy_suggest` \| `fuzzy_auto` | `explicit` | `fuzzy_suggest`: chỉ ghi đề xuất vào report, **không đổi dữ liệu** |
| `fuzzy_threshold` | float `[0,1]` | `0.90` | Dùng `difflib.SequenceMatcher.ratio()` (thư viện chuẩn) |
| `unmapped_action.default` | `to_na` \| `keep_raw` \| `raise` | `to_na` | |
| `unmapped_action.overrides` | dict cột → hành động | `{country: raise, cover_crop: raise}` | Với treatment và biến phân tầng chính thì không được đoán |
| `unit_policy` | `unit_column` \| `source_declaration` \| `threshold_inference` \| `none` | `unit_column` | |
| `unit_column_name` | str | `yield_unit` | Cột đơn vị nếu dữ liệu thô có |
| `unit_fallback` | `source_declaration` \| `none` \| `raise` | `source_declaration` | Khi `unit_column` không tồn tại |
| `unit_threshold` | float | `1000.0` | Chỉ dùng khi `threshold_inference`: `yield > ngưỡng` ⇒ coi là kg/ha |
| `decimal_comma` | `auto` \| bool | `auto` | `auto`: nếu > 50% giá trị chuỗi của cột số khớp `^\d+,\d+$` thì coi là dấu phẩy thập phân |
| `category_levels_source` | `schema` \| `data` | `schema` | |

**Thuật toán.**

1. Chuẩn hóa chuỗi theo `string_normalize` (bỏ dấu dùng `unicodedata.normalize("NFD")` + lọc `Mn`).
2. Ánh xạ category bằng bảng alias trong `raw_assumed.yaml`. Khớp chính xác trước; nếu `fuzzy_*` thì mới tính độ tương đồng với các mức hợp lệ.
3. Giá trị không ánh xạ được → theo `unmapped_action`.
4. Quy đổi đơn vị `yield_t_ha`: xác định đơn vị theo `unit_policy`; nếu là kg/ha thì chia 1000; ghi hệ số vào `ctx.unit_conversions` và số dòng bị đổi vào report.
5. Nếu dùng `threshold_inference`: thêm cờ `flag__p02__unit_inferred` cho **mọi** dòng bị suy luận, và phát finding mức `warning` (không phải info) — đây là quyết định có rủi ro.
6. Chuẩn hóa dấu thập phân trước khi ép số (chỉ khi cột còn ở dạng chuỗi).
7. Ép lại dtype theo schema sau khi ánh xạ.

**Cột sinh ra.** `flag__p02__unit_inferred` (chỉ khi `threshold_inference`), `flag__p02__unmapped__<col>`.

**Report riêng.** `mapping_applied`: list `{column, raw_value, mapped_value, n_rows}` (sắp xếp theo `column`, `raw_value`); `unit_conversion`: `{n_rows_converted, factor, policy_used}`; `fuzzy_suggestions`: list `{column, raw_value, suggestion, score}`.

**Mã finding.** `P02.UNMAPPED_CATEGORY` (warning/error tuỳ override) · `P02.FUZZY_SUGGESTION` (info) · `P02.UNIT_CONVERTED` (info) · `P02.UNIT_INFERRED` (warning) · `P02.UNIT_POLICY_UNAVAILABLE` (warning) · `P02.MIXED_UNIT_SUSPECTED` (warning — khi phân phối `yield_t_ha` có hai cụm cách nhau ~1000 lần: tỷ lệ giá trị > 1000 nằm trong `[0.02, 0.98]`).

**Ca biên.** Cột `contract` vắng mặt (không bắt buộc) → bỏ qua, không lỗi. Đã ở đúng đơn vị → `n_rows_converted = 0`, không tạo cờ.

---

### 6.3 P03 · `deduplicate`

**Mục đích.** Một ruộng-năm xuất hiện nhiều lần làm cỡ mẫu giả to (SE nhỏ giả) và nhân đôi trọng số của một đơn vị. Phải phân biệt *trùng hệt* với *mâu thuẫn dữ liệu*.

**Tham số** (`P03Config`):

| Tên | Cho phép | Mặc định | Hành vi |
|---|---|---|---|
| `key` | list[str] | `["grower_id","field_id","year"]` | |
| `resolve` | `keep_most_complete` \| `keep_first` \| `keep_last` \| `aggregate` \| `flag_only` | `keep_most_complete` | |
| `timestamp_column` | str \| null | `null` | Bắt buộc khi `keep_last`; thiếu → `ConfigError` |
| `conflict_action` | `review_list` \| `drop_group` \| `resolve` | `review_list` | `review_list`: **giữ nguyên mọi dòng**, đưa nhóm vào artifact `review_list` |
| `critical_columns` | list[str] | `["cover_crop","yield_t_ha","country","year"]` | Khác nhau ở cột này mới gọi là mâu thuẫn |
| `numeric_tolerance` | float | `1e-8` | |
| `aggregate_rules` | dict | `{numeric: "mean", categorical: "mode", boolean: "max"}` | Chỉ dùng khi `resolve = aggregate` |

**Thuật toán.**

1. Nhóm theo `key`. Nhóm có 1 dòng → giữ nguyên.
2. Phân loại nhóm ≥ 2 dòng:
   - **exact**: mọi cột canonical bằng nhau (số so với `numeric_tolerance`, NaN == NaN).
   - **partial**: khác nhau nhưng **không** khác ở `critical_columns`.
   - **conflict**: khác ở ít nhất một `critical_columns`.
3. `exact` và `partial` → xử lý theo `resolve`. `conflict` → theo `conflict_action`.
4. `keep_most_complete`: chọn dòng có ít `NaN` nhất trên các cột canonical; hòa → `record_id` nhỏ nhất theo thứ tự chuỗi.
5. Gán `dup_group_id` (chuỗi `"g%06d"` theo thứ tự nhóm đã sắp xếp) cho mọi dòng thuộc nhóm ≥ 2.
6. `flag_only` → không bỏ dòng nào, chỉ gắn cờ.

**Cột sinh ra.** `dup_group_id` (string, `NA` nếu không trùng), `flag__p03__duplicate` (bool), `flag__p03__conflict` (bool).

**Artifact.** `review_list`: các dòng thuộc nhóm `conflict`, kèm cột `conflict_columns` (chuỗi nối bằng `;`).

**Report riêng.** `groups_by_type` `{exact, partial, conflict}`, `rows_removed`, `conflict_columns_frequency` (dict cột → số nhóm).

**Mã finding.** `P03.EXACT_DUPLICATES` (info) · `P03.PARTIAL_DUPLICATES` (warning) · `P03.CONFLICTING_DUPLICATES` (error) · `P03.KEY_NOT_UNIQUE_AFTER_RESOLVE` (error — kiểm tra hậu điều kiện, nếu còn trùng sau khi resolve thì là bug).

**Ca biên.** Khóa chứa `NaN` → nhóm riêng "khóa không xác định", không gộp, finding `P03.NULL_KEY` (warning).

---

### 6.4 P04 · `outliers`

**Mục đích.** Giá trị bất thường (`yield_t_ha = 387` do lệch dấu thập phân, ruộng 900 ha) vừa kéo lệch trung bình vừa **thổi phồng độ lệch chuẩn** — mà chỉ số cân bằng SMD lại chia cho độ lệch chuẩn, nên chẩn đoán sẽ "đẹp giả". Nhưng xóa hết cũng sai: ruộng lớn có thật là một phần của quần thể.

**Tham số** (`P04Config`):

| Tên | Cho phép | Mặc định | Hành vi |
|---|---|---|---|
| `columns` | list[str] | `["yield_t_ha","field_size_ha","soil_om_baseline_pct","experience_yr"]` | Chỉ cột số; cột bool/category bị bỏ qua kèm finding |
| `method` | `domain_range` \| `iqr` \| `robust_z` \| `percentile` | `robust_z` | Mặc định toàn cục |
| `method_by_column` | dict cột → method | `{yield_t_ha: domain_range, field_size_ha: domain_range}` | Ghi đè `method` |
| `iqr_k` | float | `3.0` | |
| `robust_z_threshold` | float | `3.5` | z bền = `0.6745·(x − median)/MAD`; `MAD = 0` → bỏ qua cột, finding `P04.ZERO_MAD` |
| `percentile_bounds` | [float, float] | `[0.005, 0.995]` | |
| `group_by` | list[str] | `["country"]` | Mức yield nền khác nhau giữa các nước |
| `min_group_size` | int | `30` | Nhóm nhỏ hơn → dùng ngưỡng toàn cục, finding `P04.SMALL_GROUP` |
| `action` | `flag_only` \| `winsorize` \| `to_na` \| `drop_row` \| `log_transform` \| `keep_as_feature` | `flag_only` | |
| `parallel_actions` | list | `["winsorize"]` | Sinh thêm cột `<col>__<action>`, **không** đổi cột gốc |
| `winsorize_at` | `bound` \| `percentile` | `bound` | `bound`: kéo về đúng ngưỡng phát hiện |
| `max_flag_rate` | float | `0.05` | Vượt → `DataQualityError` → status `BLOCKED` |
| `unit_error_detection` | bool | `true` | |
| `unit_error_factors` | list[float] | `[1000, 100, 10, 0.1, 0.01, 0.001]` | |

**Thuật toán.**

1. Với mỗi cột trong `columns`: chọn method (ưu tiên `method_by_column`).
2. `domain_range` lấy `range` từ schema; các method khác tính ngưỡng **trong từng nhóm** `group_by` (nhóm < `min_group_size` dùng ngưỡng toàn cục).
3. Gắn cờ `flag__p04__outlier__<col>`.
4. `unit_error_detection`: với ô bị gắn cờ, thử từng hệ số `f` trong `unit_error_factors`; nếu `value / f` rơi vào `range` của schema thì gắn `flag__p04__suspected_unit_error__<col>` và ghi `f` vào report (**không tự chia** — việc đổi đơn vị là của P02).
5. Áp `action` cho cột gốc; áp `parallel_actions` sinh cột dẫn xuất.
6. Tính tỷ lệ gắn cờ trên toàn bộ dòng (dòng có ≥1 cờ P04). Vượt `max_flag_rate` → `DataQualityError` với thông điệp gợi ý: *"tỷ lệ gắn cờ cao thường là lỗi hệ thống (đơn vị, nhầm cột), hãy kiểm tra lại P02"*.

**Cột sinh ra.** `flag__p04__outlier__<col>`, `flag__p04__suspected_unit_error__<col>`, `<col>__winsorized` / `<col>__log` (nếu bật), `flag__p04__any`.

**Report riêng.** `thresholds`: dict `(column, group) → {lower, upper, method, n_flagged}`; `flag_rate`; `suspected_unit_factors`: dict cột → dict hệ số → số dòng; `summary_before_after`: mean/sd trước và sau mỗi action.

**Mã finding.** `P04.OUTLIERS_FLAGGED` (info) · `P04.SUSPECTED_UNIT_ERROR` (warning) · `P04.MAX_FLAG_RATE_EXCEEDED` (blocking) · `P04.ZERO_MAD` (warning) · `P04.SMALL_GROUP` (info) · `P04.NON_NUMERIC_COLUMN_SKIPPED` (warning).

**Ca biên.** Cột toàn NaN → bỏ qua, finding info. `action = drop_row` phải ghi `rows_dropped` và danh sách `record_id` (tối đa 10 mẫu) vào finding.

---

### 6.5 P05 · `treatment_define`

**Mục đích.** Trả lời "có cover crop nghĩa là gì". Gộp nhiều phiên bản (số tháng, loại cây) thành `A ∈ {0,1}` là một **lựa chọn khoa học**, phải ghi lại và phải đo được độ nhạy theo ngưỡng.

**Tham số** (`P05Config`):

| Tên | Cho phép | Mặc định | Hành vi |
|---|---|---|---|
| `mode` | `binary_threshold` \| `multi_level` \| `per_version` \| `continuous` | `binary_threshold` | `multi_level`/`per_version`/`continuous`: **chỉ tạo cột và báo cáo**, không đổi `treatment_column` |
| `source_column` | str | `cover_crop_months` | Vắng mặt → dùng `cover_crop` sẵn có, finding `P05.FALLBACK_TO_BINARY` |
| `threshold_months` | float | `2.0` | `A = 1` khi `months >= threshold` |
| `threshold_sensitivity` | list[float] | `[1.0, 2.0, 3.0]` | Sinh cột `cover_crop__thr1` … (số nguyên trong tên: `int(thr)`; thr thập phân → thay `.` bằng `p`) |
| `partial_action` | `to_na` \| `treated` \| `control` \| `own_level` | `to_na` | Áp cho giá trị `"Partial"` đã thành `NaN` ở P02 nhưng `cover_crop_months > 0` |
| `type_grouping` | `group` \| `all` \| `keep` | `group` | `group`: gộp theo `{legume, grass, mixed}` |
| `min_cell` | int | `30` | Phiên bản ít hơn → finding cảnh báo |
| `write_treatment_column` | bool | `true` | Ghi đè `cover_crop` bằng định nghĩa mới (luôn ghi giá trị cũ ra `cover_crop__raw`) |

**Thuật toán.**

1. Nếu `source_column` có mặt: `A = (months >= threshold_months)`, `NaN` giữ `NaN`.
2. Sinh cột độ nhạy cho từng ngưỡng trong `threshold_sensitivity`.
3. Lập bảng phiên bản: nhóm theo `cover_crop_type` (đã gộp theo `type_grouping`) × khoảng tháng `[0,1), [1,2), [2,3), [3,6), [6,12]` → `n`, `mean(yield_t_ha)`, `sd`, `n_missing_outcome`.
4. So sánh yield trung bình thô giữa các phiên bản trong nhóm treated; nếu khoảng cách lớn nhất > 1 độ lệch chuẩn gộp → finding `P05.VERSION_HETEROGENEITY` (warning): dấu hiệu vi phạm consistency.
5. Ghi `ctx.treatment_definition = {"source": ..., "rule": "months >= 2.0", "partial_action": ..., "type_grouping": ...}`.

**Cột sinh ra.** `cover_crop__raw`, `cover_crop__thr1`/`__thr2`/`__thr3`, `cover_crop_type__grouped`, `flag__p05__partial`.

**Mã finding.** `P05.FALLBACK_TO_BINARY` (warning) · `P05.VERSION_HETEROGENEITY` (warning) · `P05.SMALL_VERSION_CELL` (warning) · `P05.TREATMENT_MISSING` (warning — số dòng có `A` là NaN) · `P05.THRESHOLD_SENSITIVITY` (info — tỷ lệ treated theo từng ngưỡng).

---

### 6.6 P07 · `time_order`

> Chạy **trước** P08. Giữ nguyên mã P07 (không đổi thành P06) để khớp tài liệu thiết kế.

**Mục đích.** Chặn biến đo **sau** can thiệp khỏi tập điều chỉnh. Đây là lỗi tốn kém nhất trong phân tích quan sát: adjust theo mediator (`soil_om_post_pct`, `weed_pressure`) sẽ chặn mất chính con đường tác động; adjust theo collider (`in_program`) tạo liên hệ giả. **Không chỉ số thống kê nào phát hiện được** — chỉ thứ tự thời gian mới phân biệt được.

**Tham số** (`P07Config`):

| Tên | Cho phép | Mặc định | Hành vi |
|---|---|---|---|
| `time_source` | `schema` \| `name_suffix` \| `both` | `schema` | `name_suffix`: hậu tố `_post` |
| `unknown_action` | `exclude` \| `include` \| `raise` | `exclude` | Mặc định an toàn: loại khỏi L |
| `strict` | bool | `true` | `true`: vi phạm → `ContractError`; `false`: chỉ cảnh báo |
| `allow_post_precision_vars` | bool | `false` | `true` mới cho phép cột `measured_at: post` **và** `affected_by_treatment: false` (ví dụ `season_rain_mm`) vào danh sách ứng viên |
| `allow_post_as_secondary_outcome` | bool | `true` | Cho phép giữ cột post trong dữ liệu để phân tích cơ chế sau này |
| `diagnostics_on_post_vars` | bool | `true` | So sánh mô tả biến post giữa hai nhóm A (chỉ báo cáo) |

**Thuật toán.**

1. Duyệt mọi cột canonical có mặt, lấy `measured_at` (+ `affected_by_treatment`).
2. Xếp mỗi cột vào một trong bốn nhóm: `eligible` (pre/at), `blocked_post` , `blocked_unknown`, `precision_post` (post nhưng không chịu ảnh hưởng can thiệp).
3. Ghi context: `ctx.blocked_columns = blocked_post + blocked_unknown` (+ `precision_post` nếu `allow_post_precision_vars = false`); `ctx.eligible_columns = ` phần còn lại. Hai danh sách rời nhau, đều `sorted()`.
4. Hậu điều kiện bắt buộc: `soil_om_post_pct`, `weed_pressure`, `in_program`, `yield_t_ha` **luôn** nằm trong `blocked_columns`. Nếu không → `ContractError` code `P07.POST_VAR_NOT_BLOCKED`.
5. `diagnostics_on_post_vars`: với mỗi biến post, tính `mean` theo nhóm `A` và chênh lệch chuẩn hóa, đưa vào report (chỉ mô tả).

**Cột sinh ra.** Không (module này chỉ ghi context và báo cáo).

**Report riêng.** `column_time_table`: list `{column, measured_at, affected_by_treatment, dag_role, eligible, reason}` — đây là bảng sẽ đi thẳng vào `data_dictionary.csv`.

**Mã finding.** `P07.BLOCKED_POST_TREATMENT` (info) · `P07.UNKNOWN_TIMING` (warning) · `P07.POST_VAR_NOT_BLOCKED` (error) · `P07.PRECISION_VAR_ALLOWED` (warning — nhắc phải ghi lý do vào báo cáo).

---

### 6.7 P08 · `variable_roles`

**Mục đích.** Dựng tập điều chỉnh **L** từ **vai trò khai báo trong DAG**, không từ độ dự báo. Chọn biến theo độ dự báo sẽ kéo mediator vào (vì mediator dự báo Y rất tốt), kéo biến kiểu instrument (`buyer_incentive`) vào (làm **khuếch đại** bias còn lại), và kéo biến nhiễu vào (làm PS quá khớp → trọng số cực đoan do mô hình tạo ra).

**Tham số** (`P08Config`):

| Tên | Cho phép | Mặc định | Hành vi |
|---|---|---|---|
| `source` | `schema_roles` \| `manual` \| `data_driven` | `schema_roles` | |
| `allow_data_driven` | bool | `false` | `source = data_driven` khi cờ này `false` → `ConfigError` |
| `manual_list` | list[str] | `[]` | Bắt buộc khi `source = manual` |
| `include_roles` | list | `["confounder"]` | |
| `include_precision_vars` | bool | `true` | Thêm `outcome_predictor` (W) — giảm phương sai, không gây lệch |
| `exclude_roles` | list | `["mediator","collider","instrument","noise","outcome","treatment","treatment_version","id"]` | |
| `ambiguous_action` | `both` \| `include` \| `exclude` | `both` | Cho `no_till`, `organic_fert`, `rotation_len_yr` (vai trò O chưa rõ) |
| `basis.continuous` | `linear` \| `quadratic` \| `spline` | `quadratic` | **Chỉ khai báo**, không sinh cột: ghi vào context cho bước PS sau này |
| `basis.spline_df` | int | `4` | |
| `interactions` | list[list[str]] | `[["country","*"]]` | Khai báo dạng ký hiệu, không sinh cột |
| `rare_level_action` | `group` \| `keep` \| `drop` | `group` | |
| `rare_level_threshold` | float | `0.01` | Mức category chiếm < 1% → gộp thành `"other"` |
| `min_variation` | float | `1e-12` | Cột phương sai ~0 → loại, finding |

**Thuật toán.**

1. Lấy danh sách ứng viên = `ctx.eligible_columns` (do P07 ghi; thiếu khóa này → `DependencyError`).
2. Lọc theo `include_roles` / `exclude_roles`; `id`, `cluster` luôn bị loại.
3. `ambiguous_action = both` → tạo hai biến thể:
   `adjustment_set_variants = {"O_as_confounder": L ∪ {no_till, organic_fert, rotation_len_yr}, "O_as_mediator": L}`; `adjustment_set` (chính) = biến thể `O_as_confounder`, và finding `P08.AMBIGUOUS_ROLE` (warning) nhắc phải báo cáo cả hai.
4. Kiểm tra hậu điều kiện **bắt buộc** (nếu sai → `ContractError`):
   - `soil_om_post_pct`, `weed_pressure`, `in_program`, `buyer_incentive`, mọi `noise_*`, `yield_t_ha`, `cover_crop` **không** nằm trong `adjustment_set`.
5. Gộp mức hiếm, loại cột gần như không biến thiên.
6. Ghi `ctx.adjustment_set`, `ctx.adjustment_set_variants`.

**Artifact.** `data_dictionary`: DataFrame `{column, dtype, measured_at, affected_by_treatment, dag_role, in_L, variant_membership, reason}` — ghi ra `data/processed/<run_id>/data_dictionary.csv`.

**Mã finding.** `P08.ADJUSTMENT_SET_BUILT` (info, `details.columns = L`) · `P08.AMBIGUOUS_ROLE` (warning) · `P08.RARE_LEVEL_GROUPED` (info) · `P08.ZERO_VARIANCE_DROPPED` (warning) · `P08.DATA_DRIVEN_USED` (warning — luôn kèm câu cảnh báo trong message) · `P08.FORBIDDEN_COLUMN_IN_L` (error).

---

### 6.8 P06 · `missingness`

> Chạy **sau** P08: chỉ xử lý thiếu cho biến thật sự dùng (`L ∪ {A, Y}`).

**Mục đích.** Ba tác hại khác nhau: (a) thiếu covariate khiến thư viện mô hình **tự động bỏ dòng** — quần thể phân tích đổi mà không ai chủ động quyết định; (b) thiếu outcome làm complete-case bị lệch nếu việc thiếu phụ thuộc L, A; (c) thiếu có cấu trúc (một nước không hỏi một câu).

**Tham số** (`P06Config`):

| Tên | Cho phép | Mặc định | Hành vi |
|---|---|---|---|
| `scope` | `adjustment_set_plus_ay` \| `all_columns` | `adjustment_set_plus_ay` | |
| `outcome_missing` | `ipcw_flag` \| `complete_case` \| `both` | `ipcw_flag` | `ipcw_flag`: **không bỏ dòng**, chỉ tạo `c_outcome_observed` cho K07 dùng sau |
| `covariate_missing` | `median_indicator` \| `drop_row` \| `category_missing` | `median_indicator` | `median_indicator`: điền trung vị + cột cờ |
| `impute_group_by` | list[str] | `["country"]` | Nhóm < `min_group_size` → dùng trung vị toàn cục |
| `min_group_size` | int | `30` | |
| `keep_indicator` | bool | `true` | Tắt sẽ làm mất thông tin "hộ này không trả lời" |
| `max_missing_col` | float | `0.40` | Cột thiếu quá ngưỡng → loại khỏi L (ghi lý do), finding |
| `mechanism_check` | list | `["describe","regress"]` | `regress`: hồi quy logistic cờ thiếu theo `L ∪ {A}` bằng `sklearn.linear_model.LogisticRegression` |
| `diff_warn_threshold` | float | `0.05` | Chênh lệch tỷ lệ thiếu giữa hai nhóm A vượt 5 điểm % → warning |

**Thuật toán.**

1. Xác định phạm vi cột theo `scope` (cần `ctx.adjustment_set`; thiếu → `DependencyError`).
2. Lập bảng thiếu: theo cột × `country` × nhóm A.
3. Tạo `c_outcome_observed = yield_t_ha.notna()`.
4. `mechanism_check`:
   - `describe`: tỷ lệ thiếu theo nhóm A và theo nước;
   - `regress`: hồi quy `c_outcome_observed` theo `L ∪ {A}` (chuẩn hóa biến số, one-hot category, `max_iter=1000`); báo cáo hệ số lớn nhất theo trị tuyệt đối (**không** kết luận MAR/MNAR — chỉ mô tả).
5. Xử lý thiếu covariate theo `covariate_missing`; mọi cột được điền phải có `flag__p06__imputed__<col>` khi `keep_indicator = true`.
6. Cột vượt `max_missing_col` → loại khỏi `ctx.adjustment_set` (cập nhật context) và ghi finding.
7. Nếu `outcome_missing = complete_case`: bỏ dòng thiếu outcome, ghi `rows_dropped`.

**Cột sinh ra.** `c_outcome_observed` (bool), `flag__p06__imputed__<col>`, `flag__p06__missing_any_L`.

**Report riêng.** `missing_by_column` (tỷ lệ tổng, theo nước, theo nhóm A), `pattern_counts` (10 mẫu thiếu phổ biến nhất), `imputation`: dict cột → `{method, n_imputed, value_used_by_group}`, `mechanism`: hệ số hồi quy.

**Mã finding.** `P06.MISSING_SUMMARY` (info) · `P06.MISSING_DIFFERS_BY_TREATMENT` (warning) · `P06.COLUMN_DROPPED_HIGH_MISSING` (warning) · `P06.IMPUTED` (info) · `P06.STRUCTURAL_MISSING` (warning — một cột thiếu 100% trong ít nhất một nước) · `P06.OUTCOME_MISSING_RATE` (info).

---

### 6.9 P09 · `clusters`

**Mục đích.** Một nông hộ có nhiều ruộng/nhiều năm; các dòng đó không độc lập. Hai hậu quả: sai số chuẩn bị đánh giá thấp (độ phủ < 95%), và rò rỉ thông tin giữa các fold nếu chia ngẫu nhiên khi cross-fit.

**Tham số** (`P09Config`):

| Tên | Cho phép | Mặc định | Hành vi |
|---|---|---|---|
| `cluster_key` | str \| null | `grower_id` | `null` → coi mỗi dòng là một cụm, finding cảnh báo |
| `fold_strategy` | `group_stratified` \| `group` \| `random` | `group_stratified` | `group_stratified`: `StratifiedGroupKFold` phân tầng theo `A` |
| `n_folds` | int ≥ 2 | `5` | |
| `seed` | int | `20260921` | Truyền vào `ctx.rng`; ghi vào report |
| `year_handling` | `fixed_effect` \| `second_cluster` \| `ignore` | `fixed_effect` | Chỉ **khai báo** vào context, không sinh cột |
| `large_cluster_warn` | float | `0.05` | Một cụm chiếm > 5% mẫu → warning (dấu hiệu lỗi ghép bảng) |
| `compute_icc` | bool | `true` | ICC thô của `yield_t_ha` bằng phân rã phương sai một chiều |

**Thuật toán.**

1. `cluster_id = cluster_key` (ép chuỗi). Dòng thiếu khóa → `cluster_id = "singleton__" + record_id`, finding warning.
2. Thống kê: số cụm, phân phối kích thước (min/median/max/p95), tỷ lệ dòng nằm trong cụm > 1.
3. Chia fold: `group_stratified` cần `A` không NaN — dòng có `A` NaN được gán `fold_id = -1` và **không** tham gia phân tầng, finding info.
4. Hậu điều kiện bắt buộc: không cụm nào xuất hiện ở hai fold ≥ 0 khác nhau. Sai → `ContractError` code `P09.CLUSTER_SPLIT_ACROSS_FOLDS`.
5. ICC thô = `var_between / (var_between + var_within)` trên `yield_t_ha` (bỏ NaN); cụm < 2 dòng không đóng góp `var_within`.

**Cột sinh ra.** `cluster_id` (string), `fold_id` (int8).

**Mã finding.** `P09.CLUSTER_SUMMARY` (info) · `P09.LARGE_CLUSTER` (warning) · `P09.MISSING_CLUSTER_KEY` (warning) · `P09.CLUSTER_SPLIT_ACROSS_FOLDS` (error) · `P09.ICC_ESTIMATE` (info).

---

## 7. `configs/preprocess.yaml`

Cấu trúc: một khóa cho mỗi module, tên khóa = mã module viết thường; thêm khối `defaults`.

```yaml
version: 1
defaults:
  seed: 20260921
  fail_fast: true          # dừng ngay khi một module FAILED/BLOCKED
steps: [P01, P02, P03, P04, P05, P07, P08, P06, P09]
p01: { on_error: quarantine, dtype_coercion: permissive, out_of_range: to_na, ... }
p02: { ... }
...
p09: { ... }
```

Yêu cầu: **mọi tham số trong bảng của §6 đều phải xuất hiện tường minh trong file này với đúng giá trị mặc định** (không dựa vào default ẩn trong code) — để người dùng đọc file là thấy hết lựa chọn. Mỗi tham số kèm một comment tiếng Việt ≤ 1 dòng.

Cấu hình được validate bằng pydantic: sai kiểu / giá trị ngoài danh sách → `ConfigError` nêu rõ **đường dẫn khóa** (`p04.action`) và **các giá trị hợp lệ**.

---

## 8. Pipeline và cơ chế báo lỗi theo module

### 8.1 Yêu cầu cốt lõi

> Khi chạy cả chuỗi mà một module hỏng, người dùng phải biết **ngay lập tức và không mơ hồ**: hỏng ở module nào, mã lỗi gì, dữ liệu vào bước đó ra sao, và bước nào đã chạy xong.

### 8.2 `pipeline/steps.py` — hợp đồng quanh mỗi bước

Mỗi bước được bọc bởi `run_step(step_spec, df, cfg, ctx)` làm đúng trình tự:

1. **Tiền kiểm tra:** cột bắt buộc của module có mặt; khóa context cần thiết có mặt (thiếu → `DependencyError`).
2. Ghi `n_rows_in`, `n_cols_in`, chụp `set` tên cột và `record_id` (dùng `hash` của chuỗi đã sắp xếp) để so sánh sau.
3. Gọi `module.run(...)` trong `try/except`.
4. **Hậu kiểm tra (bắt buộc, dùng chung cho mọi module):**
   - Không mất dòng nếu module không khai báo `rows_dropped` > 0 → sai thì `ContractError`.
   - Không mất cột canonical nào.
   - Cột mới đúng quy ước §4.6 và khớp `columns_added` trong report.
   - `record_id` vẫn duy nhất.
5. Gắn `duration_s`, `status`.

### 8.3 `pipeline/runner.py` — xử lý lỗi

| Tình huống | Hành vi |
|---|---|
| Module trả `OK` / `OK_WITH_WARNINGS` | Ghi `data/interim/<run_id>/after_<module_id>.parquet` (bật/tắt bằng `pipeline.yaml: save_interim`), chạy tiếp |
| Module raise `DataQualityError` | status `BLOCKED`; `fail_fast: true` → dừng; ghi `run_report.json` với `failed_step` |
| Module raise `RaCausalError` khác | status `FAILED`, dừng |
| Module raise ngoại lệ **không** thuộc cây `RaCausalError` | Bọc lại thành `ContractError` với `code = "<MODULE_ID>.UNEXPECTED_EXCEPTION"`, giữ nguyên traceback trong `details.traceback` (tối đa 50 dòng cuối), status `FAILED` |

Khi dừng, runner **luôn** phải: ghi `run_report.json`, ghi dữ liệu trung gian cuối cùng chạy thành công, in ra stderr đúng một khối 6 dòng:

```
PIPELINE FAILED
  step        : P04 (outliers)
  code        : P04.MAX_FLAG_RATE_EXCEEDED
  message     : Tỷ lệ dòng bị gắn cờ 18.0% vượt ngưỡng 5.0%
  rows in/out : 1982 / -
  report      : data/reports/<run_id>/run_report.json
```

### 8.4 `run_report.json` — schema cố định

```
{
  "run_id", "started_at", "finished_at", "duration_s",
  "status",                         # ok | warning | blocked | failed
  "failed_step": null | "P04",
  "config_digest",                  # sha256 của config đã merge, 12 ký tự đầu
  "schema_version",
  "input": {"path", "n_rows", "n_cols", "adapter"},
  "steps": [ <StepReport>, ... ],   # theo đúng thứ tự chạy
  "context_final": {"adjustment_set": [...], "treatment_definition": {...},
                    "cluster_column", "fold_column", "outcome_observed_column"},
  "outputs": {"analysis_ready", "data_dictionary", "artifacts": {...}}
}
```

### 8.5 `configs/pipeline.yaml`

`input` (path, adapter: `raw_assumed` | `canonical` | `ciat`), `output_dir`, `save_interim: true`, `fail_fast: true`, `log_level: INFO`, `steps` (kế thừa từ `preprocess.yaml`, cho phép ghi đè để chạy một phần).

### 8.6 Đầu ra cuối

`data/processed/<run_id>/`: `analysis_ready.parquet`, `data_dictionary.csv`, `run_report.json` (bản sao), `artifacts/{quarantine.parquet, review_list.parquet}`.

---

## 9. CLI

Hai lệnh, dùng `argparse`, đặt entry point trong `pyproject.toml`.

**1. Chạy cả chuỗi**

```
python -m ra_causal.cli.run_pipeline \
    --config configs/pipeline.yaml \
    --input data/raw/<file>.csv \
    --output data/processed \
    [--steps P01,P02,P03] [--from P03] [--to P06] \
    [--dry-run] [--log-level DEBUG]
```

`--dry-run`: validate config + schema + đọc 1000 dòng đầu, không ghi file.

**2. Chạy một module độc lập** (phục vụ đúng yêu cầu "test từng module riêng")

```
python -m ra_causal.cli.run_step P04 \
    --input data/interim/<run_id>/after_P03.parquet \
    --config configs/preprocess.yaml \
    --output data/interim/manual/ \
    [--set p04.action=winsorize] [--set p04.max_flag_rate=0.2]
```

- `--set` cho phép ghi đè tham số theo đường dẫn khóa, ép kiểu theo model pydantic.
- Lệnh này dựng một `PipelineContext` **tối thiểu**; nếu module cần khóa context chưa có (vd P06 cần `adjustment_set`), CLI phải báo lỗi rõ: *"P06 cần ctx.adjustment_set do P08 tạo; hãy chạy `--from P08` hoặc truyền `--context <file json>`"*, và hỗ trợ `--context` đọc JSON.

**Mã thoát:** `0` ok · `1` lỗi cấu hình/đối số · `2` một module FAILED · `3` BLOCKED · `4` lỗi nội bộ không lường trước.

---

## 10. Chiến lược test

### 10.1 Bố cục

```
tests/
├── conftest.py               # fixture dùng chung, gọi tests/fixtures/make_frames.py
├── fixtures/make_frames.py   # factory dữ liệu + injector lỗi (KHÔNG phải bộ mô phỏng nhân quả)
├── core/        test_contracts.py, test_errors.py, test_schema.py, test_registry.py
├── preprocess/  test_p01_schema_check.py … test_p09_clusters.py   (9 file)
├── pipeline/    test_runner_ordering.py, test_error_localization.py, test_run_report.py
└── integration/ test_preprocess_chain.py, test_cli.py
```

Marker: `@pytest.mark.unit`, `@pytest.mark.integration`. Toàn bộ `unit` phải chạy xong **< 60 giây**.

### 10.2 Factory dữ liệu (`tests/fixtures/make_frames.py`)

Vì `simulate/` chưa làm, test tự sinh dữ liệu **bằng pandas thuần, xác định**, không mô hình nhân quả:

```
make_clean_frame(n: int = 200, seed: int = 0) -> pd.DataFrame
```
Sinh đúng các cột canonical, giá trị nằm trong `range`, `country` phân bố `[80, 60, 40, 20]`, `grower_id` lặp theo mẫu (khoảng 60% hộ có 1 dòng, 30% có 2, 10% có 3+), không có NaN, `yield_t_ha` trong `[5, 60]`.

Mỗi injector trả về `(df, truth)` với `truth` là **danh sách `record_id` đã bị làm hỏng** — đây chính là đáp án cho "test tìm lại":

| Injector | Chữ ký | Làm gì |
|---|---|---|
| `inject_country_variants` | `(df, frac=0.1, seed)` | Đổi `country` thành `"Country 1"`, `" c1 "`, `"C-1"` |
| `inject_unit_mix` | `(df, frac=0.2, seed)` | Nhân `yield_t_ha` × 1000 (kg/ha) |
| `inject_duplicates` | `(df, n_exact=5, n_partial=3, n_conflict=2, seed)` | Nhân bản dòng; `partial` đổi `noise_1`; `conflict` đổi `cover_crop` |
| `inject_outliers` | `(df, n=5, factor=10, seed)` | Nhân `yield_t_ha` × factor |
| `inject_missing` | `(df, col_fracs: dict, seed)` | Đặt NaN theo cột |
| `inject_schema_errors` | `(df, n=5, seed)` | Chuỗi vào cột số, giá trị ngoài `range`, `record_id` rỗng |
| `inject_treatment_versions` | `(df, seed)` | Điền `cover_crop_months`, `cover_crop_type` |
| `make_dirty_frame` | `(n=300, seed=0)` | Gộp tất cả injector, trả `(df, truth_all)` |

Ràng buộc: mọi injector **không** thay đổi số dòng trừ `inject_duplicates`; mọi thứ xác định theo `seed`.

### 10.3 Năm loại test bắt buộc cho **mỗi** module

| Loại | Kiểm tra gì | Ví dụ cụ thể (bắt buộc có) |
|---|---|---|
| **1. Hợp đồng** | Trả về `StepResult`; `report.to_dict()` `json.dumps` được; không sửa `df` gốc (so `df.equals(df_before)`); không đổi tên cột canonical | `test_p04_contract_does_not_mutate_input` |
| **2. Tìm lại** | Phát hiện **đúng** tập đã cài, không thừa không thiếu | `test_p03_recovers_injected_duplicates`: tập `record_id` bị gắn `flag__p03__duplicate` == `truth["duplicates"]` |
| **3. Lựa chọn tham số** | Mỗi giá trị cho phép làm đúng điều nó hứa | P04: `flag_only` giữ nguyên `n_rows` và giá trị; `drop_row` giảm đúng số dòng đã gắn cờ; `winsorize` giữ `n_rows` nhưng `max` giảm; `to_na` làm số NaN tăng đúng bằng số ô bị cờ |
| **4. Phản ứng đúng chiều** | Vặn tham số thì kết quả đổi đúng hướng | P04: tăng `robust_z_threshold` ⇒ số cờ **không tăng**. P05: tăng `threshold_months` ⇒ tỷ lệ treated **không tăng**. P06: tăng `max_missing_col` ⇒ số cột bị loại **không tăng** |
| **5. Không làm gì khi không cần** | Trên dữ liệu sạch, module không đổi dữ liệu | Chạy cả 9 module trên `make_clean_frame()` ⇒ `rows_dropped == 0`, mọi cờ `False`, `status in {OK, OK_WITH_WARNINGS}` |

Thêm hai test chung cho mọi module (viết một lần, `pytest.mark.parametrize` qua 9 module):

- **Idempotent:** chạy hai lần liên tiếp cho `data` bằng nhau (so `pd.testing.assert_frame_equal`).
- **Xác định:** hai lần chạy độc lập cùng seed cho cùng `data` và cùng `report` (bỏ qua `started_at`, `duration_s`).

### 10.4 Test cho pipeline

| Test | Nội dung |
|---|---|
| `test_runner_ordering` | Thứ tự chạy đúng `P01→P02→P03→P04→P05→P07→P08→P06→P09`; `steps` trong report đúng thứ tự đó |
| `test_error_localization` | Ép P04 hỏng (`max_flag_rate=0.001` trên dữ liệu có outlier) ⇒ `run_report["failed_step"] == "P04"`, `status == "blocked"`, các bước trước có `status ok`, các bước sau **không** xuất hiện trong `steps`, exit code `3` |
| `test_unexpected_exception_wrapped` | Monkeypatch một module raise `ValueError` ⇒ code `"<ID>.UNEXPECTED_EXCEPTION"`, có `details.traceback`, exit code `2` |
| `test_dependency_error` | Chạy `--steps P06` một mình ⇒ `DependencyError` nêu rõ thiếu `adjustment_set` |
| `test_run_report_schema` | Mọi khóa ở §8.4 có mặt, JSON hợp lệ |
| `test_golden_run` | Chạy chuỗi trên `make_dirty_frame(n=300, seed=0)`; so `run_report` rút gọn (bỏ thời gian) với `tests/fixtures/golden_run_report.json`; lệch ⇒ fail, kèm hướng dẫn cập nhật golden có chủ ý |

### 10.5 Test cho `core/`

Kiểm tra `jsonify` xử lý `numpy.int64`, `NaN`, `Timestamp`, `Categorical`; registry không cho đăng ký trùng mã; schema loader bắt được YAML thiếu trường bắt buộc.

---

## 11. Định nghĩa "xong" (agent tự kiểm trước khi bàn giao)

- [ ] Cây thư mục đúng §2; thư mục ngoài phạm vi chỉ có `__init__.py` rỗng.
- [ ] 9 module đúng chữ ký §4.5, đúng tham số §6 (không thừa, không thiếu một tham số nào).
- [ ] Mọi giá trị mặc định xuất hiện tường minh trong `configs/preprocess.yaml`.
- [ ] Mọi mã finding dùng trong code đều nằm trong bảng của §6; không có mã lạ.
- [ ] `pytest -m unit` xanh, < 60s; `pytest` toàn bộ xanh.
- [ ] Chạy thử `run_pipeline --dry-run` trên `make_dirty_frame` xuất được `run_report.json` hợp lệ.
- [ ] Test định vị lỗi (§10.4) chứng minh được: hỏng ở P04 thì report chỉ đúng P04.
- [ ] `docs/OPEN_QUESTIONS.md` liệt kê mọi chỗ spec thiếu mà agent gặp (nếu không có thì ghi "không có").
- [ ] README.md ở gốc: cài đặt, 3 lệnh ví dụ, bảng 9 module một dòng mỗi module, trỏ tới spec này.

---

## 12. Cấm và cách xử lý khi spec thiếu

### 12.1 Danh sách cấm

1. Cấm code bất kỳ thứ gì trong `process/`, `estimate/`, `evaluate/`, `simulate/`, `reporting/`.
2. Cấm tự thêm module tiền xử lý thứ 10.
3. Cấm đổi thứ tự chạy ở §6.
4. Cấm xóa dòng ngoài các tham số cho phép (`P01.on_error=quarantine`, `P03.resolve`, `P04.action=drop_row`, `P06.outcome_missing=complete_case`).
5. Cấm `print` trong code thư viện (chỉ CLI được in, và chỉ qua logger/stderr).
6. Cấm bắt `Exception` rồi nuốt lỗi.
7. Cấm dùng `inplace=True` của pandas.
8. Cấm suy luận vai trò biến từ dữ liệu khi `allow_data_driven = false`.
9. Cấm đặt bất kỳ ngưỡng số nào trong code mà không đi qua config.

### 12.2 Mẫu ghi vào `docs/OPEN_QUESTIONS.md`

```markdown
### Q-<nn> · <module> · <tiêu đề ngắn>
- **Chỗ thiếu trong spec:** ...
- **Phương án tạm dùng:** ... (nguyên tắc: an toàn nhất = chỉ gắn cờ, không đổi dữ liệu)
- **Ảnh hưởng nếu chọn khác:** ...
- **Vị trí trong code:** `src/ra_causal/preprocess/p0x_....py:<hàm>`
```

---

## 13. Gợi ý thứ tự thi công (cho agent)

1. `core/` + `io/` + `configs/schema/canonical.yaml` + test `core/` → nền móng.
2. `tests/fixtures/make_frames.py` → có dữ liệu trước khi có module (viết test trước).
3. P01 → P02 → P03 → P04 (mỗi module: viết test trước, rồi code, rồi chạy `pytest tests/preprocess/test_p0x_*.py`).
4. P05 → P07 → P08 → P06 → P09.
5. `pipeline/` + `cli/` + test định vị lỗi + golden run.
6. README + OPEN_QUESTIONS + tự kiểm §11.
