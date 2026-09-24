import pandas as pd
import os

def write_data(df: pd.DataFrame, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if path.endswith(".csv"):
        df.to_csv(path, index=False)
    elif path.endswith(".parquet"):
        df.to_parquet(path, index=False)
    else:
        raise ValueError(f"Unsupported file extension for {path}")

