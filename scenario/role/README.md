# Ý tưởng và mục đích
# Các kịch bản 
# Các phương pháp ước lượng
# Một số hàm bổ trợ
## Influence function
- Vị trí: Được xây dựng trong file utilies.py 
- Mục đích: Chứa các estimating function của từng quan sát để thực hiện phép tính ma trận M-estimation với công thức toán học:
$
\psi_i= 
\begin{bmatrix} 
    \frac{A_i}{e_i}(Y_i-\hat{\mu}_1)\\[5pt] 
    \frac{1-A_i}{1-e_i}(Y_i-\hat{\mu}_0)\\[5pt]
    X_i(A_i-e_i)
\end{bmatrix}
$.
Bao gồm:
    - estimating function của $\hat{u_1}$
    - estimating function của $\hat{u_2}$
    - Score của hệ số intercept
	- Score của hệ số X1
	- Score của hệ số X2
## Ma trận Jacobian của hệ phương trình ước lượng
- Vị trí: Được xây dựng trong file utilies.py 
- Công thức: $B= \dfrac{1}{n} \sum_{i=1}^n \dfrac{\partial \psi_i(\theta)}{\partial \theta^T}, \quad B= 
\begin{bmatrix} 
B_{11}&0&B_{1\gamma}\\ 
0&B_{22}&B_{2\gamma}\\
0&0&B_{\gamma\gamma}
\end{bmatrix} $
- Cụ thể:
1. Đạo hàm theo $\hat{u_1}, \hat{u_0}$:

Ta có: $ \frac{\partial}{\partial\mu_1} \left[\frac{A_i}{e_i}(Y_i-\mu_1) \right] = -\frac{A_i}{e_i} $

Lấy trung bình:  $B_{11}=-\frac{1}{n}\sum_i\frac{A_i}{e_i}$

Tương tự: $B_{22}=-\frac{1}{n} \sum_i\frac{1-A_i}{1-e_i}$

2. Đạo hàm treatment theo hệ số của PS

Ta bắt đầu từ: $\psi_{i,1}= \frac{A_i}{e_i}(Y_i-\mu_1)$

Đạo hàm theo $\gamma$: $\frac{\partial e_i}{\partial\gamma} =e_i(1-e_i)X_i $

Suy ra: $\frac{\partial\psi_{i,1}}{\partial\gamma} = -\frac{A_i(1-e_i)}{e_i} (Y_i-\mu_1)X_i$

Lấy trung bình: $B_{1\gamma} = -\frac{1}{n}\sum_i \frac{A_i(1-e_i)}{e_i} (Y_i-\mu_1)X_i $

3. Đạo hàm control theo hệ số của PS

Bắt đầu từ: $\psi_{i,2}= \frac{1-A_i}{1-e_i}(Y_i-\mu_0) $

Đạo hàm theo $\gamma$: $ \frac{\partial\psi_{i,2}}{\partial\gamma} = \frac{(1-A_i)e_i}{1-e_i} (Y_i-\mu_0)X_i $

Lấy trung bình: $ B_{2\gamma} = \frac{1}{n}\sum_i \frac{(1-A_i)e_i}{1-e_i} (Y_i-\mu_0)X_i $

4. Đạo hàm của Logistic Score theo hệ số PS

Phương trình score: $ \psi_{i,\gamma}=X_i(A_i-e_i) $

Đạo hàm theo $\gamma$: $ \frac{\partial\psi_{i,\gamma}} {\partial\gamma^\top} = -e_i(1-e_i)X_iX_i^\top $

Do đó: $ B_{\gamma\gamma} = -\frac{1}{n}\sum_i e_i(1-e_i)X_iX_i$