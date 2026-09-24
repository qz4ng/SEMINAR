# `pipeline` — Nối các module và canh giữ hợp đồng

> Chạy chín module theo đúng thứ tự, kiểm tra hợp đồng **trước và sau** mỗi bước, và khi có bước hỏng thì trả lời dứt khoát: **hỏng ở module nào, mã lỗi gì, những bước nào đã chạy**.

---

## 1. Các file

| File | Vai trò |
|---|---|
| `steps.py` | Bọc **một** module: tiền kiểm tra phụ thuộc → gọi module → hậu kiểm tra → ghi context |
| `runner.py` | Chạy **cả chuỗi**: nạp config và schema, dựng context, vòng lặp bước, bắt lỗi, ghi báo cáo |
| `gates.py` | **Còn trống** — cổng kiểm tra positivity/balance là việc của K03/K05 (tháng sau) |

Việc ghi `run_report.json` nằm ở [`core/reporting.py`](../core/README.md#8-reportingpy--run_reportjson), không nằm ở đây.

---

## 2. `steps.py` — lớp áo chung quanh mỗi module

`run_step(module_id, runner, cfg, df, ctx)` làm bốn việc, luôn theo thứ tự này:

### 2.1 Tiền kiểm tra phụ thuộc

```
P06 cần ctx.adjustment_set  (do P08 tạo)
P08 cần ctx.eligible_columns (do P07 tạo)
```

Kiểm tra dựa trên `ctx._written`, **không** dùng `hasattr` — vì `PipelineContext` là dataclass nên mọi trường đều tồn tại sẵn với giá trị rỗng, `hasattr` luôn đúng và sẽ để P06 lặng lẽ chạy với `L = []`. Thiếu phụ thuộc thì `DependencyError` kèm hướng dẫn cụ thể:

> *P06 cần ctx.adjustment_set do P08 tạo; hãy chạy `--from P08` hoặc truyền `--context <file json>`*

### 2.2 Gọi module và bọc ngoại lệ lạ

Ngoại lệ thuộc cây `RaCausalError` được cho đi qua nguyên vẹn (chúng đã mang `module_id` + `code`). Mọi ngoại lệ **khác** (`TypeError` của pandas, `ValueError` của scikit-learn…) bị bọc thành `ContractError` mã `<MODULE_ID>.UNEXPECTED_EXCEPTION`, kèm 50 dòng traceback cuối trong `details`. Không bao giờ có lỗi lạ bay ra mà không biết của module nào.

### 2.3 Hậu kiểm tra hợp đồng

| Kiểm tra | Ý nghĩa |
|---|---|
| **Không mất dòng im lặng** | `len(out) < len(df)` mà `report.rows_dropped == 0` → `ContractError` mã `LOST_ROWS`. Module được phép loại dòng, nhưng phải khai báo |
| **Không tự tạo khóa trùng** | Chỉ báo lỗi khi **đầu vào duy nhất mà đầu ra không còn duy nhất**. Dữ liệu thô vốn có thể trùng (đó là việc của P03), và sau P03 với `conflict_action: review_list` thì **vẫn còn trùng có chủ ý** ở các nhóm mâu thuẫn — nên không thể đòi mọi bước trả về khóa duy nhất |

### 2.4 Cổng an toàn: không bước nào được lặng lẽ làm mất phần lớn dữ liệu

Nếu một bước làm mất quá `max_row_loss_per_step` (mặc định **20%**, khai ở `defaults` trong `preprocess.yaml`; `null` để tắt) số dòng — hoặc làm bảng rỗng — pipeline dừng **ngay tại bước đó** với `DataQualityError` mã `<MÃ>.EXCESSIVE_ROW_LOSS` (trạng thái `blocked`, mã thoát 3). Thông báo kèm nguyên nhân chính lấy từ findings của bước:

```
code    : P01.EXCESSIVE_ROW_LOSS
message : P01 loại 40/80 dòng (50%), vượt ngưỡng 20%. Nguyên nhân chính: P01.COERCE_FAILED (temp_longterm_c): 40
```

Artifact của bước bị chặn (vd `quarantine.parquet`) vẫn được ghi, và findings gốc của module được gộp vào báo cáo, để xem vì sao mất dòng.

Cổng này có vì một lỗi thật: P01 cách ly 120/120 dòng dữ liệu `Yes/No`, rồi P02–P07 vẫn báo `ok` trên bảng rỗng và pipeline chỉ chết ở P08 với thông báo `boolean value of NA is ambiguous` — không liên quan gì tới nguyên nhân.

### 2.5 Ghi context

Mỗi khóa trong `res.context_updates` được `setattr` vào `ctx`, thêm vào `ctx._written`, và ghi tên vào `report.context_updates`. Đây là chỗ duy nhất được ghi context — module chỉ *đề xuất*, `steps.py` mới *áp dụng*.

---

## 3. `runner.py` — chạy cả chuỗi

### 3.1 Trình tự

1. Nạp `pipeline.yaml` + `preprocess.yaml`; sinh `run_id` = `YYYYmmdd-HHMMSS-<8 hex>`.
2. Chọn danh sách bước: `steps` trong config, cắt theo `--steps` / `--from` / `--to`.
3. Nạp schema từ `<thư mục config>/schema/canonical.yaml`.
4. Dựng `RunPaths` (`interim`, `processed`, `reports` — mỗi lần chạy một thư mục riêng theo `run_id`) và `PipelineContext` với `rng` từ `defaults.seed`.
5. Đọc dữ liệu qua adapter; `--dry-run` chỉ lấy 1000 dòng đầu và không ghi gì.
6. Vòng lặp bước: dựng config pydantic của bước → `run_step` → ghi `interim/after_P0x.parquet` và artifact.
7. Ghi `analysis_ready.parquet` (khi mã thoát 0) và `run_report.json`.

Thứ tự bước **không đổi**: `P01 → P02 → P03 → P04 → P05 → P07 → P08 → P06 → P09`. Lý do từng cặp nằm ở [`preprocess/README.md` §5.1](../preprocess/README.md#51-vì-sao-đúng-thứ-tự-này).

### 3.2 Bắt lỗi và mã thoát

| Tình huống | `status` | Mã thoát | Ghi vào báo cáo |
|---|---|---|---|
| Chạy xong | `ok` / `warning` | 0 | báo cáo đầy đủ của mọi bước |
| `DataQualityError` (ngưỡng người dùng bị vượt) | `blocked` | **3** | bước hỏng có `StepReport` riêng, `findings[0].code` là mã chặn |
| `RaCausalError` khác | `failed` | **2** | như trên |
| Ngoại lệ ngoài dự kiến | `failed` | **2** | như trên, `details.traceback` giữ 50 dòng cuối |
| Lỗi config / không đọc được dữ liệu | — | **1** | không có báo cáo (chưa chạy bước nào) |

Khi dừng, runner in ra stderr đúng một khối:

```
PIPELINE FAILED
  step        : P04
  code        : P04.MAX_FLAG_RATE_EXCEEDED
  message     : Flag rate 7.0% exceeds 5.0%. Check unit conversions.
  rows in/out : 301 / -
  report      : data/out/reports/<run_id>/run_report.json
```

**Bước hỏng vẫn có `StepReport` trong `run_report.json`** — cùng cấu trúc như mọi bước khác, chỉ khác `status` và có `findings` mô tả lỗi. Đây là bài học từ một lỗi thật: bản trước đó thêm một `dict` thô vào danh sách báo cáo, khiến bộ ghi gọi `.to_dict()` và **sập ngay khi có bước hỏng** — mất báo cáo đúng lúc cần nhất.

`fail_fast: true` (mặc định) dừng ngay khi có bước hỏng; đặt `false` để chạy tiếp và gom hết lỗi trong một lần.

### 3.3 Hai dòng import trông thừa nhưng không được xóa

```python
import ra_causal.preprocess  # noqa: F401 — nạp registry
```

Module chỉ đăng ký vào registry khi file của nó được import. Thiếu dòng này, registry rỗng và mọi lệnh chết với `KeyError: Module P01 not found in registry`.

---

## 4. Chạy lại một phần

```bash
--steps P01,P02,P03     # chỉ ba bước này
--from P05              # từ P05 tới hết
--to P04                # từ đầu tới P04
--dry-run               # validate + đọc 1000 dòng, không ghi file
```

Muốn chạy đúng **một** module trên một file bất kỳ thì dùng `cli/run_step.py` (xem [`cli/README.md`](../cli/README.md)).

`save_interim: true` trong `pipeline.yaml` giữ ảnh chụp sau từng bước — đó là cách rẻ nhất để chạy lại từ giữa chuỗi khi dò lỗi.

---

## 5. Hạn chế hiện tại

- **`gates.py` còn trống.** Cổng kiểm tra (positivity ở K03, balance ở K05, độ lệch giữa IPW và standardization ở K08) thuộc khối `process/` chưa làm. Vòng lặp quay lại và giới hạn số vòng cũng chưa có.
- **Hậu kiểm tra chưa đầy đủ:** chưa kiểm tra "không mất cột canonical" và chưa đối chiếu `columns_added` trong báo cáo với cột thực sự xuất hiện.
- **Đường dẫn schema suy ra từ vị trí file config** (`<dir>/schema/canonical.yaml`). Đổi bố cục thư mục config thì phải sửa chỗ này.
- **Phụ thuộc giữa các bước đang viết cứng** trong `steps.py` (P06 cần gì, P08 cần gì). Khi thêm module thứ mười, nên chuyển sang khai báo `requires`/`provides` ngay trong registry.

Liên quan: [`core/README.md`](../core/README.md) · [`cli/README.md`](../cli/README.md) · [`preprocess/README.md`](../preprocess/README.md).
