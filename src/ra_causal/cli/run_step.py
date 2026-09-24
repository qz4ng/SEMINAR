import argparse
import sys
import yaml
import json
import os
import pandas as pd
import numpy as np

from ra_causal.core.context import PipelineContext, RunPaths
from ra_causal.core.schema import CanonicalSchema
from ra_causal.core.registry import REGISTRY
from ra_causal.io.loaders import load_data
from ra_causal.io.writers import write_data
from ra_causal.pipeline.steps import run_step
import ra_causal.preprocess  # noqa: F401 — nạp registry

def get_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def set_nested_value(d, path, value):
    keys = path.split('.')
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    
    # Try to cast
    if value.lower() == "true":
        v = True
    elif value.lower() == "false":
        v = False
    elif value.lower() == "null" or value == "None":
        v = None
    else:
        try:
            if "." in value:
                v = float(value)
            else:
                v = int(value)
        except ValueError:
            v = value
            
    d[keys[-1]] = v

def main():
    parser = argparse.ArgumentParser(description="Run a single step.")
    parser.add_argument("step", help="Step module ID (e.g. P04)")
    parser.add_argument("--input", required=True, help="Input data file")
    parser.add_argument("--config", required=True, help="Path to preprocess.yaml")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--set", action="append", help="Override config (e.g. p04.action=winsorize)")
    parser.add_argument("--context", help="Path to context JSON")
    
    args = parser.parse_args()
    
    step_id = args.step.upper()
    
    prep_cfg = get_config(args.config)
    step_cfg_dict = prep_cfg.get(step_id.lower(), {})
    
    if args.set:
        for s in args.set:
            k, v = s.split("=", 1)
            set_nested_value(step_cfg_dict, k.replace(f"{step_id.lower()}.", ""), v)
            
    # Tra registry TRƯỚC khi làm gì khác, và báo lỗi tử tế thay vì để KeyError bay ra.
    if step_id not in REGISTRY:
        print(f"Lỗi: không có module {step_id} trong registry. Các mã hợp lệ: {REGISTRY.available()}")
        sys.exit(1)

    config_cls = REGISTRY.get_config_class(step_id)
    try:
        step_cfg = config_cls(**step_cfg_dict)
    except Exception as e:
        print(f"Config error: {e}")
        sys.exit(1)
        
    schema_path = os.path.join(os.path.dirname(args.config), "schema/canonical.yaml")
    schema = CanonicalSchema.load(schema_path)
    
    ctx = PipelineContext(
        run_id="manual",
        schema=schema,
        rng=np.random.default_rng(20260921),
        paths=RunPaths(args.output, args.output, args.output)
    )
    
    if args.context:
        with open(args.context, "r", encoding="utf-8") as f:
            cdata = json.load(f)
            for k, v in cdata.items():
                setattr(ctx, k, v)
                
    try:
        df = pd.read_parquet(args.input) if args.input.endswith(".parquet") else pd.read_csv(args.input)
    except Exception as e:
        print(f"Failed to load data: {e}")
        sys.exit(1)
        
    runner = REGISTRY.get_runner(step_id)

    try:
        res = run_step(step_id, runner, step_cfg, df, ctx)
        write_data(res.data, os.path.join(args.output, f"after_{step_id}.parquet"))
        print(f"Step {step_id} finished with status {res.report.status}")
    except Exception as e:
        print(f"Step {step_id} failed: {e}")
        sys.exit(2)
        
if __name__ == "__main__":
    main()

