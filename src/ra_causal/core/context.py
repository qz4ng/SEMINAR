from dataclasses import dataclass, field
from typing import Any, Optional
import numpy as np
from ra_causal.core.schema import CanonicalSchema

@dataclass
# class này định nghĩa cấu trúc thư mục chuẩn cho một lần chạy (run) của pipeline, đảm bảo các file sinh ra không bị ghi đè lộn xộn
class RunPaths:
    interim: str # nơi lưu các file dữ liệu trung gian (đang xử lý dang dở)
    processed: str # nơi lưu các file dữ liệu sach đã xử lý xong -> đưa vào mô hình
    reports: str # nơi xuất các file log, báo cáo (như file JSON được sinh ra từ hàm to_dict() ở đoạn code trước

@dataclass
# class này là bối cảnh luồng thực thi
class PipelineContext:
    # nhóm thông tin hệ thống, không đổi trong pipeline chạy
    run_id: str # mã định danh duy nhất cho một lần chạy pipeline
    schema: CanonicalSchema # khung chuẩn dữ liệu (CanonicalSchema) dùng để đối chiếu ở bước P01
    rng: np.random.Generator # bộ sinh số ngẫu nhiên (random number generator) dùng để đảm bảo tính ngẫu nhiên có thể tái lập (reproducible)
    paths: RunPaths # phiên bản khởi tạo của RunPaths
    
    # nhóm thông tin trạng thái, được module cập nhật liên tục
    _written: set[str] = field(default_factory=set) # lưu trữ các cột đã được ghi ra file, tránh ghi đè lộn xộn
    quarantined_ids: list[str] = field(default_factory=list) # danh sách các ID bị lỗi do P01 phát hiện
    unit_conversions: dict[str, float] = field(default_factory=dict) # từ điển lưu lại tỷ lệ chuyển đổi đơn vị khi dữ liệu cần chuẩn hóa
    duplicate_groups: int = 0 # số nhóm bản ghi trùng lặp được phát hiện bởi P03

    # nhóm cấu hình phân tích nhân quả, được module cập nhật liên tục
    treatment_column: str = "cover_crop" # cột biểu diễn trạng thái can thiệp
    treatment_definition: dict[str, Any] = field(default_factory=dict) # lưu trữ định nghĩa chi tiết về can thiệp, ví dụ: {"cover_crop": ["yes", "no"]} hoặc {"cover_crop": ["species1", "species2", "species3"]}
    blocked_columns: list[str] = field(default_factory=list) # danh sách các cột bị chặn (blocked) do vi phạm ngưỡng, ví dụ: ["yield", "soil_moisture"]
    eligible_columns: list[str] = field(default_factory=list) # danh sách các cột đủ điều kiện để đưa vào phân tích nhân quả, ví dụ: ["yield", "soil_moisture", "temperature"]
    adjustment_set: list[str] = field(default_factory=list) # danh sách các cột được chọn làm tập điều chỉnh (adjustment set) cho mô hình nhân quả, ví dụ: ["soil_moisture", "temperature"]
    adjustment_set_variants: dict[str, list[str]] = field(default_factory=dict) # lưu trữ các biến thể của tập điều chỉnh, ví dụ: {"variant1": ["soil_moisture"], "variant2": ["temperature"], "variant3": ["soil_moisture", "temperature"]}
    outcome_observed_column: Optional[str] = None # cột biểu diễn kết quả quan sát được (outcome), ví dụ: "yield"
    ps_basis_spec: dict[str, Any] = field(default_factory=dict) # lưu trữ thông tin về cơ sở của propensity score, ví dụ: {"model_type": "logistic", "features": ["soil_moisture", "temperature"]}
    cluster_column: Optional[str] = None # dùng để phân cụm dữ liệu (như module P09), cần thiết khi tính toán sai số chuẩn theo cụm (clustered standard errors).
    fold_column: Optional[str] = None # cột chia tập dữ liệu (K-fold) dùng trong Cross-Validation để đánh giá mô hình.

