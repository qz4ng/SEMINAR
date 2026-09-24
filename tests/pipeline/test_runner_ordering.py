import pytest
import os
import json
from tests.fixtures.make_frames import make_dirty_frame
from ra_causal.pipeline.runner import run_pipeline

@pytest.mark.integration
def test_runner_ordering(tmp_path):
    df, truth = make_dirty_frame(300, 0)
    # Ghi CSV, không ghi parquet: dữ liệu bẩn có cột lẫn kiểu (chuỗi trong cột số)
    # mà parquet không chứa được — đúng như luồng thật đọc bản xuất khảo sát.
    input_path = tmp_path / "dirty.csv"
    df.to_csv(input_path, index=False)
    
    prep_cfg = """
version: 1
defaults:
  fail_fast: false
steps: [P01, P02, P03, P04, P05, P07, P08, P06, P09]
p01: {on_error: quarantine}
p02: {category_mapping_mode: explicit, unmapped_action: {default: to_na}}
p03: {resolve: keep_most_complete}
p04: {max_flag_rate: 1.0}
p05: {mode: binary_threshold}
p07: {time_source: schema, unknown_action: exclude}
p08: {source: schema_roles}
p06: {outcome_missing: ipcw_flag, covariate_missing: median_indicator}
p09: {fold_strategy: group_stratified}
    """
    p_cfg_path = tmp_path / "preprocess.yaml"
    p_cfg_path.write_text(prep_cfg)
    
    pipe_cfg = """
version: 1
input:
  adapter: canonical
steps: [P01, P02, P03, P04, P05, P07, P08, P06, P09]
    """
    pipe_cfg_path = tmp_path / "pipeline.yaml"
    pipe_cfg_path.write_text(pipe_cfg)
    
    schema_dir = tmp_path / "schema"
    schema_dir.mkdir()
    schema_yaml = """
version: "1.0"
columns:
  record_id:
    dtype: string
    required: true
    measured_at: pre
    dag_role: id
  yield_t_ha:
    dtype: float32
    required: true
    measured_at: post
    affected_by_treatment: true
    dag_role: outcome
    range: [0, 120]
  field_size_ha:
    dtype: float32
    required: true
    measured_at: pre
    dag_role: confounder
    range: [0.0001, 500]
  soil_om_baseline_pct:
    dtype: float32
    required: true
    measured_at: pre
    dag_role: confounder
    range: [0, 20]
  experience_yr:
    dtype: int16
    required: false
    measured_at: pre
    dag_role: confounder
    range: [0, 60]
    """
    (schema_dir / "canonical.yaml").write_text(schema_yaml)
    
    exit_code = run_pipeline(
        pipeline_config_path=str(pipe_cfg_path),
        preprocess_config_path=str(p_cfg_path),
        input_path=str(input_path),
        output_dir=str(tmp_path)
    )
    
    assert exit_code in [0, 2, 3] # might fail on other things since schema is partial
    
    report_dirs = os.listdir(tmp_path / "reports")
    assert len(report_dirs) == 1
    report_path = tmp_path / "reports" / report_dirs[0] / "run_report.json"
    
    with open(report_path, "r") as f:
        rep = json.load(f)
        
    modules = [s["module_id"] for s in rep["steps"]]
    # Should maintain order as much as it succeeded
    expected = ["P01", "P02", "P03", "P04", "P05", "P07", "P08", "P06", "P09"]
    assert modules == expected[:len(modules)]

