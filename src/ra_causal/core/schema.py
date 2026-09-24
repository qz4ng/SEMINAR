from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal, Any
import yaml

class ColumnContract(BaseModel):
    # ép buộc kiểu dữ liệu, sử dụng các kiểu từ i8->i16 để thiết kế chạy trên dữ liệu lớn
    dtype: Literal["string", "category", "int16", "int8", "float32", "boolean"]
    required: bool
    measured_at: Literal["pre", "at", "post", "unknown"] # này bên nhân quả, đa thời điểm so với lúc thực hiện can thiệp
    #dag_role là vai trò của biến
    dag_role: Literal["id", "cluster", "confounder", "treatment", "treatment_version", "mediator", "outcome", "outcome_predictor", "collider", "instrument", "noise", "ambiguous"]
    # đơn vị đo lường unit
    unit: Optional[str] = None
    range: Optional[list[float]] = None
    allowed: Optional[list[Any]] = None
    affected_by_treatment: Optional[bool] = None

    @model_validator(mode="after")
    def check_affected_by_treatment(self):

        # nếu biến đo lường sau can thiệp -> khai báo rõ có ảnh hưởng ko
        if self.measured_at == "post" and self.affected_by_treatment is None:
            raise ValueError("affected_by_treatment is required when measured_at is 'post'")
        # ngược lại thì ko được điền thuộc tính affected_by_treatment, vì nếu biến đo lường trước can thiệp thì ko thể biết có bị ảnh hưởng hay ko
        if self.measured_at != "post" and self.affected_by_treatment is not None:
            raise ValueError("affected_by_treatment must not be set when measured_at is not 'post'")
        return self


# Lớp này gom tất cả các ColumnContract lại thành một từ điển
# -> để mô tả schema của DataFrame đầu vào, bao gồm các cột và các thuộc tính của chúng
class CanonicalSchema(BaseModel):
    version: str
    columns: dict[str, ColumnContract]

    @classmethod
    def load(cls, path: str) -> "CanonicalSchema":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)

