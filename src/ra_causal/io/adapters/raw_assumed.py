import pandas as pd
import yaml
import os

def adapt(df: pd.DataFrame, schema_version: str) -> pd.DataFrame:
    """
    Adapter for raw_assumed format.
    Loads raw_assumed.yaml and renames columns based on aliases.
    """
    # Load yaml
    config_path = os.path.join(os.path.dirname(__file__), "../../../configs/schema/raw_assumed.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    aliases = config.get("column_aliases", {})
    if aliases:
        df = df.rename(columns=aliases)
    
    return df

