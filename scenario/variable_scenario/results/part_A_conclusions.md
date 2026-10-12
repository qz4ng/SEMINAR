## 9. Kết luận từ lần chạy

Với R=200, OLS T0 có bias -0.000; T1 có bias +0.004.

Biến định tính biểu diễn đúng bằng dummy/0–1 có thể điều chỉnh confounding tốt. Hiệu ứng phi tuyến hoặc danh nghĩa cần xét mã hóa theo mức, đồng thời kiểm tra các ô thưa.

T3b: integer bias +0.172, dummy +0.000; T4: label -0.133, dummy -0.006.

T6 ở n=2000: continuous: bias -0.002; omit_X2: bias +0.231; binned_2: bias +0.083; binned_3: bias +0.046; binned_5: bias +0.021; binned_10: bias +0.006. Chia nhiều nhóm giữ được nhiều thông tin hơn; tăng n không khôi phục thông tin liên tục bị mất.

Coverage và SE/SD cần đọc cùng MC SE và failure rate, đặc biệt T5. Kết quả đang dùng R=200; R=1000 là mức chạy đầy đủ theo thiết kế.