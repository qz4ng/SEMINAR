## 9. Kết luận từ lần chạy

Với R=200, bỏ X3 ở V1 có bias OLS +0.236; thêm X3 có bias +0.001. Max |SMD| trung bình sau IPTW trên biến S2 là 0.011 nhưng SMD X3 bị bỏ sót là 0.485. Balance tốt trên biến quan sát không chứng minh hết confounding.

Tỉ lệ SD OLS S3/S2: V2=0.977; V3=1.120; V4=1.002. Biến tiên lượng Y có lợi cho độ chính xác; biến chỉ tác động A có thể làm tăng phương sai và giảm ESS; biến noise có ít lợi ích.

V5 tương quan rho=0.7: bias S2 +0.121, S3 -0.001. X1 chỉ mang một phần thông tin của X3.

Số biến cần dựa trên vai trò trong DAG. Các kết luận này áp dụng cho DGP và estimator đang xét; chênh lệch nhỏ ở R=200 cần xác nhận R=1000. V7 hậu điều trị là tùy chọn chưa chạy.