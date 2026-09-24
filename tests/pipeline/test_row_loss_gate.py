"""Cổng an toàn: một bước làm mất quá nhiều dòng phải dừng NGAY tại bước đó."""
import numpy as np
import pytest

from ra_causal.core.context import PipelineContext, RunPaths
from ra_causal.core.errors import DataQualityError
from ra_causal.core.registry import REGISTRY
from ra_causal.pipeline.steps import run_step
from tests.fixtures.make_frames import make_clean_frame


def _garbage_frame(n_bad):
    df = make_clean_frame(80, 0)
    df["temp_longterm_c"] = df["temp_longterm_c"].astype(object)
    df.loc[df.index[:n_bad], "temp_longterm_c"] = "abc"
    return df


def _ctx(schema, tmp_path):
    return PipelineContext(run_id="t", schema=schema, rng=np.random.default_rng(0),
                           paths=RunPaths(str(tmp_path), str(tmp_path), str(tmp_path)))


@pytest.mark.unit
def test_excessive_row_loss_blocks_at_the_step(schema, tmp_path, default_config):
    cfg = REGISTRY.get_config_class("P01")(**default_config["p01"])
    with pytest.raises(DataQualityError) as err:
        run_step("P01", REGISTRY.get_runner("P01"), cfg, _garbage_frame(40), _ctx(schema, tmp_path),
                 max_row_loss=0.20)
    e = err.value
    assert e.code == "P01.EXCESSIVE_ROW_LOSS"
    assert e.details["rows_in"] == 80 and e.details["rows_out"] == 40
    # Thông báo phải chỉ ra nguyên nhân, không chỉ nói "mất dòng"
    assert e.details["top_findings"][0]["code"] == "P01.COERCE_FAILED"
    assert "quarantine" in e.result.artifacts, "artifact vẫn phải giữ lại để xem vì sao"


@pytest.mark.unit
def test_small_row_loss_passes_and_gate_can_be_disabled(schema, tmp_path, default_config):
    cfg = REGISTRY.get_config_class("P01")(**default_config["p01"])
    runner = REGISTRY.get_runner("P01")
    res = run_step("P01", runner, cfg, _garbage_frame(2), _ctx(schema, tmp_path), max_row_loss=0.20)
    assert len(res.data) == 78

    res = run_step("P01", runner, cfg, _garbage_frame(40), _ctx(schema, tmp_path), max_row_loss=None)
    assert len(res.data) == 40
