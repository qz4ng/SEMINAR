# `utils` — Hai hàm dùng chung

> Chỉ chứa thứ **nhiều module cùng cần** và **không thuộc về riêng module nào**. Không phải nơi đổ những hàm chưa biết để đâu.

---

## `pandas_tools.to_schema_dtype(series, dtype)`

Ép một cột về kiểu khai trong schema, luôn dùng **kiểu nullable của pandas**:

| `dtype` trong schema | Kiểu pandas |
|---|---|
| `int8` / `int16` | `Int8` / `Int16` |
| `float32` | `Float32` |
| `boolean` | `boolean` |
| `string` | `string` |
| `category` | `category` |

**Vì sao bắt buộc dùng kiểu nullable.** Kiểu numpy `int16`/`bool` không chứa được ô trống. Bản đầu tiên của P01 ép bằng kiểu numpy và chết ngay trên dữ liệu bẩn:

```
Cannot convert non-finite values (NA or inf) to integer
```

Nghịch lý: module dọn dữ liệu bẩn lại không chịu nổi dữ liệu bẩn. Từ đó mọi chỗ ép kiểu đều đi qua hàm này, không ai gọi `.astype("int16")` trực tiếp.

## `pandas_tools.jsonify(obj)`

Đổi đệ quy một object bất kỳ thành dạng ghi JSON được: `numpy.integer/floating` → `int/float`, `NaN` → `None`, `ndarray`/`Categorical`/`tuple`/`set` → list (set được `sorted` để kết quả xác định), `Timestamp` → chuỗi ISO, object có `to_dict()` → gọi rồi đệ quy tiếp, còn lại → `str(obj)`.

**Vì sao cần.** `StepReport` chứa số liệu tính từ pandas, mà `json.dumps` không nuốt được `numpy.int64` hay `NaN`. Không có lớp này thì báo cáo sẽ hỏng ngẫu nhiên tùy dữ liệu — kiểu lỗi chỉ lộ ra khi chạy trên dữ liệu thật. `StepReport.to_dict()` và `write_run_report` đều đi qua đây.

Lưu ý: nhánh cuối `str(obj)` là mạng che an toàn — nó khiến báo cáo **không bao giờ hỏng**, nhưng cũng có thể biến một object bị quên thành chuỗi khó đọc. Thấy chuỗi lạ trong `run_report.json` thì kiểm tra xem module có nhét object Python vào `details` không.

---

## Quy tắc thêm hàm vào đây

Chỉ thêm khi **từ hai module trở lên** cùng cần, và hàm đó không mang logic nghiệp vụ của riêng một module. Ngưỡng outlier là của P04, quy tắc ánh xạ đơn vị là của P02 — những thứ đó ở lại module của chúng.

Liên quan: [`core/README.md`](../core/README.md).
