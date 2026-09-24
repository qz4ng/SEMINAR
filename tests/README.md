# `tests` — Bộ test và khung dữ liệu giả

> 116 test, chạy dưới 25 giây. Mục tiêu không phải "code chạy không lỗi" mà là **canh giữ những tính chất dễ vỡ**: module có làm đúng việc của nó không, có làm hỏng dữ liệu không, và khi hỏng thì có chỉ đúng chỗ không.

```bash
./.venv/bin/python -m pytest -q                 # tất cả
./.venv/bin/python -m pytest -q -m unit         # 62 test nhanh, ~12 giây
./.venv/bin/python -m pytest -q -m integration  # chạy chuỗi và CLI
./.venv/bin/python -m pytest -q tests/preprocess/test_p04_outliers.py   # một module
```

---

## 1. Ý tưởng nền: dữ liệu test **biết trước đáp án**

Không dùng dữ liệu thật, cũng chưa dùng bộ mô phỏng nhân quả (thư mục `simulate/` còn trống). Thay vào đó `fixtures/make_frames.py` sinh dữ liệu đúng schema rồi **cài lỗi có chủ ý**, và trả về danh sách `record_id` đã bị làm hỏng. Nhờ đó câu hỏi *"module có tìm lại đúng cái đã cài không"* trở thành một phép so hai tập hợp, không phải một phán đoán.

| Hàm | Trả về | Cài gì |
|---|---|---|
| `make_clean_frame(n, seed)` | DataFrame sạch | Không lỗi; khóa nghiệp vụ `grower_id+field_id+year` **duy nhất** |
| `inject_country_variants` | `(df, ids)` | `"Country 1"`, `" c1 "`, `"C-1"` |
| `inject_unit_mix` | `(df, ids)` | yield ×1000 (kg/ha); `declare_unit=True` thêm cột `yield_unit` |
| `inject_duplicates` | `(df, ids)` | trùng hệt, trùng một phần, và **mâu thuẫn** (khác `cover_crop`) |
| `inject_outliers` | `(df, ids)` | yield ×10 |
| `inject_missing` | `(df, ids)` | NaN theo tỷ lệ từng cột |
| `inject_schema_errors` | `(df, ids)` | chuỗi trong cột số, giá trị ngoài miền, `record_id` rỗng, hạng mục lạ ở `contract` |
| `inject_treatment_versions` | `(df, ids)` | `cover_crop_months`, `cover_crop_type` |
| `make_dirty_frame(n, seed)` | `(df, truth)` | Gộp tất cả; `truth` là dict `{tên lỗi: [record_id]}` |

Hai chi tiết của khung dữ liệu đã từng là bẫy:

- **Khung "sạch" phải thật sự sạch.** Bản đầu sinh ra 3 khóa nghiệp vụ trùng nhau, khiến P03 báo trùng ngay trên dữ liệu sạch và test *"module không làm gì khi dữ liệu sạch"* mất ý nghĩa.
- **Hạng mục lạ đặt ở `contract`, không đặt ở `country`.** `country` có chính sách `unmapped_action: raise` nên rác ở đó làm cả chuỗi dừng — đúng thiết kế, nhưng khung dữ liệu dùng chung thì không chạy hết được. Chính sách `raise` đó được kiểm tra riêng trong `test_p02_harmonize.py`.

---

## 2. Bố cục

| Thư mục | Nội dung | Số test |
|---|---|---|
| `conftest.py` | fixture dùng chung: `schema`, `default_config`, `make_ctx`, **`prepare_upto`**; hằng `PIPELINE_ORDER` | — |
| `fixtures/` | `make_frames.py` (khung dữ liệu + injector), `golden_run_report.json` | — |
| `core/` | hợp đồng, lỗi, registry, schema | 6 |
| `preprocess/` | 9 file × 5 loại test + `test_all_modules_invariants.py` (parametrize × 9 module) | 95 |
| `pipeline/` | thứ tự bước, định vị lỗi, cổng mất dòng, `run_report.json` | 8 |
| `integration/` | chạy cả chuỗi, dữ liệu `Yes/No/Partial`, CLI | 7 |

### `prepare_upto` — fixture quan trọng nhất

```python
df, ctx = prepare_upto(raw, "P04")     # chạy P01→P03 rồi trả dữ liệu cho P04
```

Module **không sống trong chân không**: P04 giả định P02 đã quy đổi đơn vị, P06 giả định P08 đã dựng **L**. Bản test đầu tiên nạp thẳng dữ liệu thô vào module giữa chuỗi và 7 test fail vì những lỗi *không tồn tại trong luồng thật* (P04 chặn do 20% dòng còn ghi kg/ha). `prepare_upto` chạy đúng các bước đứng trước, đúng như pipeline làm.

---

## 3. Năm loại test cho mỗi module

Mỗi file `test_p0x_*.py` phải có đủ năm loại (theo `docs/SPEC_preprocessing.md` §10.3):

| Loại | Câu hỏi | Ví dụ thật |
|---|---|---|
| **1. Hợp đồng** | Vào/ra có đúng cam kết không? | không sửa `df` gốc; `report.to_dict()` `json.dumps` được |
| **2. Tìm lại** | Có phát hiện đúng cái đã cài không? | P04: tập gắn cờ ⊇ `truth["outliers"]`, và mọi cờ thừa phải giải thích được |
| **3. Lựa chọn tham số** | Mỗi giá trị có làm đúng điều nó hứa? | P04: `flag_only` giữ nguyên số dòng · `drop_row` giảm đúng số dòng đã gắn cờ · `to_na` làm tăng đúng số ô trống |
| **4. Phản ứng đúng chiều** | Vặn knob thì đổi đúng hướng? | tăng `robust_z_threshold` ⇒ số cờ **không tăng**; tăng `threshold_months` ⇒ tỷ lệ treated **không tăng** |
| **5. Không làm gì khi sạch** | Dữ liệu sạch có bị đụng vào không? | `rows_dropped == 0`, mọi cờ `False`, không finding mức `error` |

Cộng thêm `test_all_modules_invariants.py` chạy `parametrize` qua **cả chín module**:

- **không sửa dữ liệu vào** (`assert_frame_equal(df, df_before)`);
- **chạy lại không đổi** (idempotent) — đã bắt được bốn lỗi thật: P02 chia 1000 hai lần, P05 ghi đè bản gốc, P09 đổi cách chia fold, P03 đánh số lại nhóm trùng;
- **tái lập** — cùng seed cho cùng dữ liệu ra và cùng báo cáo (bỏ qua `started_at`, `duration_s`);
- **báo cáo ghi JSON được và `columns_added` đã sắp xếp**.

---

## 4. Test mức pipeline và integration

| Test | Canh giữ điều gì |
|---|---|
| `test_runner_ordering` | chạy đúng thứ tự `P01→P02→P03→P04→P05→P07→P08→P06→P09` |
| `test_error_localization` | ép P04 chặn (`max_flag_rate=0.001`) ⇒ mã thoát **3**, `failed_step == "P04"`, bước hỏng **có** báo cáo riêng, P05 trở đi **không** chạy |
| `test_row_loss_gate` | một bước mất > 20% dòng ⇒ `EXCESSIVE_ROW_LOSS`, kèm nguyên nhân và artifact; ngưỡng tắt được |
| `test_text_coded_practices` | dữ liệu `Yes/No/Partial` + `Có/Không` đi hết chuỗi với đủ 120 dòng, dòng Partial được gắn cờ |
| `test_run_report` | đủ bộ khóa bắt buộc; số dòng nối tiếp giữa các bước; mọi `finding.code` bắt đầu bằng mã module của nó |
| `test_preprocess_chain` | L **không bao giờ** chứa biến đo sau can thiệp; một nông hộ không nằm ở hai fold; dữ liệu sạch qua cả chuỗi không mất dòng, không cờ nào bật |
| `test_cli` | lệnh CLI khởi động được |

Hai test dùng **chính** `configs/preprocess.yaml` và `configs/schema/canonical.yaml` (chỉ copy vào `tmp_path` rồi siết một tham số), thay vì viết schema rút gọn trong test. Bản trước dùng schema mock 5 cột và test xanh trong khi pipeline thật hỏng — mock che mất đúng thứ cần kiểm.

---

## 5. Quy ước khi viết thêm test

1. **Dữ liệu vào phải qua `prepare_upto`** nếu module không phải P01.
2. **Không dùng `assert res is not None`.** Một test không thể fail là một test không tồn tại — bản đầu có 3 test kiểu này ở mỗi file và chúng che mất lỗi P02 suốt hai vòng.
3. **Bám vào `finding.code`**, đừng bám vào câu chữ thông điệp (thông điệp bằng tiếng Việt và sẽ đổi).
4. **Ghi CSV, đừng ghi parquet** khi cần đưa dữ liệu bẩn ra file: cột lẫn kiểu sẽ làm Arrow báo lỗi.
5. Module mới chỉ cần thêm mã vào `PIPELINE_ORDER` trong `conftest.py` là **tự động** được đưa vào bộ test bất biến chung.
6. Đánh dấu `@pytest.mark.unit` hoặc `@pytest.mark.integration` để `-m unit` giữ được tốc độ.

---

## 6. Hạn chế hiện tại

- **Golden run chưa được so tự động.** `fixtures/golden_run_report.json` đã có nhưng chưa có test đối chiếu `run_report` rút gọn với nó — đây là lưới an toàn chống hồi quy còn thiếu.
- **Chưa có test cho `io/`** (đọc file hỏng, adapter không tồn tại, đuôi file lạ).
- **Chưa đo độ phủ** (`pytest-cov` đã cài nhưng chưa đặt ngưỡng).
- Test mức "đánh giá phương pháp" (bias, RMSE, độ phủ qua nhiều lần lặp) chưa tồn tại vì cần bộ mô phỏng `simulate/` — đó là cấp 3 trong thiết kế.

Liên quan: [`docs/SPEC_preprocessing.md`](../docs/SPEC_preprocessing.md) §10 · [`src/ra_causal/preprocess/README.md`](../src/ra_causal/preprocess/README.md) §9.
