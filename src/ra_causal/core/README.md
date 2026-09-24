# `core` — Định nghĩa chung của cả pipeline

> Thư mục này **không xử lý dữ liệu**. Nó định nghĩa *khái niệm của các module*: mọi module phải trả về cái gì, lỗi được phân loại ra sao, trạng thái nào truyền giữa các bước, và báo cáo trông như thế nào.
>
> Sửa một thứ ở đây là sửa giao kèo của toàn bộ hệ thống — mọi module P01–P09 (và sau này K01–K10) đều phụ thuộc vào nó.

---

## 1. Mục đích của folder core

Không có tầng này thì mỗi module sẽ tự chọn cách trả kết quả, tự đặt tên lỗi, tự quyết định ghi báo cáo hay không. Hệ quả rất cụ thể: không viết được một lớp kiểm tra dùng chung, không định vị được module gây lỗi, và không so sánh được hai lần chạy với nhau.

Ba thứ `core` bảo đảm:

1. **Mọi module trông giống nhau từ bên ngoài** — cùng chữ ký, cùng kiểu trả về → `pipeline/` bọc được tất cả bằng một hàm duy nhất.
2. **Mọi lỗi đều biết mình thuộc module nào** — nhờ `module_id` và `code` gắn sẵn trong ngoại lệ.
3. **Mọi quyết định đều ghi ra JSON được** — nhờ `StepReport` + `jsonify`.

---

## 2. Các file

| File | Vai trò | Ai dùng |
|---|---|---|
| `contracts.py` | `Status`, `Finding`, `StepReport`, `StepResult`, hằng tên cột hệ thống | Tất cả |
| `context.py` | `PipelineContext`, `RunPaths` — trạng thái chảy dọc pipeline | Tất cả |
| `errors.py` | Cây ngoại lệ có `module_id` + `code` | Tất cả |
| `registry.py` | Sổ đăng ký module theo mã (`P01`…`P09`) | `pipeline/`, `cli/` |
| `schema.py` | Đọc và **validate** `canonical.yaml` thành `CanonicalSchema` | `pipeline/`, mọi module |
| `reporting.py` | Ghi `run_report.json` | `pipeline/runner.py` |
| `logging.py` | Logger có gắn `module_id` vào từng dòng | `pipeline/`, `cli/` |

---

## 3. `contracts.py` — bốn kiểu dữ liệu

### `Status`

| Giá trị | Nghĩa | Mã thoát |
|---|---|---|
| `ok` | chạy xong, không có gì đáng ngại | 0 |
| `warning` | chạy xong, có phát hiện mức cảnh báo | 0 |
| **`blocked`** | module **hoạt động đúng**, nhưng dữ liệu vi phạm ngưỡng người dùng đặt | 3 |
| **`failed`** | lỗi kỹ thuật: thiếu cột, sai config, vi phạm hợp đồng | 2 |

Phân biệt `blocked` và `failed` là có chủ ý: `blocked` nghĩa là *dữ liệu có vấn đề, hãy quay lại xem xét*; `failed` nghĩa là *code hoặc cấu hình có vấn đề*. Hai tình huống này cần phản ứng khác nhau, nên không được gộp.

### `Finding` — đơn vị phát hiện nhỏ nhất, tức là hàm ghi vấn đề của dữ liệu

```
code · severity · message · column · count · sample_ids · details
```

Quy ước sống còn: **`code` luôn có dạng `P0x.TÊN_VIẾT_HOA`** (ví dụ `P04.MAX_FLAG_RATE_EXCEEDED`). Nhờ đó test và người đọc báo cáo bám vào một mã cố định thay vì bám vào câu chữ tiếng Việt — đổi lời nhắn không làm hỏng test. `severity` ∈ `info | warning | error | blocking`.

Module **không bao giờ** `print`; mọi thứ muốn nói đều đi qua `Finding`.

    - code : lưu trữ mã lỗi
    - severity: mức độ nghiêm trọng
    - message: thông điệp báo cáo
    - count: số dòng bị ảnh hưởng
    - column: tên cột gây lỗi
    - sample_ids: danh sách các ID mẫu bị lỗi

### `StepReport` — Đóng gói toàn bộ báo cáo siêu dữ liệu (metadata) về quá trình thực thi của một module

Ghi lại: số dòng/cột vào ra, số dòng bị loại, số dòng bị gắn cờ, cột thêm/sửa, **toàn bộ tham số đã dùng** (`params_effective`), danh sách `Finding`, artifact, và các khóa context đã ghi.

`params_effective` là chi tiết quan trọng nhất: nó trả lời *"lần chạy này đã dùng ngưỡng nào"* mà không cần mở lại file config — file config có thể đã bị sửa sau đó.

`to_dict()` đi qua `jsonify` nên kết quả luôn ghi JSON được (không `numpy.int64`, không `Timestamp`, `NaN` → `null`).

### `StepResult` — thứ module trả về

| Trường | Nội dung |
|---|---|
| `data` | DataFrame sau xử lý |
| `report` | `StepReport` |
| `artifacts` | bảng phụ, không nằm trong luồng chính: `quarantine`, `review_list`, `data_dictionary` |
| `context_updates` | những khóa context mà module này ghi ra |

Tách `artifacts` khỏi `data` là để giữ luồng chính sạch: dòng bị cách ly hay danh sách cần rà soát không được lẫn vào dữ liệu phân tích, nhưng cũng không được biến mất.

### Tên cột hệ thống

`cluster_id`, `fold_id`, `c_outcome_observed`, `row_source`, `dup_group_id` — khai thành hằng ở đây để không module nào tự đặt lại tên khác.

---

## 4. `context.py` — trạng thái chảy dọc pipeline

`PipelineContext` mang hai loại thứ:

- **Bất biến cho cả lần chạy:** `run_id`, `schema`, `rng`, `paths`.
- **Trạng thái do module trước ghi ra:** `eligible_columns` (P07) → `adjustment_set` (P08) → dùng bởi P06; `treatment_definition` (P05); `cluster_column`/`fold_column` (P09); `ps_basis_spec` (P08, dành cho bước PS sau này).

### `_written` — vì sao cần một tập riêng

`PipelineContext` là dataclass nên **mọi trường đều tồn tại sẵn** với giá trị mặc định (`adjustment_set = []`). Do đó `hasattr(ctx, "adjustment_set")` **luôn đúng**, kể cả khi P08 chưa chạy. Nếu kiểm tra phụ thuộc bằng `hasattr`, P06 sẽ im lặng chạy với `L = []` thay vì báo lỗi — sai mà không ai biết.

Vì vậy pipeline ghi tên khóa vào `ctx._written` mỗi lần áp `context_updates`, và `pipeline/steps.py` kiểm tra *"khóa này đã thực sự được ghi chưa"*, chứ không phải *"trường này có tồn tại không"*.

Module **chỉ đọc** context và trả `context_updates`; chỉ `pipeline/steps.py` được ghi.

---

## 5. `errors.py` — hệ thống báo lỗi

```
RaCausalError                 (gốc — mang module_id, code, message, details)
├── ConfigError               config sai kiểu / giá trị không cho phép
├── SchemaError               dữ liệu không khớp schema (thiếu cột bắt buộc, ép kiểu hỏng)
├── ContractError             module vi phạm hợp đồng (mất dòng không khai báo, tạo khóa trùng)
├── DataQualityError          ngưỡng chất lượng bị vượt → BLOCKED, không phải FAILED
└── DependencyError           thiếu khóa context do module trước chưa chạy
```

Mọi ngoại lệ **bắt buộc** mang `module_id` và `code`. Đó là lý do khi P04 chặn, người dùng thấy ngay:

```
step : P04
code : P04.MAX_FLAG_RATE_EXCEEDED
```

Ngoại lệ **ngoài** cây này (ví dụ `TypeError` của pandas) được `pipeline/steps.py` bọc lại thành `ContractError` với mã `<MODULE_ID>.UNEXPECTED_EXCEPTION` kèm 50 dòng traceback cuối — không bao giờ để một lỗi lạ bay ra mà không biết của module nào.

---

## 6. `registry.py` — sổ đăng ký module

Module tự đăng ký bằng decorator:

```python
@REGISTRY.register("P04", P04Config)
def run(df, cfg, ctx) -> StepResult: ...
```

Registry lưu cặp *(hàm chạy, lớp config)*, nên `pipeline/` và `cli/` chỉ cần biết **mã module** là dựng được config đúng kiểu và gọi đúng hàm.

> **Bẫy đã từng làm chết cả pipeline:** decorator chỉ chạy khi file module được **import**. Nếu `runner.py` chỉ `from ra_causal.core.registry import REGISTRY` mà không import gói `ra_causal.preprocess`, registry sẽ rỗng và mọi lệnh chết với `KeyError: Module P01 not found`. Vì vậy `pipeline/runner.py` và `cli/run_step.py` đều có dòng `import ra_causal.preprocess  # noqa: F401` — **đừng xóa nó vì trông như import thừa**.

API: `register(module_id, config_class)` · `get_runner(id)` · `get_config_class(id)` · `available()` (danh sách mã đã đăng ký, dùng trong thông báo lỗi) · `"P04" in REGISTRY`.

---

## 7. `schema.py` — schema là nguồn sự thật, và nó tự kiểm tra

Hiểu đơn giản thì không chỉ kiểm soát chất lượng dữ liệu thuần túy (data quality) mà còn mã hóa các giả định về nhân quả (causal assumptions)

`CanonicalSchema.load(path)` đọc `configs/schema/canonical.yaml` thành các `ColumnContract` đã validate.

Một `ColumnContract` gồm: `dtype`, `required`, `measured_at`, `dag_role`, `unit`, `range`, `allowed`, `affected_by_treatment`.

**Luật kiểm tra chéo đáng chú ý** (`check_affected_by_treatment`):

- `measured_at: post` thì **bắt buộc** khai `affected_by_treatment`;
- `measured_at` khác `post` thì **không được** khai.

Lý do: P07 quyết định chặn hay cho phép một biến dựa đúng vào cặp thuộc tính này. `season_rain_mm` đo sau time zero nhưng không chịu ảnh hưởng can thiệp → được dùng làm biến tăng độ chính xác; `soil_om_post_pct` thì có → chặn tuyệt đối. Bỏ trống thuộc tính này là bỏ trống đúng thông tin quyết định, nên schema từ chối nạp ngay từ đầu thay vì để sai lan xuống dưới.

---

## 8. `reporting.py` — `run_report.json`

`write_run_report(...)` gom mọi `StepReport` thành một file, kèm: `run_id`, thời gian, `status`, **`failed_step`**, `config_digest` (sha256 12 ký tự đầu(thuật toán băm) của config đã merge), `schema_version`, thông tin input, `context_final`, đường dẫn đầu ra.

Hai chi tiết cố ý:

- **`config_digest`** cho phép nói chắc hai lần chạy có dùng cùng cấu hình hay không, mà không phải so từng dòng YAML.
- Hàm chấp nhận cả `StepReport` lẫn `dict` (`s.to_dict() if hasattr(...) else dict(s)`). Trước đây runner thêm một `dict` vào danh sách và bộ ghi gọi `.to_dict()` → **mọi lần chạy hỏng đều làm sập luôn việc ghi báo cáo**, tức là mất báo cáo đúng lúc cần nó nhất.

---

## 9. `logging.py`

`get_logger(module_id)` trả logger ghi ra **stderr** với định dạng `[thời gian] [mức] [module_id] thông điệp`, không nhân đôi handler khi gọi lại.

Chỉ `pipeline/` và `cli/` được log. Module xử lý dữ liệu **không log** — mọi thứ chúng muốn nói phải đi qua `Finding` để còn nằm lại trong báo cáo.

---

## 10. Quy tắc khi sửa `core`

1. **Thêm trường vào `StepReport`** → phải cập nhật `to_dict()`, `tests/pipeline/test_run_report.py` (bộ khóa bắt buộc) và toàn bộ 9 module.
2. **Thêm khóa context** → khai trong `PipelineContext`, và module ghi nó phải liệt kê trong `context_updates` để `steps.py` đưa vào `_written`.
3. **Thêm loại lỗi** → kế thừa `RaCausalError`, và quyết định rõ nó dẫn tới `blocked` hay `failed` (ảnh hưởng mã thoát).
4. **Không** đặt logic xử lý dữ liệu vào `core`. Ở đây chỉ có kiểu dữ liệu, kiểm tra hợp đồng và ghi báo cáo.

Liên quan: [`preprocess/README.md`](../preprocess/README.md) (chín module dùng các hợp đồng này) · [`pipeline/README.md`](../pipeline/README.md) (nơi hợp đồng được thi hành).
