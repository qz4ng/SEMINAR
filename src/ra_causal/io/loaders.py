import pandas as pd
import os
from .adapters import ADAPTERS

def load_data(path: str, adapter_name: str, schema_version: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Input file not found: {path}")
    
    if path.endswith(".csv"):
        df = pd.read_csv(path)
    elif path.endswith(".parquet"):
        df = pd.read_parquet(path)
    else:
        raise ValueError(f"Unsupported file extension for {path}")
    
    if adapter_name not in ADAPTERS:
        raise ValueError(f"Unknown adapter: {adapter_name}")
    
    return ADAPTERS[adapter_name](df, schema_version)

