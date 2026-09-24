"""Chuỗi P01→P09 chạy trên dữ liệu bẩn: kết quả có dùng được cho bước nhân quả không."""
import numpy as np
import pandas as pd
import pytest

from ra_causal.core.registry import REGISTRY
from tests.conftest import PIPELINE_ORDER
from tests.fixtures.make_frames import make_clean_frame, make_dirty_frame


def _run_chain(df, make_ctx, default_config):
    ctx = make_ctx()
    reports = []
    for step_id in PIPELINE_ORDER:
        runner = REGISTRY.get_runner(step_id)
        config_cls = REGISTRY.get_config_class(step_id)
        res = runner(df, config_cls(**default_config.get(step_id.lower(), {})), ctx)
        df = res.data
        reports.append(res.report)
        for key, value in res.context_updates.items():
            setattr(ctx, key, value)
            ctx._written.add(key)
    return df, ctx, reports


@pytest.mark.integration
def test_chain_produces_analysis_ready_frame(make_ctx, default_config):
    raw, truth = make_dirty_frame(300, 0)
    out, ctx, reports = _run_chain(raw, make_ctx, default_config)

    assert len(out) <= len(raw), "chuỗi không được sinh thêm dòng"

    # Sau P03 chỉ còn trùng ở các nhóm MÂU THUẪN: mặc định conflict_action=review_list
    # giữ nguyên mọi dòng để người xem, vì khác nhau ở A hoặc Y là dấu hiệu lỗi ghép bảng
    # chứ không phải trùng lặp thuần túy.
    still_dup = out[out["record_id"].duplicated(keep=False)]
    assert still_dup.empty or still_dup["flag__p03__conflict"].all(), \
        "dòng trùng còn lại phải được đánh dấu là mâu thuẫn, không được im lặng"
    assert not out["country"].isna().any()
    assert set(out["country"].dropna().astype(str).unique()) <= {"C1", "C2", "C3", "C4"}
    assert out["cluster_id"].notna().all()
    assert "c_outcome_observed" in out.columns


@pytest.mark.integration
def test_chain_never_lets_post_treatment_vars_into_adjustment_set(make_ctx, default_config):
    """Bất biến quan trọng nhất của cả khối: L không được chứa biến đo sau can thiệp."""
    raw, _ = make_dirty_frame(200, 0)
    _, ctx, _ = _run_chain(raw, make_ctx, default_config)

    forbidden = {"soil_om_post_pct", "weed_pressure", "in_program", "yield_t_ha",
                 "cover_crop", "buyer_incentive"}
    assert forbidden.isdisjoint(set(ctx.adjustment_set)), \
        f"biến cấm lọt vào L: {sorted(forbidden & set(ctx.adjustment_set))}"
    assert not any(c.startswith("noise_") for c in ctx.adjustment_set)
    assert set(ctx.adjustment_set).isdisjoint(set(ctx.blocked_columns))


@pytest.mark.integration
def test_chain_folds_respect_clusters(make_ctx, default_config):
    raw, _ = make_dirty_frame(200, 0)
    out, _, _ = _run_chain(raw, make_ctx, default_config)

    assigned = out[out["fold_id"] >= 0]
    folds_per_cluster = assigned.groupby("cluster_id")["fold_id"].nunique()
    assert (folds_per_cluster <= 1).all(), "một nông hộ không được nằm ở hai fold"


@pytest.mark.integration
def test_chain_on_clean_data_changes_nothing_substantive(make_ctx, default_config):
    """Dữ liệu sạch đi qua cả chuỗi: không mất dòng, không cờ nào bật."""
    clean = make_clean_frame(150, 0)
    out, ctx, reports = _run_chain(clean, make_ctx, default_config)

    assert len(out) == len(clean), "không được loại dòng nào của dữ liệu sạch"
    assert sum(r.rows_dropped for r in reports) == 0

    quality_flags = [c for c in out.columns
                     if c.startswith(("flag__p01__", "flag__p02__", "flag__p03__", "flag__p04__"))]
    assert not out[quality_flags].any().any(), \
        f"cờ chất lượng bật trên dữ liệu sạch: {[c for c in quality_flags if out[c].any()]}"

    assert not any(f.severity == "error" for r in reports for f in r.findings)
    pd.testing.assert_series_equal(
        out["yield_t_ha"].astype(float), clean["yield_t_ha"].astype(float),
        check_names=False, check_dtype=False)


@pytest.mark.integration
def test_chain_is_deterministic(make_ctx, default_config):
    raw, _ = make_dirty_frame(150, 0)
    out_a, ctx_a, _ = _run_chain(raw, make_ctx, default_config)
    out_b, ctx_b, _ = _run_chain(raw, make_ctx, default_config)

    pd.testing.assert_frame_equal(out_a, out_b, check_like=True)
    assert ctx_a.adjustment_set == ctx_b.adjustment_set
    assert np.array_equal(out_a["fold_id"].to_numpy(), out_b["fold_id"].to_numpy())
