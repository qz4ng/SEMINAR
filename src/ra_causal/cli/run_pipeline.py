import argparse
import sys
from ra_causal.pipeline.runner import run_pipeline

def main():
    parser = argparse.ArgumentParser(description="Run the ra_causal preprocessing pipeline.")
    parser.add_argument("--config", required=True, help="Path to pipeline.yaml")
    parser.add_argument("--input", required=True, help="Path to input data file")
    parser.add_argument("--output", required=True, help="Path to output directory")
    parser.add_argument("--steps", help="Comma-separated list of steps to run")
    parser.add_argument("--from", dest="start_step", help="Step to start from")
    parser.add_argument("--to", dest="end_step", help="Step to end at")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    
    args = parser.parse_args()
    
    steps_list = args.steps.split(",") if args.steps else None
    
    # We assume preprocess_config is in the same dir as pipeline config or relative
    # Actually just assume it's configs/preprocess.yaml
    prep_config = args.config.replace("pipeline.yaml", "preprocess.yaml")
    
    exit_code = run_pipeline(
        pipeline_config_path=args.config,
        preprocess_config_path=prep_config,
        input_path=args.input,
        output_dir=args.output,
        steps=steps_list,
        start_step=args.start_step,
        end_step=args.end_step,
        dry_run=args.dry_run
    )
    sys.exit(exit_code)

if __name__ == "__main__":
    main()

