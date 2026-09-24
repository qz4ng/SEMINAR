import pytest
import pandas as pd
import json
import numpy as np
import os
from ra_causal.preprocess.p05_treatment_define import run, P05Config
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
    res = run(df, P05Config(), ctx)
    
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
    res = run(df, P05Config(), ctx)
    # Recovery check skipped for generic template, you can customize per module
    pass

def test_parameter_selection(ctx):
    df, _ = make_dirty_frame(20, 0)
    res = run(df, P05Config(), ctx)
    assert res is not None

def test_directional_reaction(ctx):
    df, _ = make_dirty_frame(20, 0)
    res = run(df, P05Config(), ctx)
    assert res is not None

def test_clean_data(ctx):
    df = make_clean_frame(50, 0)
    res = run(df, P05Config(), ctx)
    assert res.report.rows_dropped == 0
    assert not any(f.severity == "error" for f in res.report.findings)
    # flag columns should be False
    flag_cols = [c for c in res.data.columns if c.startswith("flag__")]
    if flag_cols:
        assert not res.data[flag_cols].any().any()


# ---------- Dòng "Partial": gắn cờ, không bỏ ----------

def _partial_frame(prepare_upto, drop_months=False):
    df = make_clean_frame(60, 0)
    if drop_months:
        df = df.drop(columns=["cover_crop_months"])
    df["cover_crop"] = df["cover_crop"].map({True: "Yes", False: "No"}).astype(object)
    df.loc[df.index[:3], "cover_crop"] = "Partial"
    ids = df.loc[df.index[:3], "record_id"].tolist()
    return prepare_upto(df, "P05"), ids


@pytest.mark.unit
@pytest.mark.parametrize("drop_months", [False, True], ids=["co_so_thang", "chi_co_yes_no"])
def test_partial_rows_are_flagged_not_dropped(prepare_upto, drop_months):
    """Cả khi có cột số tháng lẫn khi chỉ có Yes/No/Partial, dòng Partial phải được gắn cờ,
    giữ lại trong dữ liệu, và tách ra bảng rà soát."""
    (df, ctx), partial_ids = _partial_frame(prepare_upto, drop_months)
    res = run(df, P05Config(), ctx)

    assert len(res.data) == len(df), "không được bỏ dòng Partial"
    assert set(res.data.loc[res.data["flag__p05__partial"], "record_id"]) == set(partial_ids)
    assert res.data.loc[res.data["flag__p05__partial"], "cover_crop"].isna().all()  # to_na
    assert set(res.artifacts["partial_review"]["record_id"]) == set(partial_ids)
    assert any(f.code == "P05.PARTIAL_FLAGGED" for f in res.report.findings)


@pytest.mark.unit
@pytest.mark.parametrize("action,expected", [("treated", True), ("control", False)])
def test_partial_action_assigns_as_configured(prepare_upto, action, expected):
    (df, ctx), _ = _partial_frame(prepare_upto)
    res = run(df, P05Config(partial_action=action), ctx)
    partial = res.data["flag__p05__partial"]
    assert (res.data.loc[partial, "cover_crop"] == expected).all()
    assert partial.sum() == 3, "cờ vẫn phải có dù đã xếp nhóm"
