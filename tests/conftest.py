import os
import sys

import numpy as np
import pytest
import yaml

# Add src to path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from ra_causal.core.context import PipelineContext, RunPaths  # noqa: E402
from ra_causal.core.registry import REGISTRY  # noqa: E402
from ra_causal.core.schema import CanonicalSchema  # noqa: E402
import ra_causal.preprocess  # noqa: E402,F401  — nạp registry

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCHEMA_PATH = os.path.join(ROOT, "configs", "schema", "canonical.yaml")
PREPROCESS_CONFIG_PATH = os.path.join(ROOT, "configs", "preprocess.yaml")

# Thứ tự chạy chính thức, dùng lại trong test thay vì chép tay ở từng file
PIPELINE_ORDER = ["P01", "P02", "P03", "P04", "P05", "P07", "P08", "P06", "P09"]


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: mark test as a unit test.")
    config.addinivalue_line("markers", "integration: mark test as an integration test.")


@pytest.fixture
def schema():
    return CanonicalSchema.load(SCHEMA_PATH)


@pytest.fixture
def default_config():
    """Toàn bộ configs/preprocess.yaml — để test chạy đúng mặc định mà người dùng thấy."""
    with open(PREPROCESS_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def make_ctx(tmp_path, schema):
    """Tạo PipelineContext rỗng cho test chạy module độc lập."""
    def _make():
        paths = RunPaths(
            interim=str(tmp_path / "interim"),
            processed=str(tmp_path / "processed"),
            reports=str(tmp_path / "reports"),
        )
        return PipelineContext(run_id="test", schema=schema, rng=np.random.default_rng(0), paths=paths)
    return _make


@pytest.fixture
def prepare_upto(make_ctx, default_config):
    """Chạy các module ĐỨNG TRƯỚC một module, trả về (df, ctx) đã sẵn sàng cho nó.

    Module không chạy trong chân không: P04 giả định P02 đã quy đổi đơn vị, P06 giả định
    P08 đã dựng L… Test nào nạp thẳng dữ liệu thô vào module giữa chuỗi là đang kiểm tra
    một tình huống không tồn tại trong luồng thật.
    """
    def _prepare(df, target: str, overrides: dict | None = None):
        ctx = make_ctx()
        cfg_all = dict(default_config)
        if overrides:
            for step_id, params in overrides.items():
                cfg_all[step_id.lower()] = {**cfg_all.get(step_id.lower(), {}), **params}

        for step_id in PIPELINE_ORDER:
            if step_id == target:
                break
            runner = REGISTRY.get_runner(step_id)
            config_cls = REGISTRY.get_config_class(step_id)
            res = runner(df, config_cls(**cfg_all.get(step_id.lower(), {})), ctx)
            df = res.data
            for key, value in res.context_updates.items():
                setattr(ctx, key, value)
                ctx._written.add(key)
        return df, ctx
    return _prepare
