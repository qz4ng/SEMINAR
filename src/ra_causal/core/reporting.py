import json
from typing import Any, Optional
from ra_causal.core.contracts import StepReport
from ra_causal.utils.pandas_tools import jsonify
import hashlib

def write_run_report(
    path: str,
    run_id: str,
    started_at: str,
    finished_at: str,
    duration_s: float,
    status: str,
    failed_step: Optional[str],
    config_dict: dict[str, Any],
    schema_version: str,
    input_info: dict[str, Any],
    steps: list[StepReport],
    context_final: dict[str, Any],
    outputs_info: dict[str, Any]
):
    
    config_json = json.dumps(jsonify(config_dict), sort_keys=True)
    config_digest = hashlib.sha256(config_json.encode("utf-8")).hexdigest()[:12]

    report = {
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_s": duration_s,
        "status": status,
        "failed_step": failed_step,
        "config_digest": config_digest,
        "schema_version": schema_version,
        "input": input_info,
        # Chấp nhận cả StepReport lẫn dict đã dựng sẵn, để một bước hỏng không làm
        # sập luôn việc ghi báo cáo — đó chính là lúc báo cáo cần nhất.
        "steps": [s.to_dict() if hasattr(s, "to_dict") else dict(s) for s in steps],
        "context_final": context_final,
        "outputs": outputs_info
    }
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(jsonify(report), f, ensure_ascii=False, indent=2)

