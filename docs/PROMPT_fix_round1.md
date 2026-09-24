# Prompt sửa lỗi vòng 1 — khối tiền xử lý `ra_causal`

Dán nguyên khối dưới đây cho agent lập trình (quyền đọc/ghi trong `/home/doan/Seminar/ra_causal`).

---

Bạn tiếp tục công việc trên dự án `/home/doan/Seminar/ra_causal`. Khối tiền xử lý P01–P09 đã được viết nhưng **chưa chạy được end-to-end**, kể cả trên dữ liệu sạch. Nhiệm vụ lần này: **sửa cho chạy đúng, rồi phủ test, rồi hiện thực nốt các tham số đang bị bỏ trống.**

Bản thiết kế vẫn là `docs/SPEC_preprocessing.md` — **không sửa file đó**, không đổi tên tham số, không đổi thứ tự chạy, không thêm thư viện. Mô tả hiện trạng nằm ở `src/ra_causal/preprocess/README.md` §9.

## 0. Môi trường (làm trước tiên)

```bash
cd /home/doan/Seminar/ra_causal
python -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/pip install -e .
./.venv/bin/python -c "import pandas, pydantic; print(pandas.__version__, pydantic.VERSION)"
```

Bắt buộc dùng **pandas 2.x** và **pydantic 2.x** đúng như `requirements.txt`. Cập nhật `pyproject.toml` cho khớp chặn phiên bản trong `requirements.txt` (đặc biệt `pandas<3.0`, `pydantic<3.0`).

**Mọi lệnh kiểm chứng trong prompt này phải chạy bằng `./.venv/bin/python`.** Không báo "xong" nếu chưa tự chạy lệnh và nhìn thấy kết quả.

---

## GIAI ĐOẠN 1 — Năm lỗi chặn

Sửa theo đúng thứ tự dưới đây; sau mỗi lỗi, chạy lệnh kiểm chứng kèm theo.

### 1.1 Registry rỗng → cả hai lệnh CLI chết ngay

**Triệu chứng thật:**
```
$ ./.venv/bin/python -m ra_causal.cli.run_pipeline --config configs/pipeline.yaml \
      --input data/raw/dirty.csv --output data/out
KeyError: 'Module P01 not found in registry.'
```

**Nguyên nhân.** `@REGISTRY.register(...)` chỉ chạy khi module được import. `src/ra_causal/pipeline/runner.py` và `src/ra_causal/cli/run_step.py` import `REGISTRY` từ `core.registry` nhưng **không bao giờ import gói `ra_causal.preprocess`**, nên registry luôn rỗng.

**Yêu cầu sửa.**
- Nạp registry một cách tường minh: thêm `import ra_causal.preprocess  # noqa: F401 — nạp registry` vào `pipeline/runner.py` và `cli/run_step.py` (hoặc gọn hơn: nạp trong `ra_causal/pipeline/__init__.py`, miễn là cả hai đường vào đều chắc chắn có).
- Thêm kiểm tra sớm: trước vòng lặp, nếu mã bước không có trong registry thì `raise ConfigError` với thông điệp liệt kê **các mã đang đăng ký**, thay vì để `KeyError` thô bay ra.
- `KeyError` trần không được phép thoát ra khỏi CLI: bọc lại thành `ConfigError` (mã thoát 1).

**Kiểm chứng:** lệnh ở trên không còn `KeyError`, và `run_step` cũng vậy:
```bash
./.venv/bin/python -m ra_causal.cli.run_step P04 --input data/raw/clean.csv \
    --config configs/preprocess.yaml --output data/interim/manual/
```

### 1.2 P01 ép kiểu số nguyên/bool làm crash khi có ô trống

**Triệu chứng thật** (chạy chuỗi trên dữ liệu bẩn):
```
PIPELINE FAILED
  step        : P01
  code        : P01.UNEXPECTED_EXCEPTION
  message     : Cannot convert non-finite values (NA or inf) to integer
```

**Nguyên nhân.** `src/ra_causal/preprocess/p01_schema_check.py:83` gọi `coerced.astype(contract.dtype)` với `dtype` kiểu numpy (`int16`, `int8`) — không chứa được `NaN`. Cột `boolean` cũng gặp vấn đề tương tự khi có ô trống. Đây là nghịch lý: module dọn dữ liệu bẩn lại chết vì dữ liệu bẩn.

**Yêu cầu sửa.**
- Ánh xạ mọi dtype của schema sang **kiểu nullable của pandas** khi ép: `int8 → Int8`, `int16 → Int16`, `float32 → Float32` (hoặc giữ `float32` vì float chứa được NaN), `boolean → boolean`, `string → string`, `category → category`. Viết ánh xạ này thành **một hàm dùng chung** trong `utils/pandas_tools.py`, ví dụ `to_schema_dtype(series, dtype) -> Series`, và dùng ở mọi nơi cần ép kiểu.
- Không được `try/except: pass` nuốt lỗi ép kiểu ở nhánh `strict` (hiện tại `p01_schema_check.py:86-89` đang làm vậy): `strict` phải `raise SchemaError` mã `P01.COERCE_FAILED`.
- Sau P01, mọi cột phải mang đúng kiểu nullable — các module sau dựa vào điều này.

**Kiểm chứng:** chuỗi đầy đủ chạy qua được P01 trên `data/raw/dirty.csv` (tạo dữ liệu theo §1.6).

### 1.3 P02 chặn cả dữ liệu hợp lệ vì bảng alias rỗng

**Triệu chứng thật** (chạy trên dữ liệu **sạch**, hoàn toàn đúng schema):
```
PIPELINE FAILED
  step        : P02
  code        : P02.UNMAPPED_CATEGORY
  message     : Unmapped value 'c1' in country
```

**Nguyên nhân.** Ba thứ cộng lại: `configs/schema/raw_assumed.yaml` có `country_aliases: {}` (rỗng); `string_normalize.lower: true` biến `C1` hợp lệ thành `c1`; `unmapped_action.overrides.country: raise`. Kết quả: **không giá trị nào qua được P02.**

**Yêu cầu sửa.**
- Chuẩn hóa chỉ dùng để **so khớp**, không phải để ghi đè: sau khi tra alias, giá trị ghi ra phải là **mã canonical đúng hoa/thường** theo `allowed` trong `canonical.yaml`.
- Quy tắc tra cứu theo thứ tự: (1) khớp trực tiếp với `allowed` của schema sau khi chuẩn hóa hai vế → giữ nguyên mã canonical; (2) khớp bảng alias; (3) fuzzy nếu bật; (4) thất bại → `unmapped_action`.
- Điền `country_aliases` trong `raw_assumed.yaml` cho **đúng các biến thể mà fixture sinh ra** (`"Country 1"`, `"c1 "`, `"C-1"` → `C1`, tương tự C2–C4). Không bịa thêm alias ngoài các biến thể này.
- Điền `column_aliases` và `unit_declarations` nếu fixture có dùng; nếu không dùng thì để rỗng kèm comment nói rõ "chưa có dữ liệu thật".

**Kiểm chứng:** chạy toàn bộ chuỗi trên `data/raw/clean.csv` phải **không** phát `P02.UNMAPPED_CATEGORY` và không đổi giá trị cột `country` (so sánh trước/sau).

### 1.4 P03 crash khi nhóm trùng có cột boolean

**Triệu chứng thật:** `TypeError: numpy boolean subtract, the '-' operator, is not supported`

**Nguyên nhân.** `src/ra_causal/preprocess/p03_deduplicate.py:71-74`: `pd.api.types.is_numeric_dtype` trả `True` cho cột bool, rồi code tính `np.nanmax(non_na) - np.nanmin(non_na)`.

**Yêu cầu sửa.**
- Tách ba nhánh so sánh rõ ràng: **số thực/nguyên** (so theo `numeric_tolerance`), **boolean** (so bằng `nunique(dropna=True) > 1`), **chuỗi/category** (so bằng `nunique`).
- Xử lý `NaN` nhất quán: hai dòng cùng `NaN` ở một cột **không** tính là khác nhau; một dòng có giá trị và một dòng `NaN` thì **tính là khác** (giữ đúng hành vi hiện tại).
- Không dùng `.values` + hàm numpy trên cột kiểu extension (`Int16`, `boolean`, `string`); làm việc trực tiếp trên `Series`.

**Kiểm chứng:** P03 chạy được trên `data/raw/clean.csv` và trên `data/raw/dirty.csv`; số nhóm `exact/partial/conflict` khớp với `truth["duplicates"]` của fixture.

### 1.5 P09 crash khi chia fold

**Triệu chứng thật:** `ValueError: Supported target types are: ('binary', 'multiclass'). Got 'unknown' instead.`

**Nguyên nhân.** `p09_clusters.py:66-67` truyền thẳng `cover_crop` (kiểu `boolean` nullable, có `pd.NA` do P05 tạo) vào `StratifiedGroupKFold`. scikit-learn không hiểu kiểu này.

**Yêu cầu sửa.**
- Chỉ phân tầng trên các dòng có `A` **không rỗng**, và ép `A` sang `int` (`0/1`) trước khi truyền vào scikit-learn.
- Dòng có `A` rỗng: `fold_id = -1` và phát một `Finding` mức `info` (đã có trong thiết kế).
- Nếu sau khi lọc mà một lớp có ít hơn `n_folds` mẫu, hoặc số cụm nhỏ hơn `n_folds`, thì **lùi về** `GroupKFold` và phát `Finding` mức `warning` giải thích lý do — không để scikit-learn ném lỗi thô.
- Dùng `ctx.rng` để sinh `random_state` thay vì đọc thẳng `cfg.seed` (thiết kế §4.7 yêu cầu mọi ngẫu nhiên đi qua `ctx.rng`); vẫn phải tái lập được.

**Kiểm chứng:** hậu điều kiện "không cụm nào nằm ở hai fold" vẫn đúng, và chuỗi chạy hết P09.

### 1.6 Nghiệm thu giai đoạn 1

Sửa `generate_data.py` (đang import sai `ra_causal.tests.fixtures...`; đường dẫn đúng là `tests.fixtures.make_frames`) để sinh cả hai file, hoặc thay bằng một lệnh CLI nhỏ:

```bash
./.venv/bin/python -c "
from tests.fixtures.make_frames import make_clean_frame, make_dirty_frame
make_clean_frame(200, 0).to_csv('data/raw/clean.csv', index=False)
make_dirty_frame(300, 0)[0].to_csv('data/raw/dirty.csv', index=False)"
```

Cả hai lệnh sau phải chạy hết 9 bước và trả mã thoát 0:

```bash
./.venv/bin/python -m ra_causal.cli.run_pipeline --config configs/pipeline.yaml --input data/raw/clean.csv --output data/out_clean; echo "exit=$?"
./.venv/bin/python -m ra_causal.cli.run_pipeline --config configs/pipeline.yaml --input data/raw/dirty.csv --output data/out_dirty; echo "exit=$?"
```

Kiểm tra thêm trong `run_report.json` của lần chạy **sạch**: không có finding mức `error`, `rows_dropped` bằng 0 ở mọi bước, và `context_final.adjustment_set` không rỗng.

---

## GIAI ĐOẠN 2 — Test (phần đang thiếu nhiều nhất)

Hiện có 7 test, 2 fail, 2 file không import được, và **không có test nào cho 9 module**. Đây là lý do năm lỗi trên lọt lưới.

### 2.1 Sửa những gì đang hỏng

- `tests/pipeline/test_runner_ordering.py` và `tests/pipeline/test_error_localization.py` import `ra_causal.tests.fixtures.make_frames` — sai. Đường dẫn đúng: `tests.fixtures.make_frames`.
- `tests/integration/test_cli.py::test_cli_dry_run` tính sai thư mục gốc (`../../..`) và gọi `python` trần. Sửa để chạy bằng `sys.executable` và `cwd` là gốc dự án.
- `tests/core/test_schema.py::test_schema_affected_by_treatment_validation` đang fail: validate trong `core/schema.py` không bắt lỗi như test mong đợi. Xác định bên nào đúng theo `SPEC_preprocessing.md §5.1` (cột `measured_at: post` **bắt buộc** khai `affected_by_treatment`; cột khác thì không được khai) rồi sửa cho khớp — nêu rõ trong báo cáo bạn đã sửa test hay sửa code, và vì sao.
- Thêm `pytest.ini` hoặc mục `[tool.pytest.ini_options]` trong `pyproject.toml`: khai `testpaths`, `markers = ["unit", "integration"]`, và `pythonpath = ["src", "."]` để không phải dựng `PYTHONPATH` thủ công.

### 2.2 Viết đủ 9 file test cho 9 module

`tests/preprocess/test_p01_schema_check.py` … `test_p09_clusters.py`. Mỗi file phải có **đủ 5 loại** theo `SPEC_preprocessing.md §10.3`:

| Loại | Nội dung tối thiểu |
|---|---|
| 1. Hợp đồng | trả về `StepResult`; `report.to_dict()` `json.dumps` được; **không sửa `df` gốc** (`assert_frame_equal(df, df_before)`); không đổi tên cột canonical |
| 2. Tìm lại | tập `record_id` bị gắn cờ **bằng đúng** `truth[...]` của injector tương ứng (P02: `country_variants` + `unit_mix`; P03: `duplicates`; P04: `outliers`; P06: `missing`; P01: `schema_errors`) |
| 3. Lựa chọn tham số | **mỗi giá trị cho phép** của tham số quan trọng có ít nhất một test. Ví dụ P04: `flag_only` giữ nguyên số dòng và giá trị · `drop_row` giảm đúng số dòng đã gắn cờ · `winsorize` giữ số dòng nhưng `max` giảm · `to_na` làm số ô trống tăng đúng bằng số ô bị cờ |
| 4. Phản ứng đúng chiều | tăng `robust_z_threshold` ⇒ số cờ **không tăng**; tăng `threshold_months` (P05) ⇒ tỷ lệ treated **không tăng**; tăng `max_missing_col` (P06) ⇒ số cột bị loại **không tăng** |
| 5. Không làm gì khi sạch | chạy module trên `make_clean_frame()`: `rows_dropped == 0`, mọi cờ `False`, không có finding mức `error` |

Thêm hai test dùng `pytest.mark.parametrize` qua cả 9 module:
- **idempotent**: chạy hai lần liên tiếp cho `data` bằng nhau;
- **tái lập**: hai lần chạy độc lập cùng seed cho `data` và `report` bằng nhau (bỏ qua `started_at`, `duration_s`).

### 2.3 Test pipeline còn thiếu

- `tests/pipeline/test_run_report.py`: mọi khóa ở `SPEC §8.4` có mặt, JSON hợp lệ.
- `tests/integration/test_preprocess_chain.py`: chạy hết chuỗi trên `make_dirty_frame(300, 0)`, kiểm tra `analysis_ready.parquet` tồn tại, `record_id` duy nhất, và **không cột nào bị chặn bởi P07 nằm trong `context_final.adjustment_set`**.
- **Golden run**: lưu `run_report.json` rút gọn (bỏ trường thời gian) vào `tests/fixtures/golden_run_report.json` và so sánh; khi lệch thì thông báo lỗi phải hướng dẫn cách cập nhật golden một cách có chủ ý.
- Giữ và làm chạy được `test_error_localization`: ép P04 hỏng (`--set p04.max_flag_rate=0.001`) ⇒ `run_report["failed_step"] == "P04"`, `status == "blocked"`, mã thoát 3, các bước sau **không** có trong `steps`.

### 2.4 Nghiệm thu giai đoạn 2

```bash
./.venv/bin/python -m pytest -q          # tất cả xanh
./.venv/bin/python -m pytest -q -m unit  # dưới 60 giây
```

---

## GIAI ĐOẠN 3 — Hiện thực các tham số đang bị bỏ trống

Những tham số sau **đang có trong config nhưng code không dùng**: người dùng chỉnh, không báo lỗi, mà hành vi không đổi. Đây là loại lỗi nguy hiểm nhất trong một pipeline khoa học.

| Module | Tham số | Phải làm |
|---|---|---|
| P03 | `resolve: aggregate`, `aggregate_rules` | Hiện thực gộp nhóm: số → `mean`, hạng mục → `mode` (hòa thì lấy giá trị nhỏ nhất theo thứ tự chuỗi), boolean → `max`. Dòng gộp phải giữ `record_id` của dòng đầy đủ nhất và được gắn cờ `flag__p03__aggregated`. Ghi rõ trong report: dòng này **không tồn tại thật trong dữ liệu gốc** |
| P04 | `winsorize_at` | `bound`: kéo về đúng ngưỡng phát hiện; `percentile`: kéo về `percentile_bounds`. `winsorize` phải chạy với **mọi** phương pháp phát hiện, không chỉ `domain_range` |
| P06 | `impute_group_by`, `min_group_size` | Điền trung vị **trong từng nhóm** (mặc định theo `country`); nhóm nhỏ hơn `min_group_size` dùng trung vị toàn cục và phát finding. Ghi giá trị đã dùng theo từng nhóm vào report (`value_used_by_group`) |
| P06 | `mechanism_check: regress` | Hồi quy logistic `c_outcome_observed ~ L + A` (chuẩn hóa biến số, one-hot hạng mục, `max_iter=1000`), báo cáo các hệ số lớn nhất theo trị tuyệt đối. **Chỉ mô tả**, tuyệt đối không kết luận MAR/MNAR |
| P06 | `missing_by_column`, `pattern_counts` | Đang được tính rỗng rồi bỏ đi. Điền đủ: tỷ lệ thiếu theo cột × nước × nhóm A, và 10 mẫu hình thiếu phổ biến nhất |
| P07 | `time_source`, `allow_post_as_secondary_outcome` | Hiện thực `name_suffix` (hậu tố `_post`) và `both`; `both` mà hai nguồn mâu thuẫn thì ưu tiên schema và phát `warning` |
| P08 | `exclude_roles` | Dùng chính danh sách trong config thay cho danh sách tên cột viết cứng. **Giữ** kiểm tra hậu điều kiện hiện có như lưới an toàn thứ hai, nhưng suy ra từ `dag_role` + `measured_at` chứ không từ tên cột |
| P08 | `basis`, `interactions` | Chỉ **khai báo** vào context để bước PS sau dùng (`ctx.ps_basis_spec`), không sinh cột. Ghi vào report |
| P02 | `category_levels_source` | `schema`: chỉ chấp nhận mức trong `allowed`; `data`: lấy mức từ dữ liệu và phát `warning` rằng kết quả sẽ đổi giữa các lần chạy |

### 3.1 Dọn nợ kỹ thuật kèm theo

1. **Kiểm tra phụ thuộc context đang là mã chết.** `hasattr(ctx, "adjustment_set")` luôn đúng vì `PipelineContext` khai sẵn trường. Thay bằng kiểm tra *đã được ghi hay chưa*: thêm vào `PipelineContext` một tập `_written: set[str]`, pipeline ghi tên khóa vào đó mỗi lần áp `context_updates`, và `steps.py` kiểm tra khóa nằm trong tập này. Chạy `run_step P06` một mình phải cho `DependencyError` với thông điệp *"P06 cần ctx.adjustment_set do P08 tạo; hãy chạy `--from P08` hoặc truyền `--context <file json>"*. Bỏ hết các khối `if ...: pass  # raise ...` trong `p06_missingness.py` và `p08_variable_roles.py`.
2. **`columns_added` phải `sorted()`** ở cả 9 module (hiện dựng từ `set(...)` nên thứ tự đổi giữa các lần chạy, phá golden run).
3. **Bỏ mẫu `findings[0].details = details`** (P04, P06): thống kê đang bị gắn nhờ vào finding đầu tiên và **mất hẳn** nếu module không phát finding nào. Đưa các thống kê này vào một `Finding` riêng mức `info` có mã `SUMMARY` của module đó.
4. **Bước hỏng phải có `StepReport` trong `run_report.json`**, với `status` = `blocked`/`failed`, mã lỗi và `details.traceback` (hiện chỉ có trường `failed_step`).
5. **`data_dictionary.csv`** phải được ghi ra `data/<output>/processed/<run_id>/data_dictionary.csv` (hiện chỉ có parquet trong `artifacts/`).
6. **`P08` với `source: manual` đang chết**: đã kiểm chứng — `UnboundLocalError: cannot access local variable 'variants'`, vì `variants = {}` chỉ được gán trong nhánh `schema_roles` (`p08_variable_roles.py:68`) nhưng lại được đọc ở dòng 132 và 160. Khởi tạo `variants = {}` ở đầu hàm.
7. **Mã thoát cho ngoại lệ ngoài dự kiến**: thống nhất theo `SPEC §9` (module hỏng = 2; 4 chỉ dành cho lỗi nội bộ của chính runner).
8. Thêm các finding còn thiếu so với thiết kế: `P04.SMALL_GROUP`, `P05.THRESHOLD_SENSITIVITY`.
9. `duration_s` làm tròn 3 chữ số ở mọi report.

---

## Quy tắc làm việc

1. **Không sửa `docs/SPEC_preprocessing.md`.** Nếu thấy spec sai hoặc thiếu, ghi vào `docs/OPEN_QUESTIONS.md` theo mẫu §12.2 và đánh dấu `# SPEC-GAP` trong code. Lần trước file đó ghi "Không có" trong khi nhiều chức năng bị bỏ qua — **đừng lặp lại**: mỗi chỗ bạn bỏ qua hoặc làm khác thiết kế đều phải nằm trong file này.
2. **Không thêm thư viện** ngoài `requirements.txt`.
3. **Không viết chức năng mới** ngoài ba giai đoạn trên. Không đụng `process/`, `estimate/`, `evaluate/`, `simulate/`.
4. Không `try/except: pass`. Không `print` trong thư viện. Không `inplace=True`.
5. Sau mỗi giai đoạn, **tự chạy** lệnh nghiệm thu của giai đoạn đó và dán kết quả thật vào báo cáo.

## Báo cáo khi bàn giao

1. Kết quả `./.venv/bin/python -m pytest -q` (số test, thời gian).
2. Kết quả hai lệnh chạy chuỗi ở §1.6 (mã thoát, số dòng vào/ra, trạng thái từng bước).
3. Một ví dụ `run_report.json` của lần chạy hỏng có chủ ý ở P04 (`--set p04.max_flag_rate=0.001`), chứng minh `failed_step == "P04"` và mã thoát 3.
4. Danh sách mục trong `docs/OPEN_QUESTIONS.md`.
5. Cập nhật `src/ra_causal/preprocess/README.md` §9: xóa những mục đã sửa, giữ lại những mục còn nợ. **Không xóa cả mục §9.**
