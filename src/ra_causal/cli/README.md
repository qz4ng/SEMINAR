# `cli` — Hai lệnh chạy

> `run_pipeline` chạy cả chuỗi chín module. `run_step` chạy **đúng một** module trên một file bất kỳ — công cụ chính khi dò lỗi hoặc thử một lựa chọn tham số.

Cả hai dùng `argparse` và `logging` của thư viện chuẩn (spec cấm thêm `click`/`typer`/`rich`).

---

## 1. `run_pipeline` — chạy cả chuỗi

```bash
python -m ra_causal.cli.run_pipeline \
    --config configs/pipeline.yaml \
    --input  data/raw/dirty.csv \
    --output data/out
```

| Đối số | Bắt buộc | Ý nghĩa |
|---|---|---|
| `--config` | ✔ | đường dẫn `pipeline.yaml` |
| `--input` | ✔ | file dữ liệu vào (`.csv` hoặc `.parquet`) |
| `--output` | ✔ | thư mục gốc cho `interim/`, `processed/`, `reports/` |
| `--steps P01,P02` | | chỉ chạy các bước này |
| `--from P05` / `--to P04` | | chạy một đoạn của chuỗi |
| `--dry-run` | | validate config + schema, đọc 1000 dòng đầu, **không ghi file** |
| `--log-level` | | mặc định `INFO` |

`preprocess.yaml` **không** được truyền riêng: lệnh suy ra bằng cách thay `pipeline.yaml` → `preprocess.yaml` trong đường dẫn `--config`. Hệ quả: hai file phải nằm cùng thư mục, và schema phải ở `<thư mục đó>/schema/canonical.yaml`.

**Mã thoát** — thứ cần kiểm trong script hoặc CI:

| Mã | Nghĩa |
|---|---|
| 0 | chạy xong (có thể kèm cảnh báo) |
| 1 | lỗi đối số, lỗi config, hoặc không đọc được dữ liệu |
| 2 | một module `failed` (lỗi kỹ thuật) |
| 3 | một module `blocked` (dữ liệu vi phạm ngưỡng người dùng đặt) |

Phân biệt 2 và 3 là có chủ ý: **3 nghĩa là hãy xem lại dữ liệu**, **2 nghĩa là hãy xem lại code hoặc cấu hình**.

---

## 2. `run_step` — chạy một module

```bash
python -m ra_causal.cli.run_step P04 \
    --input  data/out/interim/<run_id>/after_P03.parquet \
    --config configs/preprocess.yaml \
    --output data/interim/manual/ \
    --set p04.action=winsorize \
    --set p04.max_flag_rate=0.2
```

| Đối số | Bắt buộc | Ý nghĩa |
|---|---|---|
| `step` (vị trí) | ✔ | mã module, không phân biệt hoa thường (`p04` cũng được) |
| `--input` | ✔ | file dữ liệu vào |
| `--config` | ✔ | `preprocess.yaml` |
| `--output` | ✔ | thư mục ghi `after_<MÃ>.parquet` |
| `--set khóa=giá_trị` | | ghi đè tham số, lặp lại được nhiều lần |
| `--context file.json` | | nạp sẵn trạng thái context cho module cần phụ thuộc |

### 2.1 `--set` hoạt động thế nào

Đường dẫn khóa được viết theo dạng đầy đủ (`p04.action=winsorize`); phần tiền tố `p04.` được cắt bỏ rồi giá trị được đặt vào cấu hình của bước. Kiểu được suy luận: `true/false` → bool, `null`/`None` → None, số → int/float, còn lại là chuỗi. Khóa lồng nhau dùng dấu chấm (`p02.string_normalize.lower=false`). Sau đó cấu hình đi qua pydantic, nên gõ sai tên hoặc sai giá trị sẽ bị chặn ngay với thông báo rõ ràng.

### 2.2 Khi module cần trạng thái của bước trước

Module giữa chuỗi không sống trong chân không: P06 cần `adjustment_set` do P08 tạo, P08 cần `eligible_columns` do P07 tạo. Chạy riêng mà thiếu thì lệnh dừng với thông báo cụ thể:

```
Step P06 failed: P06 cần ctx.adjustment_set do P08 tạo;
hãy chạy --from P08 hoặc truyền --context <file json>
```

Hai cách xử lý: dùng `run_pipeline --from P08`, hoặc truyền `--context ctx.json` chứa các khóa cần thiết, ví dụ:

```json
{"adjustment_set": ["country", "rain_longterm_mm", "field_size_ha"],
 "treatment_column": "cover_crop"}
```

### 2.3 Dùng để làm gì

- **Dò lỗi:** chạy lại đúng module hỏng trên file `interim/after_<bước trước>.parquet`, không phải chạy lại cả chuỗi.
- **Thử tham số:** so `--set p04.action=flag_only` với `--set p04.action=winsorize` trên cùng dữ liệu vào.
- **Kiểm tra độc lập:** đúng yêu cầu thiết kế "mỗi module phải chạy và test được một mình".

---

## 3. Điều cần biết

- `run_step` dựng một `PipelineContext` **tối thiểu** với `run_id = "manual"` và seed cố định `20260921`, ba đường dẫn `interim/processed/reports` đều trỏ vào `--output`. Nó **không** ghi `run_report.json` — chỉ ghi dữ liệu ra và in trạng thái.
- Cả hai lệnh đều có `import ra_causal.preprocess` để nạp registry. Xóa dòng đó thì registry rỗng và lệnh chết ngay ở module đầu tiên.
- Mã module không hợp lệ được báo tử tế kèm danh sách mã hợp lệ, chứ không để `KeyError` bay ra.
- Entry point ngắn đã khai trong `pyproject.toml` (`run_pipeline`, `run_step`), dùng được sau khi `pip install -e .`.

## 4. Hạn chế hiện tại

- `--log-level` được nhận nhưng chưa truyền xuống logger.
- `run_pipeline` suy ra đường dẫn `preprocess.yaml` bằng cách thay chuỗi trong tên file — đơn giản nhưng gãy nếu đặt tên file khác.
- `run_step` chưa cho phép ghi ra CSV (luôn ghi `.parquet`).
- Chưa có lệnh hiển thị/kiểm tra config (kiểu `show-config`), hiện phải đọc thẳng `configs/preprocess.yaml`.

Liên quan: [`pipeline/README.md`](../pipeline/README.md) · [`preprocess/README.md`](../preprocess/README.md).
