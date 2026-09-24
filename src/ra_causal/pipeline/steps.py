import pandas as pd
from pydantic import BaseModel
import time
import traceback

from ra_causal.core.contracts import StepResult, Status
from ra_causal.core.context import PipelineContext
from ra_causal.core.errors import ContractError, RaCausalError, DependencyError, DataQualityError

def run_step(module_id: str, runner, cfg: BaseModel, df: pd.DataFrame, ctx: PipelineContext,
             max_row_loss: float | None = 0.20) -> StepResult:
    """Chạy một module trong lớp áo kiểm tra hợp đồng.

    `max_row_loss`: tỷ lệ dòng tối đa một bước được phép loại (cách ly, gộp trùng, bỏ dòng).
    Vượt ngưỡng -> DataQualityError (BLOCKED). `None` để tắt.
    """
    # Check context requirements (basic heuristic for now or manually mapped)
    if module_id == "P06" and "adjustment_set" not in ctx._written:
        raise DependencyError(module_id, "P06.MISSING_ADJUSTMENT_SET", "P06 cần ctx.adjustment_set do P08 tạo; hãy chạy --from P08 hoặc truyền --context <file json>")
    if module_id == "P08" and "eligible_columns" not in ctx._written:
        raise DependencyError(module_id, "P08.MISSING_ELIGIBLE_COLUMNS", "P08 cần ctx.eligible_columns do P07 tạo; hãy chạy --from P07 hoặc truyền --context <file json>")

    n_rows_in = len(df)
    n_cols_in = len(df.columns)
    
    # Store initial state to check post-conditions
    # canonical_cols = set(ctx.schema.columns.keys())
    # initial_canonical = canonical_cols.intersection(df.columns)
    
    try:
        res = runner(df, cfg, ctx)
    except RaCausalError:
        raise
    except Exception as e:
        # Wrap unexpected exception
        tb = traceback.format_exc().splitlines()[-50:]
        raise ContractError(module_id, f"{module_id}.UNEXPECTED_EXCEPTION", str(e), {"traceback": tb}) from e

    out = res.data
    report = res.report

    # Post-conditions check
    if report.rows_dropped == 0 and len(out) < n_rows_in:
        raise ContractError(module_id, f"{module_id}.LOST_ROWS", f"Module dropped {n_rows_in - len(out)} rows without declaring")

    # Cổng an toàn: một bước làm mất quá nhiều dòng thì dừng NGAY TẠI BƯỚC ĐÓ.
    # Không có cổng này, P01 từng cách ly 120/120 dòng rồi các bước sau vẫn báo "ok"
    # trên bảng rỗng, và lỗi chỉ lộ ra ở P08 với một thông báo không liên quan.
    if n_rows_in > 0 and max_row_loss is not None:
        lost = n_rows_in - len(out)
        loss_rate = lost / n_rows_in
        if len(out) == 0 or loss_rate > max_row_loss:
            causes = sorted(
                [{"code": f.code, "column": f.column, "count": f.count}
                 for f in report.findings if f.severity in ("warning", "error", "blocking") and f.count],
                key=lambda d: -d["count"])[:5]
            hint = "; ".join(f"{c['code']}" + (f" ({c['column']})" if c["column"] else "") + f": {c['count']}"
                             for c in causes) or "xem findings của bước này"
            err = DataQualityError(
                module_id, f"{module_id}.EXCESSIVE_ROW_LOSS",
                f"{module_id} loại {lost}/{n_rows_in} dòng ({loss_rate:.0%}), vượt ngưỡng "
                f"{max_row_loss:.0%}. Nguyên nhân chính: {hint}",
                {"rows_in": n_rows_in, "rows_out": len(out), "loss_rate": round(loss_rate, 4),
                 "limit": max_row_loss, "top_findings": causes})
            err.result = res  # để runner vẫn ghi được artifact (vd quarantine) mà xem lại
            raise err

    # Tính duy nhất của record_id: chỉ bắt lỗi khi module TỰ TẠO RA trùng lặp.
    # Dữ liệu thô vốn có thể trùng — đó là việc của P03, nên không thể đòi mọi module
    # trước P03 phải trả về khóa duy nhất.
    if "record_id" in out.columns and "record_id" in df.columns:
        was_unique = not df["record_id"].duplicated().any()
        now_unique = not out["record_id"].duplicated().any()
        if was_unique and not now_unique:
            raise ContractError(
                module_id, f"{module_id}.DUPLICATE_RECORD_ID",
                "Module đã tạo ra record_id trùng lặp (đầu vào vốn duy nhất)")
        
    # Any other canonical columns check
    # We could check if it lost canonical columns unexplainably but skipping for brevity
    
    # Context updates
    for k, v in res.context_updates.items():
        setattr(ctx, k, v)
        ctx._written.add(k)
        if k not in report.context_updates:
            report.context_updates.append(k)
            
    return res

