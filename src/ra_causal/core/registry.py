from typing import Callable, Type, Any
import pandas as pd
from ra_causal.core.contracts import StepResult
from ra_causal.core.context import PipelineContext
from pydantic import BaseModel

# chuẩn hóa giao tiếp giữa các module trong pipeline, mỗi module sẽ có một hàm chạy (runner) nhận vào DataFrame, cấu hình và ngữ cảnh, trả về StepResult
ModuleRunner = Callable[[pd.DataFrame, BaseModel, PipelineContext], StepResult]


# lớp quản lý
class PreprocessRegistry:
    def __init__(self):
        self._modules: dict[str, tuple[ModuleRunner, Type[BaseModel]]] = {}

    # đăng ký một module mới với mã định danh và lớp cấu hình tương ứng
    def register(self, module_id: str, config_class: Type[BaseModel]):
        def decorator(func: ModuleRunner) -> ModuleRunner:
            if module_id in self._modules:
                raise ValueError(f"Module {module_id} already registered.")
            self._modules[module_id] = (func, config_class)
            return func
        return decorator

    # lấy hàm chạy (runner) của một module dựa trên mã định danh, nếu không tìm thấy sẽ ném KeyError
    def get_runner(self, module_id: str) -> ModuleRunner:
        if module_id not in self._modules:
            raise KeyError(f"Module {module_id} not found in registry.")
        return self._modules[module_id][0]

    # lấy lớp cấu hình của một module dựa trên mã định danh, nếu không tìm thấy sẽ ném KeyError
    def get_config_class(self, module_id: str) -> Type[BaseModel]:
        if module_id not in self._modules:
            raise KeyError(f"Module {module_id} not found in registry.")
        return self._modules[module_id][1]

    # danh sách tất cả các module đã đăng ký, trả về danh sách các mã định danh
    def available(self) -> list[str]:
        """Danh sách mã module đã đăng ký, dùng trong thông báo lỗi."""
        return sorted(self._modules)

    # kiểm tra xem một module có tồn tại trong registry hay không, trả về True hoặc False
    def __contains__(self, module_id: str) -> bool:
        return module_id in self._modules

REGISTRY = PreprocessRegistry()

