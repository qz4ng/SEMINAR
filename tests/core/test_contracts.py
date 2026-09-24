import pytest
import numpy as np
import pandas as pd
from ra_causal.core.contracts import StepReport, Finding
from ra_causal.utils.pandas_tools import jsonify

@pytest.mark.unit
def test_jsonify():
    data = {
        "a": np.int64(42),
        "b": np.float64(3.14),
        "c": np.nan,
        "d": pd.Timestamp("2026-09-21 12:00:00"),
        "e": pd.Categorical(["x", "y"]),
        "f": {1, 2, 3}
    }
    result = jsonify(data)
    assert result["a"] == 42
    assert isinstance(result["a"], int)
    assert result["b"] == 3.14
    assert result["c"] is None
    assert result["d"] == "2026-09-21T12:00:00"
    assert result["e"] == ["x", "y"]
    assert result["f"] == [1, 2, 3]

@pytest.mark.unit
def test_step_report_to_dict():
    finding = Finding(code="P01.TEST", severity="info", message="Test", count=1)
    report = StepReport(
        module_id="P01",
        module_name="test",
        spec_version="1.0",
        status="ok",
        started_at="2026-09-21T12:00:00",
        duration_s=1.234,
        n_rows_in=100,
        n_rows_out=100,
        n_cols_in=10,
        n_cols_out=10,
        rows_dropped=0,
        rows_flagged=0,
        columns_added=[],
        columns_modified=[],
        params_effective={"p1": 1},
        findings=[finding],
        artifacts={},
        context_updates=[]
    )
    d = report.to_dict()
    assert d["module_id"] == "P01"
    assert d["status"] == "ok"
    assert len(d["findings"]) == 1
    assert d["findings"][0]["code"] == "P01.TEST"

