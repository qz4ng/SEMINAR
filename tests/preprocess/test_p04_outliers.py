import pytest
import pandas as pd
import json
import numpy as np
import os
import dataclasses
from ra_causal.preprocess.p04_outliers import run, P04Config
from tests.fixtures.make_frames import make_dirty_frame, make_clean_frame
from ra_causal.core.context import PipelineContext, RunPaths
from ra_causal.core.schema import CanonicalSchema

@pytest.fixture
def ctx(tmp_path):
    schema = CanonicalSchema.load(os.path.join(os.path.dirname(__file__), "../../configs/schema/canonical.yaml"))
    paths = RunPaths(
        interim=str(tmp_path / "interim"),
        processed=str(tmp_path / "processed"),
        reports=str(tmp_path / "reports")
    )
    ctx = PipelineContext(run_id="test", schema=schema, rng=np.random.default_rng(0), paths=paths)
    ctx._written = {"eligible_columns", "adjustment_set"}
    ctx.adjustment_set = ["soil_om_baseline_pct", "experience_yr"]
    ctx.eligible_columns = ["soil_om_baseline_pct", "experience_yr", "yield_t_ha", "cover_crop"]
    ctx.outcome_observed_column = "c_outcome_observed"
    ctx.treatment_column = "cover_crop"
    return ctx

def test_contract(ctx):
    df, _ = make_dirty_frame(20, 0)
    df_before = df.copy()
    res = run(df, P04Config(max_flag_rate=1.0), ctx)
    assert hasattr(res, "data")
    assert hasattr(res, "report")
    d = dataclasses.asdict(res.report) if dataclasses.is_dataclass(res.report) else res.report.model_dump()
    json.dumps(d)
    pd.testing.assert_frame_equal(df, df_before)

def test_recovery(prepare_upto):
    """Phải tìm lại ĐÚNG các outlier đã cài, sau khi P02 đã quy đổi đơn vị."""
    raw, truth = make_dirty_frame(100, 0)
    df, ctx = prepare_upto(raw, "P04")
    res = run(df, P04Config(method="domain_range", max_flag_rate=1.0), ctx)

    flagged = set(res.data.loc[res.data["flag__p04__any"], "record_id"])
    expected = set(truth.get("outliers", [])) & set(df["record_id"])
    assert expected, "khung dữ liệu bẩn phải có outlier đã cài"
    assert expected.issubset(flagged), f"bỏ sót outlier: {sorted(expected - flagged)}"

    # Các dòng ghi kg/ha đã được P02 quy đổi (có cột yield_unit) nên KHÔNG còn bất thường:
    # đây chính là lý do P02 phải chạy trước P04.
    unit_mix = set(truth.get("unit_mix", [])) & set(df["record_id"])
    assert unit_mix, "khung dữ liệu bẩn phải có dòng ghi sai đơn vị"
    assert not (unit_mix & flagged), "dòng đã quy đổi đơn vị không được coi là outlier"

    # Mọi cờ còn lại phải giải thích được (outlier cài sẵn hoặc lỗi schema như yield = -10)
    schema_errors = set(truth.get("schema_errors", []))
    assert not (flagged - expected - schema_errors)


def test_recovery_without_unit_info_marks_suspected_unit_error(prepare_upto):
    """Không có cột đơn vị thì P02 không được tự quy đổi; P04 phải nhận ra là NGHI LỖI ĐƠN VỊ."""
    from tests.fixtures.make_frames import inject_unit_mix, make_clean_frame

    raw, unit_mix = inject_unit_mix(make_clean_frame(100, 0), frac=0.1, seed=1, declare_unit=False)
    df, ctx = prepare_upto(raw, "P04")
    res = run(df, P04Config(method="domain_range", max_flag_rate=1.0), ctx)

    suspect_col = "flag__p04__suspected_unit_error__yield_t_ha"
    assert suspect_col in res.data.columns
    suspected = set(res.data.loc[res.data[suspect_col], "record_id"])
    assert set(unit_mix).issubset(suspected)


def test_parameter_selection(prepare_upto):
    raw, _ = make_dirty_frame(50, 0)
    df, ctx = prepare_upto(raw, "P04")
    res_flag = run(df, P04Config(action="flag_only", max_flag_rate=1.0), ctx)
    assert len(res_flag.data) == len(df)
    
    res_drop = run(df, P04Config(action="drop_row", max_flag_rate=1.0), ctx)
    assert len(res_drop.data) == len(df) - res_drop.report.rows_dropped

    res_win = run(df, P04Config(action="winsorize", method="domain_range", max_flag_rate=1.0), ctx)
    assert len(res_win.data) == len(df)
    
    res_na = run(df, P04Config(action="to_na", max_flag_rate=1.0), ctx)
    na_diff = res_na.data["yield_t_ha"].isna().sum() - df["yield_t_ha"].isna().sum()
    assert na_diff >= 0

def test_directional_reaction(ctx):
    df, _ = make_dirty_frame(100, 0)
    res1 = run(df, P04Config(robust_z_threshold=2.0, max_flag_rate=1.0), ctx)
    res2 = run(df, P04Config(robust_z_threshold=10.0, max_flag_rate=1.0), ctx)
    assert res2.report.rows_flagged <= res1.report.rows_flagged

def test_clean_data(ctx):
    df = make_clean_frame(50, 0)
    res = run(df, P04Config(max_flag_rate=1.0), ctx)
    assert res.report.rows_dropped == 0
    assert not any(f.severity == "error" for f in res.report.findings)
    flag_cols = [c for c in res.data.columns if c.startswith("flag__")]
    if flag_cols:
        assert not res.data[flag_cols].any().any()
