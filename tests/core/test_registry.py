import pytest
from ra_causal.core.registry import PreprocessRegistry
from pydantic import BaseModel

class DummyConfig(BaseModel):
    pass

@pytest.mark.unit
def test_registry():
    registry = PreprocessRegistry()
    
    @registry.register("P00", DummyConfig)
    def dummy_runner(df, cfg, ctx):
        pass

    assert registry.get_runner("P00") == dummy_runner
    assert registry.get_config_class("P00") == DummyConfig
    
    with pytest.raises(ValueError):
        @registry.register("P00", DummyConfig)
        def dummy_runner_2(df, cfg, ctx):
            pass

    with pytest.raises(KeyError):
        registry.get_runner("P99")

