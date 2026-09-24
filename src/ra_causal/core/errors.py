from typing import Any, Optional

# đoạn mã này định nghĩa Hệ thống báo lỗi tùy chỉnh cho toàn bộ thư viện ra_causal
class RaCausalError(Exception):
# gốc của các lỗi tùy chỉnh trong ra_causal, tất cả các lỗi khác sẽ kế thừa từ lớp này
    def __init__(self, module_id: str, code: str, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message) # gọi hàm khởi tạo của lớp cha (Exception) với thông điệp lỗi
        self.module_id = module_id # mã định danh của module nơi lỗi xảy ra, ví dụ: "P01" cho module kiểm tra schema
        self.code = code # mã lỗi cụ thể, ví dụ: "P01.MISSING_REQUIRED_COLUMN"
        self.message = message # thông điệp lỗi mô tả vấn đề, ví dụ: "Missing required columns: ['record_id']"
        self.details = details or {} # từ điển chứa thông tin chi tiết bổ sung về lỗi, ví dụ: {"missing": ["record_id"]}

class ConfigError(RaCausalError):
    # lỗi liên quan đến cấu hình, ví dụ: cấu hình không hợp lệ hoặc thiếu thông tin cần thiết
    pass

class SchemaError(RaCausalError):
    # lỗi liên quan đến schema, ví dụ: dữ liệu không phù hợp với định dạng chuẩn
    pass

class ContractError(RaCausalError):
    # lỗi liên quan đến cấu hình dữ liệu, ví dụ: dữ liệu không tuân thủ các ràng buộc đã định nghĩa
    pass

class DataQualityError(RaCausalError):
    # lỗi liên quan đến chất lượng dữ liệu, ví dụ: dữ liệu bị thiếu, sai lệch hoặc không nhất quán
    pass

class DependencyError(RaCausalError):
    # lỗi liên quan đến phụ thuộc giữa các module, ví dụ: một module không thể hoạt động mà không có module khác
    pass

