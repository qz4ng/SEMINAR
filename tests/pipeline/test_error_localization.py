import json
import os
import shutil

import pytest
import yaml

from ra_causal.pipeline.runner import run_pipeline
from tests.conftest import PREPROCESS_CONFIG_PATH, SCHEMA_PATH
from tests.fixtures.make_frames import make_dirty_frame


@pytest.mark.integration
def test_error_localization(tmp_path):
    """Một bước hỏng phải được định vị chính xác: đúng module, đúng mã lỗi, đúng mã thoát,
    và các bước phía sau KHÔNG được chạy."""
    df, _ = make_dirty_frame(300, 0)
    # Ghi CSV, không ghi parquet: dữ liệu bẩn có cột lẫn kiểu (chuỗi trong cột số)
    # mà parquet không chứa được — đúng như luồng thật đọc bản xuất khảo sát.
    input_path = tmp_path / "dirty.csv"
    df.to_csv(input_path, index=False)

    # Dùng CHÍNH config và schema thật, chỉ siết một tham số để ép P04 chặn.
    with open(PREPROCESS_CONFIG_PATH, "r", encoding="utf-8") as f:
        prep_cfg = yaml.safe_load(f)
    prep_cfg["defaults"]["fail_fast"] = True
    prep_cfg["p04"]["max_flag_rate"] = 0.001

    p_cfg_path = tmp_path / "preprocess.yaml"
    with open(p_cfg_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(prep_cfg, f, allow_unicode=True)

    schema_dir = tmp_path / "schema"
    schema_dir.mkdir()
    shutil.copy(SCHEMA_PATH, schema_dir / "canonical.yaml")

    pipe_cfg_path = tmp_path / "pipeline.yaml"
    pipe_cfg_path.write_text(
        "version: 1\ninput:\n  adapter: canonical\n"
        "steps: [P01, P02, P03, P04, P05, P07, P08, P06, P09]\n",
        encoding="utf-8",
    )

    exit_code = run_pipeline(
        pipeline_config_path=str(pipe_cfg_path),
        preprocess_config_path=str(p_cfg_path),
        input_path=str(input_path),
        output_dir=str(tmp_path),
    )

    assert exit_code == 3, "vượt ngưỡng chất lượng phải là BLOCKED (3), không phải FAILED"

    report_dirs = os.listdir(tmp_path / "reports")
    assert len(report_dirs) == 1
    with open(tmp_path / "reports" / report_dirs[0] / "run_report.json", encoding="utf-8") as f:
        rep = json.load(f)

    assert rep["status"] == "blocked"
    assert rep["failed_step"] == "P04"

    ran = [s["module_id"] for s in rep["steps"]]
    assert "P04" in ran, "bước hỏng vẫn phải có báo cáo riêng trong run_report.json"
    assert "P05" not in ran, "các bước sau bước hỏng không được chạy"

    p04_report = next(s for s in rep["steps"] if s["module_id"] == "P04")
    assert p04_report["status"] == "blocked"
    assert p04_report["findings"][0]["code"] == "P04.MAX_FLAG_RATE_EXCEEDED"
    assert p04_report["params_effective"]["max_flag_rate"] == 0.001
