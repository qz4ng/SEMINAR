# Prompt bàn giao cho agent lập trình

Dán nguyên khối dưới đây cho agent (agent phải có quyền đọc/ghi trong `/home/doan/Seminar/ra_causal`).

---

Bạn là kỹ sư Python hiện thực khối **tiền xử lý dữ liệu** cho dự án suy luận nhân quả `ra_causal`.

**Bản thiết kế bắt buộc:** `/home/doan/Seminar/ra_causal/docs/SPEC_preprocessing.md`. Đọc **toàn bộ** file đó trước khi viết dòng code đầu tiên. Nó là hợp đồng: mọi tên cột, tên tham số, giá trị mặc định, mã lỗi, thứ tự chạy và yêu cầu test đều đã được quy định ở đó.

**Việc cần làm:** hiện thực đúng phạm vi §1.2 của spec — `core/`, `io/`, 9 module `preprocess/` (P01–P09), `pipeline/`, `cli/`, 4 file config, và bộ test theo §10. Các thư mục `simulate/`, `process/`, `estimate/`, `evaluate/`, `reporting/` **để trống** (chỉ `__init__.py` rỗng).

**Ràng buộc quan trọng nhất:**

1. Không bịa tên cột, tên tham số, giá trị mặc định hay mã lỗi. Tất cả đã liệt kê trong spec (§5, §6). Nếu cần thứ gì không có trong spec → ghi vào `docs/OPEN_QUESTIONS.md` theo mẫu §12.2, chọn phương án an toàn nhất (chỉ gắn cờ, không đổi dữ liệu), đánh dấu `# SPEC-GAP` trong code, **không tự quyết định im lặng**.
2. Không thêm thư viện ngoài §3 (`pandas`, `numpy`, `pyarrow`, `pyyaml`, `pydantic`, `scikit-learn`, `pytest`). CLI dùng `argparse`, log dùng `logging`.
3. Mặc định mọi module **không xóa dòng, không sửa giá trị** — chỉ gắn cờ và báo cáo. Việc thay đổi dữ liệu chỉ xảy ra khi người dùng bật tham số tương ứng, và luôn phải ghi vào report.
4. Mỗi module phải chạy **độc lập** được qua `python -m ra_causal.cli.run_step <MÃ>` (§9), và khi chạy cả chuỗi mà hỏng thì `run_report.json` phải chỉ đúng module hỏng kèm mã lỗi (§8.3, §8.4).
5. Viết test **trước** mỗi module theo đúng 5 loại ở §10.3; dữ liệu test do factory ở §10.2 sinh ra, không dùng dữ liệu thật, không tải gì từ mạng.

**Thứ tự thi công:** theo §13 của spec.

**Xong khi nào:** đủ toàn bộ checklist §11. Khi bàn giao, báo cáo lại: các mục trong `OPEN_QUESTIONS.md`, kết quả `pytest`, và ví dụ đầu ra `run_report.json` của một lần chạy hỏng có chủ ý ở P04 (để chứng minh cơ chế định vị lỗi hoạt động).

Không hiện thực bất kỳ phương pháp nhân quả nào (propensity score, weighting, ước lượng) — phần đó thuộc giai đoạn sau.

---

## Ghi chú cho người giao việc

- Nếu muốn agent làm **từng phần** cho dễ kiểm: cắt theo §13, ví dụ lượt 1 = mục 1–2 (`core/`, `io/`, factory test), lượt 2 = P01–P04, lượt 3 = P05–P09, lượt 4 = `pipeline/` + `cli/` + golden run.
- Sau mỗi lượt, kiểm nhanh bằng ba câu hỏi: (1) `pytest` có xanh không; (2) mọi tham số trong `configs/preprocess.yaml` có đúng bảng trong spec không; (3) thử sửa một tham số bất kỳ trong YAML rồi chạy lại — kết quả có đổi đúng hướng như §10.3 loại 4 không.
