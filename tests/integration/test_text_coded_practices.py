"""Bản xuất khảo sát ghi practice dạng chữ (Yes/No/Partial, Có/Không) — đúng như mô tả bài toán CIAT.

Trước bản sửa: P01 cách ly 120/120 dòng, P02–P07 báo "ok" trên bảng rỗng, pipeline chết ở P08.
"""
import pandas as pd
import pytest

from ra_causal.core.registry import REGISTRY
from tests.conftest import PIPELINE_ORDER
from tests.fixtures.make_frames import make_clean_frame


@pytest.mark.integration
def test_yes_no_partial_survives_the_whole_chain(make_ctx, default_config):
    df = make_clean_frame(120, 0)
    df["cover_crop"] = df["cover_crop"].map({True: "Yes", False: "No"}).astype(object)
    df.loc[df.index[:4], "cover_crop"] = "Partial"
    df["irrigation"] = df["irrigation"].map({True: "Có", False: "Không"}).astype(object)
    partial_ids = set(df.loc[df.index[:4], "record_id"])

    ctx = make_ctx()
    for step_id in PIPELINE_ORDER:
        res = REGISTRY.get_runner(step_id)(df, REGISTRY.get_config_class(step_id)(
            **default_config.get(step_id.lower(), {})), ctx)
        assert len(res.data) == len(df), f"{step_id} làm mất dòng"
        df = res.data
        for k, v in res.context_updates.items():
            setattr(ctx, k, v)
            ctx._written.add(k)

    assert len(df) == 120
    assert set(df.loc[df["flag__p05__partial"], "record_id"]) == partial_ids
    assert set(df["irrigation"].dropna()) <= {True, False}
    assert not df["irrigation"].isna().any(), "Có/Không phải được ánh xạ hết"
    assert ctx.adjustment_set, "phải dựng được tập điều chỉnh L"
