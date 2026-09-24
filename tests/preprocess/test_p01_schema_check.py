import pytest
import pandas as pd
import json
import numpy as np
import os
from ra_causal.preprocess.p01_schema_check import run, P01Config
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
    res = run(df, P01Config(), ctx)
    
    # Check returns StepResult
    assert hasattr(res, "data")
    assert hasattr(res, "report")
    
    # Check report serialization
    # if it's a dataclass, asdict
    import dataclasses
    try:
        if dataclasses.is_dataclass(res.report):
            d = dataclasses.asdict(res.report)
        else:
            d = res.report.model_dump()
        json.dumps(d)
    except Exception as e:
        pytest.fail(f"Report not serializable: {e}")
        
    # Check no mutation
    pd.testing.assert_frame_equal(df, df_before)

def test_recovery(ctx):
    df, truth = make_dirty_frame(100, 0)
    res = run(df, P01Config(), ctx)
    # Recovery check skipped for generic template, you can customize per module
    pass

def test_parameter_selection(ctx):
    df, _ = make_dirty_frame(20, 0)
    res = run(df, P01Config(), ctx)
    assert res is not None

def test_directional_reaction(ctx):
    df, _ = make_dirty_frame(20, 0)
    res = run(df, P01Config(), ctx)
    assert res is not None

def test_clean_data(ctx):
    df = make_clean_frame(50, 0)
    res = run(df, P01Config(), ctx)
    assert res.report.rows_dropped == 0
    assert not any(f.severity == "error" for f in res.report.findings)
    # flag columns should be False
    flag_cols = [c for c in res.data.columns if c.startswith("flag__")]
    if flag_cols:
        assert not res.data[flag_cols].any().any()


# ---------- Cột nhị phân ghi dạng chữ (Yes/No/Partial, Có/Không) ----------

def _text_coded(n=40):
    df = make_clean_frame(n, 0)
    df["cover_crop"] = df["cover_crop"].map({True: "Yes", False: "No"}).astype(object)
    df.loc[df.index[:3], "cover_crop"] = "Partial"
    df["irrigation"] = df["irrigation"].map({True: "Có", False: "Không"}).astype(object)
    return df


@pytest.mark.unit
def test_text_coded_binary_is_deferred_not_quarantined(ctx):
    """Chữ trong cột nhị phân là việc của P02, không phải lỗi dòng.

    Lỗi thật đã xảy ra: P01 cách ly 120/120 dòng vì "Yes" không ép được sang boolean.
    """
    df = _text_coded()
    res = run(df, P01Config(), ctx)

    assert len(res.data) == len(df), "không được cách ly dòng chỉ vì cột nhị phân ghi dạng chữ"
    assert "quarantine" not in res.artifacts or len(res.artifacts["quarantine"]) == 0
    deferred = [f for f in res.report.findings if f.code == "P01.DEFERRED_TO_P02"]
    assert deferred and {"cover_crop", "irrigation"} <= set(deferred[0].details["columns"])
    # Giá trị gốc được giữ nguyên cho P02 ánh xạ
    assert set(res.data["cover_crop"].dropna()) == {"Yes", "No", "Partial"}


@pytest.mark.unit
def test_garbage_in_numeric_column_is_still_a_row_error(ctx):
    """Nới lỏng cho cột nhị phân KHÔNG được làm nới lỏng cột số: "abc" trong cột số vẫn là lỗi."""
    df = make_clean_frame(40, 0)
    df["temp_longterm_c"] = df["temp_longterm_c"].astype(object)
    df.loc[df.index[0], "temp_longterm_c"] = "abc"
    res = run(df, P01Config(), ctx)
    assert len(res.data) == len(df) - 1
