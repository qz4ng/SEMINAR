import pytest
from ra_causal.core.errors import RaCausalError, ConfigError, DataQualityError

@pytest.mark.unit
def test_errors():
    err = ConfigError(module_id="P01", code="P01.TEST", message="Test message", details={"k": "v"})
    assert err.module_id == "P01"
    assert err.code == "P01.TEST"
    assert err.message == "Test message"
    assert err.details == {"k": "v"}
    assert isinstance(err, RaCausalError)
    assert isinstance(err, Exception)

