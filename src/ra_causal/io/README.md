# `io` — Đọc, ghi, và lớp adapter cho dữ liệu thô

> Tầng mỏng ngăn cách **định dạng file** và **định dạng dữ liệu thật của đối tác** khỏi phần còn lại của hệ thống. Nhờ nó, khi CIAT gửi dữ liệu với tên cột khác, ta viết thêm một adapter chứ không sửa module nào.

---

## 1. Các file

| File | Vai trò |
|---|---|
| `loaders.py` | `load_data(path, adapter_name, schema_version)` — đọc file rồi đưa qua adapter |
| `writers.py` | `write_data(df, path)` — ghi CSV hoặc Parquet, tự tạo thư mục |
| `adapters/__init__.py` | Sổ đăng ký adapter (`ADAPTERS`) |
| `adapters/raw_assumed.py` | Adapter cho **định dạng thô giả định** |
| `adapters/ciat.py` | **Stub** cho dữ liệu CIAT thật — cố tình `NotImplementedError` |

---

## 2. Adapter là gì và vì sao tách riêng

Adapter chỉ làm **một việc**: đưa dữ liệu về đúng **tên cột canonical**. Nó không làm sạch, không ánh xạ giá trị, không quy đổi đơn vị — những việc đó là của P01/P02.

| Adapter | Làm gì | Khi nào dùng |
|---|---|---|
| `canonical` | Không làm gì | Dữ liệu đã đúng tên cột (dữ liệu test, hoặc file `interim` của lần chạy trước) |
| `raw_assumed` | Đổi tên cột theo `column_aliases` trong `configs/schema/raw_assumed.yaml` | Bản xuất khảo sát theo định dạng giả định |
| `ciat` | Chưa hiện thực | Dành cho dữ liệu thật, sau data audit |

Ranh giới này quan trọng: nếu adapter bắt đầu "sửa giá trị cho tiện", ta sẽ có hai chỗ cùng làm việc của P02 và không ai biết chỗ nào đã đổi gì. Adapter chỉ được đụng vào **tên cột**.

Chọn adapter trong `configs/pipeline.yaml`:

```yaml
input:
  adapter: canonical   # canonical | raw_assumed | ciat
```

---

## 3. `loaders.py`

`load_data` đọc theo đuôi file (`.csv` → `read_csv`, `.parquet` → `read_parquet`), đuôi khác thì báo lỗi rõ ràng; file không tồn tại thì `FileNotFoundError` ngay thay vì để lỗi mơ hồ ở bước sau. Sau khi đọc, dữ liệu đi qua adapter được chỉ định.

> **Lưu ý về Parquet:** dữ liệu **thô** thường không ghi được ra Parquet — một cột số lẫn chuỗi `"abc"` sẽ làm Arrow báo `ArrowInvalid`. Đó là lý do luồng thật đọc **CSV** ở đầu vào, và Parquet chỉ dùng cho dữ liệu **đã qua P01** (các file `interim/after_P0x.parquet`). Test cũng phải theo quy tắc này.

---

## 4. `writers.py`

`write_data` tự tạo thư mục cha rồi ghi theo đuôi file, luôn `index=False` (chỉ số dòng của pandas không phải dữ liệu, ghi ra sẽ thành một cột rác).

Nơi các file được ghi (do `pipeline/runner.py` quyết định):

```
data/<output>/interim/<run_id>/after_P0x.parquet      ảnh chụp sau mỗi bước
data/<output>/processed/<run_id>/analysis_ready.parquet
data/<output>/processed/<run_id>/data_dictionary.csv  (CSV để mở bằng Excel)
data/<output>/processed/<run_id>/artifacts/*.parquet  quarantine, review_list
data/<output>/reports/<run_id>/run_report.json
```

---

## 5. Viết adapter cho dữ liệu CIAT thật

Khi có bản xuất thật, làm theo thứ tự này:

1. **Data audit trước, code sau.** Ghi lại: tên cột thật, đơn vị của yield, cách mã hóa practice, khóa xác định một dòng (một năm có nhiều vụ không?).
2. Điền `column_aliases` và `unit_declarations` trong `configs/schema/raw_assumed.yaml`, hoặc tạo file khai báo riêng cho CIAT.
3. Hiện thực `adapters/ciat.py` theo đúng chữ ký `adapt(df, schema_version) -> pd.DataFrame`, **chỉ đổi tên cột** và bỏ cột thừa.
4. Đăng ký vào `ADAPTERS` (đã có sẵn khóa `"ciat"`).
5. Mọi khác biệt về **giá trị** (tên nước viết khác, `"Yes/No"`, kg/ha) thì bổ sung alias cho P02, **không** xử lý trong adapter.

Cái cần giữ: sau adapter, dữ liệu phải sẵn sàng cho P01 kiểm tra schema — nghĩa là đúng tên cột, còn nguyên mọi sự bẩn thỉu khác.

---

## 6. Hạn chế hiện tại

- `adapters/ciat.py` là stub, gọi vào sẽ `NotImplementedError`.
- `column_aliases` trong `raw_assumed.yaml` đang rỗng (chưa có định dạng thật để ánh xạ).
- `load_data` nhận `schema_version` và truyền cho adapter nhưng chưa adapter nào dùng tới — chỗ dành sẵn cho việc xử lý nhiều phiên bản schema sau này.
- Chưa hỗ trợ Excel (`.xlsx`); nếu bản xuất của CIAT là Excel thì thêm nhánh đọc ở `loaders.py`.

Liên quan: [`core/README.md`](../core/README.md) (schema mà adapter phải bám theo) · [`preprocess/README.md`](../preprocess/README.md) §2.4.
