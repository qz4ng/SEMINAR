"""Hai tính chất bắt buộc với MỌI module: chạy lại không đổi, và tái lập được.

Viết một lần, chạy qua cả chín module, thay vì lặp lại ở từng file test.
"""
import pandas as pd
import pytest

from ra_causal.core.registry import REGISTRY
from tests.conftest import PIPELINE_ORDER
from tests.fixtures.make_frames import make_dirty_frame


def _run_module(module_id, prepare_upto, overrides=None):
    raw, _ = make_dirty_frame(80, 0)
    df, ctx = prepare_upto(raw, module_id, overrides)
    runner = REGISTRY.get_runner(module_id)
    config_cls = REGISTRY.get_config_class(module_id)
    cfg = config_cls(**(overrides or {}).get(module_id, {}))
    return df, ctx, runner, cfg


# P04 gắn cờ nhiều trên khung bẩn; nới ngưỡng để kiểm tra tính chất chứ không kiểm tra cổng chặn
OVERRIDES = {"P04": {"max_flag_rate": 1.0}}


@pytest.mark.unit
@pytest.mark.parametrize("module_id", PIPELINE_ORDER)
def test_module_is_idempotent(module_id, prepare_upto):
    """Chạy hai lần liên tiếp phải cho kết quả giống chạy một lần."""
    df, ctx, runner, cfg = _run_module(module_id, prepare_upto, OVERRIDES)

    once = runner(df, cfg, ctx).data
    twice = runner(once, cfg, ctx).data

    pd.testing.assert_frame_equal(once, twice, check_like=True)


@pytest.mark.unit
@pytest.mark.parametrize("module_id", PIPELINE_ORDER)
def test_module_is_deterministic(module_id, prepare_upto):
    """Cùng dữ liệu, cùng config, cùng seed -> cùng dữ liệu ra và cùng báo cáo."""
    df_a, ctx_a, runner, cfg = _run_module(module_id, prepare_upto, OVERRIDES)
    df_b, ctx_b, _, _ = _run_module(module_id, prepare_upto, OVERRIDES)

    res_a = runner(df_a, cfg, ctx_a)
    res_b = runner(df_b, cfg, ctx_b)

    pd.testing.assert_frame_equal(res_a.data, res_b.data, check_like=True)

    rep_a, rep_b = res_a.report.to_dict(), res_b.report.to_dict()
    for volatile in ("started_at", "duration_s"):
        rep_a.pop(volatile, None)
        rep_b.pop(volatile, None)
    assert rep_a == rep_b


@pytest.mark.unit
@pytest.mark.parametrize("module_id", PIPELINE_ORDER)
def test_module_does_not_mutate_input(module_id, prepare_upto):
    df, ctx, runner, cfg = _run_module(module_id, prepare_upto, OVERRIDES)
    before = df.copy()
    runner(df, cfg, ctx)
    pd.testing.assert_frame_equal(df, before)


@pytest.mark.unit
@pytest.mark.parametrize("module_id", PIPELINE_ORDER)
def test_module_report_is_json_serializable_and_sorted(module_id, prepare_upto):
    import json

    df, ctx, runner, cfg = _run_module(module_id, prepare_upto, OVERRIDES)
    report = runner(df, cfg, ctx).report

    json.dumps(report.to_dict())  # không được chứa numpy/Timestamp/NaN
    assert report.module_id == module_id
    # Danh sách trong báo cáo phải có thứ tự xác định, nếu không golden run sẽ nhiễu
    assert report.columns_added == sorted(report.columns_added)
