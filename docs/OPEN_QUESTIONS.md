# Câu hỏi mở và chỗ hiện thực khác thiết kế

Ghi lại mọi chỗ code làm khác `SPEC_preprocessing.md`, hoặc chỗ spec chưa nói rõ mà phải tự quyết.
Mỗi mục cần người (nhóm hoặc GVHD) xác nhận hoặc bác bỏ.

---

### Q-01 · P01 · Hạng mục lạ và số ngoài miền không còn bị cách ly theo dòng

- **Spec nói gì:** §6.1 bước 7 — "dòng lỗi ở bước 3–6 xử lý theo `on_error`", mặc định `quarantine`; mặc định `out_of_range: to_na`.
- **Đã làm khác:** hai loại lỗi này chỉ **đánh dấu ô** (`flag__p01__not_allowed__<cột>`, `flag__p01__out_of_range__<cột>`), không đưa dòng vào diện cách ly. Mặc định `out_of_range` đổi từ `to_na` sang `flag`.
- **Vì sao:** làm đúng spec thì P01 xóa mất chính những dòng mà P02/P04 sinh ra để sửa. Đo được trên khung dữ liệu test: 10% dòng có tên nước viết biến thể và 15–20% dòng ghi kg/ha bị cách ly hoặc bị xóa giá trị **trước khi** P02 kịp ánh xạ/quy đổi. Mâu thuẫn trực tiếp với §10.3 của spec ("P02 phải chạy trước P04 vì phải quy về cùng đơn vị rồi mới nói được thế nào là bất thường").
- **Ảnh hưởng nếu chọn khác:** muốn quay lại hành vi cũ thì đặt `p01.out_of_range: to_na` trong config; còn việc cách ly theo hạng mục lạ thì phải sửa code.
- **Vị trí:** `src/ra_causal/preprocess/p01_schema_check.py` (khối "Categorical allowed" và "Range").

### Q-02 · P03 · `dup_group_id` suy từ hàm băm của khóa, không đánh số tuần tự

- **Spec nói gì:** §6.3 bước 5 — mã nhóm dạng `"g%06d"` theo thứ tự nhóm đã sắp xếp.
- **Đã làm khác:** `"g" + sha1(khóa)[:6]`.
- **Vì sao:** đánh số theo thứ tự gặp làm mã nhóm đổi hết khi chạy lại trên dữ liệu đã gộp (vài nhóm biến mất), phá yêu cầu "chạy lại không đổi" ở §10.3 loại test idempotent.
- **Ảnh hưởng:** mã nhóm không còn đọc được theo thứ tự, nhưng ổn định và đối chiếu được giữa các lần chạy.
- **Vị trí:** `p03_deduplicate.py`, vòng lặp nhóm.

### Q-03 · P07 · Cột không có trong schema bị coi là "không rõ thời điểm đo"

- **Spec nói gì:** §6.6 chỉ nói về cột có khai trong schema.
- **Đã làm khác:** cột xuất hiện trong dữ liệu nhưng không khai trong `canonical.yaml` được xử lý theo `unknown_action` (mặc định `exclude` → vào `blocked_columns`), kèm cảnh báo.
- **Vì sao:** code cũ bỏ qua im lặng, nghĩa là một biến đo sau can thiệp lọt vào dữ liệu mà không khai schema sẽ không bị chặn. Đây đúng là loại lỗi mà P07 sinh ra để chặn.
- **Vị trí:** `p07_time_order.py`, đầu vòng lặp cột.

### Q-04 · P09 · Seed chia fold lấy từ `cfg.seed`, không rút từ `ctx.rng`

- **Spec nói gì:** §4.7 — mọi ngẫu nhiên đi qua `ctx.rng`.
- **Đã làm khác:** `np.random.default_rng(cfg.seed)` dùng riêng cho việc chia fold.
- **Vì sao:** `ctx.rng` tiến trạng thái sau mỗi lần gọi, nên gọi P09 lần hai cho cách chia fold khác — vi phạm idempotent. Fold phải ổn định theo cấu hình chứ không theo lịch sử gọi hàm.
- **Vị trí:** `p09_clusters.py`, khối chia fold.

### Q-05 · steps.py · Tính duy nhất của `record_id` chỉ kiểm tra theo chiều "module tự tạo trùng"

- **Spec nói gì:** §8.2 bước 4 — "`record_id` vẫn duy nhất" sau mỗi bước.
- **Đã làm khác:** chỉ báo lỗi khi đầu vào duy nhất mà đầu ra không còn duy nhất.
- **Vì sao:** dữ liệu thô vốn có dòng trùng (đó là lý do P03 tồn tại), nên không thể đòi P01/P02 trả về khóa duy nhất. Ngoài ra với `conflict_action: review_list` (mặc định) thì **sau P03 vẫn còn trùng** có chủ ý ở các nhóm mâu thuẫn.
- **Vị trí:** `pipeline/steps.py`, phần hậu kiểm tra.

### Q-06 · Khung dữ liệu test: hạng mục lạ chuyển sang cột `contract`

- **Chỗ thiếu trong spec:** §10.2 mô tả `inject_schema_errors` nhưng không nói nên nhét hạng mục lạ vào cột nào.
- **Đã làm:** nhét vào `contract` thay vì `country`.
- **Vì sao:** `country` có chính sách `unmapped_action: raise`, nên nhét rác vào đó làm cả chuỗi dừng — đúng thiết kế nhưng khiến khung dữ liệu bẩn dùng chung không chạy hết được. Chính sách raise của `country` được kiểm tra riêng trong `test_p02_harmonize.py::test_param_unmapped_action_raise_vs_to_na`.
- **Vị trí:** `tests/fixtures/make_frames.py::inject_schema_errors`.

### Q-07 · Khung dữ liệu test: dòng ghi kg/ha kèm theo cột `yield_unit`

- **Chỗ thiếu trong spec:** §10.2 không nói bản xuất khảo sát có cột đơn vị hay không.
- **Đã làm:** `inject_unit_mix(..., declare_unit=True)` (mặc định) thêm cột `yield_unit`; đặt `False` để mô phỏng trường hợp không có thông tin đơn vị.
- **Vì sao:** cần cả hai tình huống. Có cột đơn vị → P02 quy đổi an toàn. Không có → P02 không được tự đoán, và P04 phải bắt được là *nghi lỗi đơn vị*. Cả hai đều có test riêng.
- **Câu hỏi cho data audit:** bản xuất của CIAT có cột đơn vị không, hay đơn vị được khai theo từng nguồn/quốc gia?

---

### Q-08 · P01 · Cột nhị phân/hạng mục ghi dạng chữ không bị cách ly

- **Spec nói gì:** §6.1 — ép kiểu theo schema, ô ép hỏng tính là lỗi dòng.
- **Đã làm khác:** cột `boolean`/`category` chưa ép được (vd `"Yes"/"No"/"Partial"`, `"Có"/"Không"`) được giữ nguyên dạng chữ cho P02 ánh xạ, phát `P01.DEFERRED_TO_P02`, không tính là lỗi dòng. Cột **số** vẫn giữ quy tắc cũ (`"abc"` trong cột số là lỗi thật).
- **Vì sao:** làm đúng spec thì P01 cách ly **120/120 dòng** của một bản xuất ghi `Yes/No`, và bảng alias `Yes/No` của P02 không bao giờ được dùng tới. Bài toán CIAT mô tả đúng định dạng này.
- **Vị trí:** `p01_schema_check.py`, khối ép kiểu.

### Q-09 · P02 · `null` trong bảng alias nghĩa là "cố ý để trống"

- **Chỗ thiếu trong spec:** §5.4 khai `"Partial": null` nhưng không nói P02 xử lý thế nào; code cũ coi `null` là "chưa ánh xạ" nên chính sách `raise` chặn cả chuỗi.
- **Đã làm:** giá trị có alias `null` → ô trống + cờ `flag__p02__intentional_na__<cột>` + finding `P02.ALIAS_TO_NA`; không bị `raise`. Giá trị **không có** trong bảng alias vẫn bị `raise`.
- **Kèm theo:** khi `raise`, P02 gom **mọi** giá trị lạ của mọi cột rồi báo một lần (trước đây dừng ở giá trị đầu tiên).

### Q-10 · Pipeline · Cổng an toàn chống mất dòng hàng loạt

- **Chỗ thiếu trong spec:** không có.
- **Đã làm:** bước nào loại quá `defaults.max_row_loss_per_step` (mặc định 20%) số dòng, hoặc làm bảng rỗng, thì dừng ngay với `<MÃ>.EXCESSIVE_ROW_LOSS` (BLOCKED, mã thoát 3), kèm nguyên nhân chính và vẫn ghi artifact.
- **Vì sao:** trước đây P01 làm rỗng bảng mà P02–P07 vẫn báo `ok`, lỗi chỉ lộ ở P08 với thông báo không liên quan.
- **Chờ dữ liệu thật:** ngưỡng 20% là giá trị khởi điểm.

---

## Quyết định đã chốt (2026-09-24)

1. **`country` và `cover_crop` giữ `unmapped_action: raise`.** Có giá trị lạ thì dừng, xem danh sách trong thông báo lỗi rồi bổ sung alias. Giá trị hợp lệ nhưng không xếp được thì khai `null`.
2. **`"Partial"` không bị bỏ.** Mỗi dòng được gắn cờ `flag__p05__partial` và tách ra `partial_review.parquet` để xem xét domain của chính cột trước khi quyết định. `partial_action: to_na` giữ nguyên (cột `cover_crop` để trống ở các dòng đó, dòng vẫn còn).

## Chờ dữ liệu thật mới chỉnh

| Tham số | Giá trị hiện tại |
|---|---|
| `P04.max_flag_rate` | 5% |
| `P05.threshold_months` / `threshold_sensitivity` | 2 / `[1, 2, 3]` |
| Khóa nghiệp vụ (`P03.key`) | `grower_id + field_id + year` |
| `P06` điền theo nhóm | theo nước, nhóm ≥ 30 dòng |
| `defaults.max_row_loss_per_step` | 20% |
| Cấp cụm (`P09.cluster_key`) | `grower_id` (nông hộ) — cần hỏi CIAT có cấp thôn/HTX không |
