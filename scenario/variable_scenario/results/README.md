# Kết quả mô phỏng variable_scenario

Ba notebook đã chạy đầy đủ ở **R=1000**, seed 20261021, lưới chung
n=250/500/1000/2000/4000/8000. ATE thật=2.0 trong mọi kịch bản đã chạy. Phần A và B có
648.000 dòng ước lượng (384.000 phần A, 264.000 phần B) và 162.000 dòng diagnostics
(96.000 phần A, 66.000 phần B). Phần D có thêm 240.000 dòng ước lượng và 48.000 dòng
diagnostics. Hình theo n: `figures_A/`, `figures_B/`, `figures_D/`.
T7, V7 và phần C chưa triển khai.

## Đọc và tái lập kết quả

- [variable_type.ipynb](../variable_type.ipynb): DGP T0–T6, estimator/SE, kiểm tra,
  diagnostics, Monte Carlo, nhận xét từng kịch bản và kết luận.
- [add_variable.ipynb](../add_variable.ipynb): V0–V5, mỗi kịch bản là một phần tự chứa.
- [ols_unfavorable.ipynb](../ols_unfavorable.ipynb): phần D, cùng khung với phần B;
  kết quả tóm tắt ở [README](../README.md) và ngay trong notebook.
- `<scenario>.csv`: long format, khóa scenario/analysis/n/rep/method, est, se, truth,
  status. `ok` là fit thành công; lỗi giữ dòng với est/se=NaN. `D_<mã>.csv` của phần D
  không có cột analysis.
- `<scenario>_diagnostics.csv`: một dòng/analysis/rep; tất cả overlap/balance/ESS dùng
  PS ước lượng. Riêng phần A có `cell_counts` (bảng A × mức X2 dạng JSON),
  `has_empty_cell` và `empty_cells` tính trên đủ mức cấu hình.
- `part_A_bias_coverage_all_T.csv`: **một file tổng hợp** của phần A, 64 dòng
  (scenario, analysis, method), hai hàng tiêu đề: Bias theo n rồi Coverage theo n.
- `part_A_summary.csv`, `part_B_summary.csv`: bias, MC SE bias, empirical SD,
  mean SE, SE/SD, RMSE, coverage, MC SE coverage, độ rộng CI và failure rate.
- `part_A_diagnostic_summary.csv`, `part_B_diagnostic_summary.csv`: trung bình
  diagnostics; `ps_valid_reps`, `ps_failed_reps` cho biết mẫu số, phần A có thêm
  `empty_cell_reps`.
- `part_A_metadata.json`, `part_B_metadata.json`: tham số, seed, gamma0, mức R và
  phiên bản thư viện.
- `part_A_conclusions.md`, `part_B_conclusions.md`: kết luận được sinh trực tiếp
  từ bảng kết quả; `T6_bias_coverage.png`, `X3_sd_ratio.png`: biểu đồ xuất độc lập.

Mở notebook và Run All từ thư mục variable_scenario, gốc ra_causal hoặc Seminar, với
kernel `ra_causal/.venv`. Mỗi notebook tự định nghĩa toàn bộ hàm, không phụ thuộc module
mô phỏng mới; riêng cell kiểm tra của phần B và D đọc `T0.csv` của phần A nên cần chạy
phần A trước. Phần B chạy hết khoảng 10 phút. Để chạy thử, đặt `RA_VARIABLE_REPS=200`
trước khi khởi động kernel; đổi lưới n bằng `RA_VARIABLE_N`. Run All ghi lại CSV; sao lưu
thư mục này nếu cần giữ kết quả cũ. Đặt `RA_VARIABLE_RUN_MC=0` để chỉ đọc lại CSV sẵn có.

## Kiểm tra baseline

Naive vẫn chệch do confounding; các kiểm tra gần không chệch áp dụng cho
OLS/IPTW/AIPW. Các dòng bên dưới đạt kiểm tra bias trong 3 MC SE, coverage trong
3 MC SE quanh 0.95 và SE/SD trong [0.8, 1.2]. Trên toàn lưới n, V0 đạt 18/18 dòng; T0
đạt 17/18, ngoại lệ là coverage của AIPW ở n=250 (0.927, cận dưới 0.929).

| scenario | analysis | n | method | bias | mc_se_bias | se_sd_ratio | coverage |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T0 | continuous | 500 | OLS | 0.0002 | 0.0030 | 0.9960 | 0.9480 |
| T0 | continuous | 500 | IPTW | 0.0007 | 0.0032 | 0.9765 | 0.9380 |
| T0 | continuous | 500 | AIPW | 0.0001 | 0.0031 | 0.9899 | 0.9430 |
| T0 | continuous | 2000 | OLS | -0.0001 | 0.0015 | 0.9765 | 0.9400 |
| T0 | continuous | 2000 | IPTW | -0.0004 | 0.0016 | 0.9698 | 0.9340 |
| T0 | continuous | 2000 | AIPW | -0.0002 | 0.0016 | 0.9682 | 0.9360 |
| V0 | S2 | 500 | OLS | 0.0002 | 0.0030 | 1.0062 | 0.9520 |
| V0 | S2 | 500 | IPTW | -0.0003 | 0.0031 | 0.9854 | 0.9500 |
| V0 | S2 | 500 | AIPW | -0.0009 | 0.0031 | 0.9930 | 0.9480 |
| V0 | S2 | 2000 | OLS | 0.0011 | 0.0015 | 1.0113 | 0.9580 |
| V0 | S2 | 2000 | IPTW | 0.0015 | 0.0015 | 1.0041 | 0.9500 |
| V0 | S2 | 2000 | AIPW | 0.0011 | 0.0015 | 1.0085 | 0.9500 |

## Phần A: kết quả và giải thích

OLS tại n=2000 (tất cả có 1000 lần thành công):

| scenario | analysis | bias | mc_se_bias | emp_sd | coverage |
| --- | --- | --- | --- | --- | --- |
| T0 | continuous | -0.0001 | 0.0015 | 0.0483 | 0.9400 |
| T1 | binary | 0.0013 | 0.0015 | 0.0461 | 0.9580 |
| T2 | binary | 0.0024 | 0.0015 | 0.0477 | 0.9460 |
| T3a | integer | 0.0014 | 0.0015 | 0.0479 | 0.9490 |
| T3a | dummy | 0.0014 | 0.0015 | 0.0480 | 0.9500 |
| T3b | integer | 0.1707 | 0.0015 | 0.0487 | 0.0680 |
| T3b | dummy | 0.0006 | 0.0015 | 0.0467 | 0.9520 |
| T4 | dummy | -0.0002 | 0.0015 | 0.0466 | 0.9540 |
| T4 | label | 0.1904 | 0.0016 | 0.0510 | 0.0350 |
| T5 | dummy | -0.0011 | 0.0015 | 0.0490 | 0.9390 |
| T6 | continuous | 0.0001 | 0.0015 | 0.0475 | 0.9450 |
| T6 | omit_X2 | 0.2359 | 0.0016 | 0.0512 | 0.0040 |
| T6 | binned_2 | 0.0862 | 0.0015 | 0.0490 | 0.5810 |
| T6 | binned_3 | 0.0489 | 0.0015 | 0.0485 | 0.8070 |
| T6 | binned_5 | 0.0234 | 0.0015 | 0.0479 | 0.9280 |
| T6 | binned_10 | 0.0092 | 0.0015 | 0.0479 | 0.9420 |

- **T1/T2:** bias OLS không quá 0.004 ở mọi n khi mã hóa 0/1 đúng. Coverage OLS của
  T1 là 0.926 ở n=250, thấp hơn cận 3 MC SE, các n khác 0.935–0.958; T2 là 0.945–0.962.
  T2 có 8/1000 rep rỗng ô ở n=250, IPTW/AIPW ghi nhận thất bại ở các rep đó; từ n=500
  không còn rep nào. Không thấy ô thưa làm OLS mất coverage ở các n đã xét.
- **T3a:** integer và dummy cho kết quả gần nhau, phù hợp với hiệu ứng tuyến tính theo
  mức. SD tăng do dummy rất nhỏ: ở n=250, OLS 0.1348 → 0.1352, IPTW 0.1418 → 0.1462,
  AIPW 0.1392 → 0.1400.
- **T3b:** ở n=2000, integer có bias +0.171 (OLS), +0.173 (IPTW), +0.176 (AIPW),
  coverage 0.05–0.07; dummy gần 0. Cả hai nuisance models dùng integer đều sai dạng nên
  double robustness không loại được bias đó.
- **T4:** ở n=2000, label có bias khoảng +0.190 ở cả ba estimator, coverage khoảng 0.035;
  dummy gần 0. Dấu và độ lớn phụ thuộc vector hiệu ứng riêng của PS và outcome
  (Cov(g,h) ≈ 0.19 trong cấu hình hiện tại). Thứ tự nhãn không thể thay hiệu ứng theo mức.
- **T5:** giảm overlap có chủ đích; xác suất mức hiếm=0.1, marginal PS mức này=0.98.
  Số rep có ô rỗng là 568/1000 ở n=250, 376 ở n=500, 130 ở n=1000, 28 ở n=2000, và 0 từ
  n=4000. IPTW/AIPW ghi nhận thất bại trong những rep này. OLS dùng mô hình outcome chung
  vẫn chạy được ở mọi rep, coverage 0.939–0.958. Khi hết lỗi fit, overlap kém chuyển
  thành trọng số lớn: ESS/n giảm từ 0.65 xuống 0.39, trọng số lớn nhất trung bình tăng
  từ 23 lên 116. SE/SD và coverage có điều kiện của IPTW/AIPW vẫn thấp, kể cả ở n lớn.

| n | method | valid_reps | failed_reps | failure_rate | se_sd_ratio | coverage |
| --- | --- | --- | --- | --- | --- | --- |
| 250 | IPTW | 432 | 568 | 0.5680 | 0.7434 | 0.8657 |
| 250 | AIPW | 432 | 568 | 0.5680 | 0.8051 | 0.8958 |
| 500 | IPTW | 624 | 376 | 0.3760 | 0.6727 | 0.8045 |
| 500 | AIPW | 624 | 376 | 0.3760 | 0.7342 | 0.8397 |
| 1000 | IPTW | 870 | 130 | 0.1300 | 0.6323 | 0.8138 |
| 1000 | AIPW | 870 | 130 | 0.1300 | 0.7051 | 0.8287 |
| 2000 | IPTW | 972 | 28 | 0.0280 | 0.7152 | 0.8539 |
| 2000 | AIPW | 972 | 28 | 0.0280 | 0.8219 | 0.8827 |
| 4000 | IPTW | 1000 | 0 | 0.0000 | 0.8260 | 0.8920 |
| 4000 | AIPW | 1000 | 0 | 0.0000 | 0.9121 | 0.9190 |
| 8000 | IPTW | 1000 | 0 | 0.0000 | 0.9142 | 0.9060 |
| 8000 | AIPW | 1000 | 0 | 0.0000 | 0.9585 | 0.9250 |

**T6:** bias tăng khi giảm số nhóm và không giảm khi tăng n, do mất thông tin X2. Với
2 nhóm, bias OLS khoảng 0.085–0.089, coverage giảm từ 0.864 (n=500) xuống 0.581 (n=2000)
và 0.050 (n=8000). Với 5 nhóm, bias khoảng 0.022–0.026, coverage giảm từ 0.945 xuống
0.928 và 0.807. Tăng n làm CI hẹp hơn quanh một ước lượng vẫn chệch.

| analysis | n | bias | mc_se_bias | coverage |
| --- | --- | --- | --- | --- |
| continuous | 500 | -0.0019 | 0.0030 | 0.9470 |
| omit_X2 | 500 | 0.2326 | 0.0033 | 0.3860 |
| binned_2 | 500 | 0.0847 | 0.0031 | 0.8640 |
| binned_3 | 500 | 0.0472 | 0.0031 | 0.9230 |
| binned_5 | 500 | 0.0220 | 0.0030 | 0.9450 |
| binned_10 | 500 | 0.0079 | 0.0030 | 0.9490 |
| continuous | 2000 | 0.0001 | 0.0015 | 0.9450 |
| omit_X2 | 2000 | 0.2359 | 0.0016 | 0.0040 |
| binned_2 | 2000 | 0.0862 | 0.0015 | 0.5810 |
| binned_3 | 2000 | 0.0489 | 0.0015 | 0.8070 |
| binned_5 | 2000 | 0.0234 | 0.0015 | 0.9280 |
| binned_10 | 2000 | 0.0092 | 0.0015 | 0.9420 |
| continuous | 8000 | 0.0023 | 0.0008 | 0.9390 |
| omit_X2 | 8000 | 0.2393 | 0.0008 | 0.0000 |
| binned_2 | 8000 | 0.0889 | 0.0008 | 0.0500 |
| binned_3 | 8000 | 0.0509 | 0.0008 | 0.4410 |
| binned_5 | 8000 | 0.0260 | 0.0008 | 0.8070 |
| binned_10 | 8000 | 0.0113 | 0.0008 | 0.9050 |

![T6: bias và coverage OLS theo n](T6_bias_coverage.png)

## Phần B: kết quả và giải thích

OLS tại n=2000 (tất cả có 1000 lần thành công; toàn phần B không có lần fit lỗi):

| scenario | analysis | bias | mc_se_bias | emp_sd | coverage |
| --- | --- | --- | --- | --- | --- |
| V0 | S2 | 0.0011 | 0.0015 | 0.0467 | 0.9580 |
| V1 | S2 | 0.2392 | 0.0017 | 0.0530 | 0.0060 |
| V1 | S3 | 0.0018 | 0.0016 | 0.0491 | 0.9440 |
| V2 | S2 | 0.0018 | 0.0017 | 0.0528 | 0.9450 |
| V2 | S3 | 0.0008 | 0.0015 | 0.0461 | 0.9530 |
| V3 | S2 | 0.0016 | 0.0014 | 0.0457 | 0.9570 |
| V3 | S3 | 0.0018 | 0.0016 | 0.0501 | 0.9530 |
| V4 | S2 | 0.0024 | 0.0015 | 0.0477 | 0.9460 |
| V4 | S3 | 0.0024 | 0.0015 | 0.0477 | 0.9470 |
| V5 | S2 | 0.1254 | 0.0016 | 0.0512 | 0.3240 |
| V5 | S3 | 0.0015 | 0.0015 | 0.0487 | 0.9590 |

- **V1:** bỏ X3 tạo bias OLS khoảng +0.236 và không giảm theo n; coverage về 0.000 từ
  n=4000. S3 gần 0. Max |SMD| trung bình sau IPTW trên S2 chỉ 0.034 (n=250) đến 0.006
  (n=8000), trong khi SMD X3 bị bỏ sót khoảng 0.49. Balance trên biến đã đưa vào mô hình
  không phát hiện confounder bị bỏ sót.
- **V2:** thêm biến tiên lượng Y giảm SD khoảng 10% ở cả ba estimator (OLS 0.87–0.91 lần
  tùy n; công thức FWL 0.895), không mất ESS. Mức 12% của pilot đúng với riêng n=2000.
  Bản R=200 trước đây chỉ thấy giảm 2.3%, nhiều khả năng do dao động Monte Carlo.
- **V3:** SD OLS tăng khoảng 9–14%, AIPW 16–25%, IPTW 27–31%. ESS/n giảm từ khoảng 0.91
  xuống 0.64. IPTW S3 có coverage 0.920–0.925 ở n≤500, về 0.95 từ n=2000. Thêm biến chỉ
  tác động A làm PS cực đoan hơn mà không giải thích thêm Y; FWL cho OLS 1.091, thấp hơn
  mức 15% của pilot.
- **V4:** tỷ lệ SD S3/S2 cao nhất là 1.007 (AIPW, n=250), từ n=2000 không quá 1.001. Chi
  phí của một biến noise rất nhỏ ở các n đã xét.
- **V5:** bỏ X3 có bias OLS khoảng +0.123, bằng 0.52 lần V1 (1−ρ²=0.51); S3 gần 0. X1
  tương quan với X3 nên mang một phần thông tin, nhưng chưa đủ để loại hết confounding:
  coverage OLS S2 vẫn về 0.003 ở n=8000. Thêm X3 làm SD IPTW tăng 3–9% nhưng S3 vẫn thắng
  về RMSE ở mọi n.

Tỷ lệ SD S3/S2 cho từng phương pháp, n=2000:

| scenario | method | S2 | S3 | SD_S3_over_S2 |
| --- | --- | --- | --- | --- |
| V1 | AIPW | 0.0534 | 0.0504 | 0.9442 |
| V1 | IPTW | 0.0538 | 0.0543 | 1.0081 |
| V1 | Naive | 0.0566 | 0.0566 | 1.0000 |
| V1 | OLS | 0.0530 | 0.0491 | 0.9258 |
| V2 | AIPW | 0.0534 | 0.0467 | 0.8750 |
| V2 | IPTW | 0.0542 | 0.0476 | 0.8772 |
| V2 | Naive | 0.0585 | 0.0585 | 1.0000 |
| V2 | OLS | 0.0528 | 0.0461 | 0.8733 |
| V3 | AIPW | 0.0461 | 0.0549 | 1.1920 |
| V3 | IPTW | 0.0465 | 0.0595 | 1.2805 |
| V3 | Naive | 0.0540 | 0.0540 | 1.0000 |
| V3 | OLS | 0.0457 | 0.0501 | 1.0969 |
| V4 | AIPW | 0.0485 | 0.0485 | 1.0005 |
| V4 | IPTW | 0.0500 | 0.0500 | 1.0002 |
| V4 | Naive | 0.0550 | 0.0550 | 1.0000 |
| V4 | OLS | 0.0477 | 0.0477 | 1.0003 |
| V5 | AIPW | 0.0532 | 0.0518 | 0.9740 |
| V5 | IPTW | 0.0597 | 0.0612 | 1.0252 |
| V5 | Naive | 0.0620 | 0.0620 | 1.0000 |
| V5 | OLS | 0.0512 | 0.0487 | 0.9503 |

![Tỷ lệ SD khi thêm X3](X3_sd_ratio.png)

## Mẫu số và giới hạn diễn giải

Bias, empirical SD, SE, RMSE và coverage tính trên **các lần fit thành công**;
`valid_reps`, `failed_reps`, `failure_rate` đi kèm từng nhóm. Đặc biệt, coverage
T5 là coverage có điều kiện, không đại diện cho một thủ tục luôn cho ra CI.
Diagnostics PS/balance/ESS cũng dùng các rep PS thành công; treated rate và số
lần ô rỗng dùng toàn bộ R rep. Naive/OLS được tính ngay cả khi PS không fit được.

Không clip PS, không regularize và không thay pseudoinverse cho outcome thiếu mức
một cách âm thầm. Các chẩn đoán `x3_smd_after` khi analysis bỏ X3 và
`x2_continuous_smd_after` trong T6 chỉ dùng thông tin sẵn có ở mô phỏng; chúng
không đi vào estimator và không thể quan sát trong bài toán thực nếu biến bị thiếu.

Phần A đã kiểm tra seed thường/seed con, consistency, phương sai đóng góp 0.25,
calibration treated=0.50 và mức hiếm T5=0.98, HC1, SMD nhị phân, dummy vắng mức,
AIPW khi ô rỗng. Phần B đã kiểm tra seed thường/seed con, consistency, HC1, công thức
SMD, tính đầy đủ của CSV, và V0 tái lập đúng ước lượng và SE của T0 phần A trên 400 rep.
Ở cả hai phần, SE IPTW được đối chiếu độc lập với sandwich của hệ estimating equations
dùng đạo hàm số. Cả ba notebook có đầy đủ outputs và không có cell lỗi.

Notebook phần B được viết lại theo khung của phần D ngày 02/11/2026. DGP và estimator
không đổi: chạy code mới với seed cũ (20261012) cho đúng các CSV của bản R=200 trước đó,
sai khác ước lượng và SE dưới 1e-14. Hai lần chạy đầy đủ cho CSV giống hệt nhau.
