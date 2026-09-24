import pandas as pd
import numpy as np
import json
from typing import Any

def to_schema_dtype(series: pd.Series, dtype: str) -> pd.Series:
    """Map schema dtype to pandas nullable dtype."""
    if dtype == "int8":
        return series.astype("Int8")
    elif dtype == "int16":
        return series.astype("Int16")
    elif dtype == "float32":
        return series.astype("Float32") # Use Float32 for consistency
    elif dtype == "boolean":
        return series.astype("boolean")
    elif dtype == "string":
        return series.astype("string")
    elif dtype == "category":
        return series.astype("category")
    else:
        return series.astype(dtype)

def jsonify(obj: Any) -> Any:
    """Recursively converts an object into a JSON-serializable format."""
    if obj is None:
        return None
    if isinstance(obj, (int, float, str, bool)):
        if isinstance(obj, float) and np.isnan(obj):
            return None
        return obj
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        if np.isnan(obj):
            return None
        return float(obj)
    if isinstance(obj, np.ndarray):
        return [jsonify(item) for item in obj.tolist()]
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, pd.Categorical):
        return [jsonify(item) for item in obj.tolist()]
    if isinstance(obj, dict):
        return {str(k): jsonify(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [jsonify(item) for item in obj]
    if isinstance(obj, tuple):
        return [jsonify(item) for item in obj]
    if isinstance(obj, set):
        return [jsonify(item) for item in sorted(list(obj))]
    
    # Try to convert custom classes with to_dict if possible
    if hasattr(obj, "to_dict") and callable(getattr(obj, "to_dict")):
        return jsonify(obj.to_dict())
    
    return str(obj)

