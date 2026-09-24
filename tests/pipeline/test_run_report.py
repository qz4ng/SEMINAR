"""run_report.json phải đủ trường và đọc được — đó là nơi trả lời 'vì sao con số này ra như vậy'."""
import json
import os
import shutil

import pytest
import yaml

from ra_causal.pipeline.runner import run_pipeline
from tests.conftest import PIPELINE_ORDER, PREPROCESS_CONFIG_PATH, SCHEMA_PATH
from tests.fixtures.make_frames import make_dirty_frame

TOP_LEVEL_KEYS = {
    "run_id", "started_at", "finished_at", "duration_s", "status", "failed_step",
    "config_digest", "schema_version", "input", "steps", "context_final", "outputs",
}

STEP_KEYS = {
    "module_id", "module_name", "spec_version", "status", "started_at", "duration_s",
    "n_rows_in", "n_rows_out", "n_cols_in", "n_cols_out", "rows_dropped", "rows_flagged",
    "columns_added", "columns_modified", "params_effective", "findings", "artifacts",
    "context_updates",
}


@pytest.fixture
def run_dir(tmp_path):
    df, _ = make_dirty_frame(200, 0)
    input_path = tmp_path / "dirty.csv"
    df.to_csv(input_path, index=False)

    with open(PREPROCESS_CONFIG_PATH, "r", encoding="utf-8") as f:
        prep_cfg = yaml.safe_load(f)
    p_cfg_path = tmp_path / "preprocess.yaml"
    with open(p_cfg_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(prep_cfg, f, allow_unicode=True)

    schema_dir = tmp_path / "schema"
    schema_dir.mkdir()
    shutil.copy(SCHEMA_PATH, schema_dir / "canonical.yaml")

    pipe_cfg_path = tmp_path / "pipeline.yaml"
    pipe_cfg_path.write_text(
        "version: 1\ninput:\n  adapter: canonical\n"
        f"steps: [{', '.join(PIPELINE_ORDER)}]\n", encoding="utf-8")

    exit_code = run_pipeline(
        pipeline_config_path=str(pipe_cfg_path),
        preprocess_config_path=str(p_cfg_path),
        input_path=str(input_path),
        output_dir=str(tmp_path),
    )
    assert exit_code == 0, "khung dữ liệu bẩn phải chạy hết chuỗi"

    report_dir = os.listdir(tmp_path / "reports")[0]
    with open(tmp_path / "reports" / report_dir / "run_report.json", encoding="utf-8") as f:
        return json.load(f), tmp_path


@pytest.mark.integration
def test_report_has_all_top_level_keys(run_dir):
    rep, _ = run_dir
    assert TOP_LEVEL_KEYS.issubset(rep.keys())
    assert rep["status"] in {"ok", "warning", "blocked", "failed"}
    assert rep["failed_step"] is None
    assert len(rep["config_digest"]) == 12


@pytest.mark.integration
def test_every_step_report_is_complete_and_ordered(run_dir):
    rep, _ = run_dir
    assert [s["module_id"] for s in rep["steps"]] == PIPELINE_ORDER
    for step in rep["steps"]:
        assert STEP_KEYS.issubset(step.keys()), f"{step['module_id']} thiếu trường báo cáo"
        assert step["params_effective"], "phải ghi lại toàn bộ tham số đã dùng"
        assert step["columns_added"] == sorted(step["columns_added"])
        for finding in step["findings"]:
            assert finding["code"].startswith(step["module_id"] + ".")
            assert finding["severity"] in {"info", "warning", "error", "blocking"}


@pytest.mark.integration
def test_report_records_the_decisions_needed_to_reproduce(run_dir):
    rep, tmp_path = run_dir
    ctx = rep["context_final"]
    assert ctx["adjustment_set"], "phải ghi lại tập biến điều chỉnh L"
    assert ctx["treatment_definition"]["rule"], "phải ghi lại quy tắc định nghĩa treatment"
    assert ctx["cluster_column"] == "cluster_id"
    assert ctx["outcome_observed_column"] == "c_outcome_observed"

    # Số dòng phải nối tiếp nhau: đầu ra bước trước là đầu vào bước sau
    for prev, nxt in zip(rep["steps"], rep["steps"][1:]):
        assert prev["n_rows_out"] == nxt["n_rows_in"]


@pytest.mark.integration
def test_outputs_exist_on_disk(run_dir):
    rep, tmp_path = run_dir
    processed = os.path.join(tmp_path, "processed", rep["run_id"])
    assert os.path.exists(os.path.join(processed, "analysis_ready.parquet"))
    assert os.path.exists(os.path.join(processed, "data_dictionary.csv"))
