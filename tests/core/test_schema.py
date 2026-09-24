import pytest
from ra_causal.core.schema import CanonicalSchema, ColumnContract
import pydantic

@pytest.mark.unit
def test_schema_load(tmp_path):
    yaml_content = """
version: "1.0"
columns:
  test_col:
    dtype: "int16"
    required: true
    measured_at: "pre"
    dag_role: "confounder"
    """
    p = tmp_path / "schema.yaml"
    p.write_text(yaml_content)
    
    schema = CanonicalSchema.load(str(p))
    assert schema.version == "1.0"
    assert "test_col" in schema.columns
    assert schema.columns["test_col"].dtype == "int16"
    assert schema.columns["test_col"].required is True

@pytest.mark.unit
def test_schema_affected_by_treatment_validation():
    with pytest.raises(pydantic.ValidationError, match="affected_by_treatment is required"):
        ColumnContract(
            dtype="float32",
            required=False,
            measured_at="post",
            dag_role="outcome",
        )
        
    with pytest.raises(pydantic.ValidationError, match="affected_by_treatment must not be set"):
        ColumnContract(
            dtype="float32",
            required=False,
            measured_at="pre",
            dag_role="confounder",
            affected_by_treatment=False
        )

