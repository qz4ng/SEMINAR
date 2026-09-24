from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import pandas as pd

class Status(str, Enum):
    OK = "ok" # oke rồi bro
    OK_WITH_WARNINGS = "warning" # chạy xong thấy cảnh báo!
    BLOCKED = "blocked" # module hoạt động đúng nhưng dữ liệu vi phạm ngưỡng
    FAILED = "failed"# module bị lỗi, không chạy được

    # Chỗ này làm rõ blocked là dữ liệu có vấn đề, còn failed là code hoặc hạ tầng bị lỗi, không chạy được
@dataclass
class Finding:
    code: str # lưu trữ mã lỗi
    severity: str  # "info" | "warning" | "error" | "blocking", mức độ nghiêm trọng
    message: str # thông điệp báo cáo
    count: int # số dòng bị ảnh hưởng
    column: Optional[str] = None #  tên cột gây lỗi
    sample_ids: list[str] = field(default_factory=list) #danh sách các ID mẫu bị lỗi
    details: dict[str, Any] = field(default_factory=dict) 

@dataclass
class StepReport: # Đóng gói toàn bộ báo cáo siêu dữ liệu (metadata) về quá trình thực thi của một module
    module_id: str
    module_name: str
    spec_version: str
    status: str
    started_at: str
    duration_s: float
    n_rows_in: int
    n_rows_out: int
    n_cols_in: int
    n_cols_out: int
    rows_dropped: int
    rows_flagged: int
    columns_added: list[str]
    columns_modified: list[str]
    params_effective: dict[str, Any] #Lưu vết thông tin cấu hình đã dùng
    findings: list[Finding] # danh sách lỗi
    artifacts: dict[str, str]
    context_updates: list[str]

    def to_dict(self) -> dict[str, Any]: 
       # dùng để serialize (chuyển đổi) object này thành định dạng JSON chuẩn, phục vụ cho việc lưu log vào cơ sở dữ liệu
        from ra_causal.utils.pandas_tools import jsonify
        return jsonify({
            "module_id": self.module_id,
            "module_name": self.module_name,
            "spec_version": self.spec_version,
            "status": self.status,
            "started_at": self.started_at,
            "duration_s": self.duration_s,
            "n_rows_in": self.n_rows_in,
            "n_rows_out": self.n_rows_out,
            "n_cols_in": self.n_cols_in,
            "n_cols_out": self.n_cols_out,
            "rows_dropped": self.rows_dropped,
            "rows_flagged": self.rows_flagged,
            "columns_added": self.columns_added,
            "columns_modified": self.columns_modified,
            "params_effective": self.params_effective,
            "findings": [f.__dict__ for f in self.findings],
            "artifacts": self.artifacts,
            "context_updates": self.context_updates
        })

@dataclass(frozen=True)
class StepResult:
    data: pd.DataFrame
    report: StepReport
    artifacts: dict[str, pd.DataFrame] = field(default_factory=dict)
    context_updates: dict[str, Any] = field(default_factory=dict)

# Cột hệ thống
SYS_COL_CLUSTER_ID = "cluster_id"
SYS_COL_FOLD_ID = "fold_id"
SYS_COL_OUTCOME_OBSERVED = "c_outcome_observed"
SYS_COL_ROW_SOURCE = "row_source"
SYS_COL_DUP_GROUP_ID = "dup_group_id"

SYSTEM_COLUMNS = [
    SYS_COL_CLUSTER_ID,
    SYS_COL_FOLD_ID,
    SYS_COL_OUTCOME_OBSERVED,
    SYS_COL_ROW_SOURCE,
    SYS_COL_DUP_GROUP_ID
]

