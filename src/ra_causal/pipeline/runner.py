import pandas as pd
import time
import os
import sys
import json
from typing import Optional
import yaml
import numpy as np

from ra_causal.core.context import PipelineContext, RunPaths
from ra_causal.core.schema import CanonicalSchema
from ra_causal.core.registry import REGISTRY
from ra_causal.core.errors import DataQualityError, RaCausalError, ContractError, ConfigError
from ra_causal.core.logging import get_logger
from ra_causal.io.loaders import load_data
from ra_causal.io.writers import write_data
from ra_causal.core.reporting import write_run_report
from ra_causal.core.contracts import StepReport, Finding
from ra_causal.pipeline.steps import run_step

def get_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def _module_name(runner) -> str:
    """Tên nghiệp vụ của module (vd 'outliers'), lấy từ hằng MODULE_NAME trong file module."""
    mod = sys.modules.get(getattr(runner, "__module__", ""), None)
    return getattr(mod, "MODULE_NAME", "") if mod else ""

def _failure_report(step_id: str, module_name: str, status: str, code: str, message: str,
                    details: dict, df: pd.DataFrame, started_at: str, duration_s: float,
                    params: dict) -> StepReport:
    """Dựng StepReport cho một bước hỏng.

    Bước hỏng vẫn phải có mặt trong run_report.json với đúng cấu trúc như mọi bước khác:
    đó chính là lúc người đọc cần báo cáo nhất.
    """
    return StepReport(
        module_id=step_id,
        module_name=module_name,
        spec_version="1.0",
        status=status,
        started_at=started_at,
        duration_s=round(duration_s, 3),
        n_rows_in=len(df),
        n_rows_out=0,
        n_cols_in=len(df.columns),
        n_cols_out=0,
        rows_dropped=0,
        rows_flagged=0,
        columns_added=[],
        columns_modified=[],
        params_effective=params,
        findings=[Finding(
            code=code,
            severity="blocking" if status == "blocked" else "error",
            message=message,
            count=0,
            details=details or {},
        )],
        artifacts={},
        context_updates=[],
    )

import ra_causal.preprocess  # noqa: F401

def run_pipeline(
    pipeline_config_path: str,
    preprocess_config_path: str,
    input_path: str,
    output_dir: str,
    steps: Optional[list[str]] = None,
    start_step: Optional[str] = None,
    end_step: Optional[str] = None,
    dry_run: bool = False
):
    logger = get_logger("runner")
    
    pipe_cfg = get_config(pipeline_config_path)
    prep_cfg = get_config(preprocess_config_path)
    
    run_id = time.strftime("%Y%m%d-%H%M%S-") + os.urandom(4).hex()
    started_at = pd.Timestamp.utcnow()
    start_time = time.time()
    
    # Resolve steps
    all_steps = pipe_cfg.get("steps", prep_cfg.get("steps", []))
    if steps:
        run_steps = steps
    else:
        run_steps = all_steps
        if start_step:
            if start_step in run_steps:
                run_steps = run_steps[run_steps.index(start_step):]
        if end_step:
            if end_step in run_steps:
                run_steps = run_steps[:run_steps.index(end_step)+1]

    # Load schema
    schema_path = os.path.join(os.path.dirname(preprocess_config_path), "schema/canonical.yaml")
    schema = CanonicalSchema.load(schema_path)
    
    # Context
    paths = RunPaths(
        interim=os.path.join(output_dir, "interim", run_id),
        processed=os.path.join(output_dir, "processed", run_id),
        reports=os.path.join(output_dir, "reports", run_id)
    )
    if not dry_run:
        os.makedirs(paths.interim, exist_ok=True)
        os.makedirs(paths.processed, exist_ok=True)
        os.makedirs(paths.reports, exist_ok=True)
        
    seed = prep_cfg.get("defaults", {}).get("seed", 20260921)
    rng = np.random.default_rng(seed)
    
    ctx = PipelineContext(
        run_id=run_id,
        schema=schema,
        rng=rng,
        paths=paths
    )
    
    # Load data
    adapter = pipe_cfg.get("input", {}).get("adapter", "canonical")
    
    try:
        df = load_data(input_path, adapter, schema.version)
        if dry_run:
            df = df.head(1000)
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return 1
        
    input_info = {
        "path": input_path,
        "n_rows": len(df),
        "n_cols": len(df.columns),
        "adapter": adapter
    }
    
    # Merge defaults into configs
    defaults = prep_cfg.get("defaults", {})
    
    step_reports = []
    status_final = "ok"
    failed_step = None
    exit_code = 0
    fail_fast = defaults.get("fail_fast", True)
    # Cổng an toàn: tỷ lệ dòng tối đa một bước được phép loại (None = tắt)
    max_row_loss = defaults.get("max_row_loss_per_step", 0.20)
    
    for step_id in run_steps:
        if step_id not in all_steps:
            logger.error(f"Unknown step {step_id}")
            return 1
            
        step_logger = get_logger(step_id)
        step_logger.info(f"Running {step_id}")
        
        try:
            runner = REGISTRY.get_runner(step_id)
            config_cls = REGISTRY.get_config_class(step_id)
        except KeyError:
            logger.error(f"Không có module {step_id} trong registry. Các mã hợp lệ: {REGISTRY.available()}")
            return 1

        
        step_cfg_dict = prep_cfg.get(step_id.lower(), {})
        
        try:
            step_cfg = config_cls(**step_cfg_dict)
        except Exception as e:
            logger.error(f"Config error in {step_id}: {e}")
            return 1
            
        step_started_at = pd.Timestamp.utcnow().isoformat()
        step_t0 = time.time()

        try:
            res = run_step(step_id, runner, step_cfg, df, ctx, max_row_loss=max_row_loss)
            df = res.data
            step_reports.append(res.report)
            
            if res.report.status == "blocked":
                status_final = "blocked"
                failed_step = step_id
                exit_code = 3
                if fail_fast:
                    break
            elif res.report.status == "failed":
                status_final = "failed"
                failed_step = step_id
                exit_code = 2
                if fail_fast:
                    break
            else:
                if res.report.status == "warning" and status_final == "ok":
                    status_final = "warning"
                
                # Save interim
                if not dry_run and pipe_cfg.get("save_interim", True):
                    write_data(df, os.path.join(paths.interim, f"after_{step_id}.parquet"))
                    
                # Save artifacts
                if not dry_run:
                    for art_name, art_df in res.artifacts.items():
                        if art_name == "data_dictionary":
                            art_df.to_csv(os.path.join(paths.processed, f"{art_name}.csv"), index=False)
                        else:
                            write_data(art_df, os.path.join(paths.processed, "artifacts", f"{art_name}.parquet"))
                        
        except DataQualityError as e:
            status_final = "blocked"
            failed_step = step_id
            exit_code = 3
            fail_rep = _failure_report(
                step_id, _module_name(runner), "blocked", e.code, e.message,
                getattr(e, "details", {}), df, step_started_at, time.time() - step_t0,
                step_cfg.model_dump())
            partial = getattr(e, "result", None)
            if partial is not None:
                # Module đã chạy xong nhưng bị cổng an toàn chặn: giữ lại findings gốc của
                # nó và ghi artifact (vd quarantine) để người dùng xem vì sao mất dòng.
                fail_rep.findings.extend(partial.report.findings)
                fail_rep.n_rows_out = len(partial.data)
                if not dry_run:
                    for art_name, art_df in partial.artifacts.items():
                        write_data(art_df, os.path.join(paths.processed, "artifacts", f"{art_name}.parquet"))
            step_reports.append(fail_rep)
            msg = f"\nPIPELINE FAILED\n  step        : {step_id}\n  code        : {e.code}\n  message     : {e.message}\n  rows in/out : {len(df)} / -\n  report      : {os.path.join(paths.reports, 'run_report.json')}\n"
            sys.stderr.write(msg.lstrip())
            if fail_fast:
                break
        except RaCausalError as e:
            status_final = "failed"
            failed_step = step_id
            exit_code = 2
            step_reports.append(_failure_report(
                step_id, _module_name(runner), "failed", e.code, e.message,
                getattr(e, "details", {}), df, step_started_at, time.time() - step_t0,
                step_cfg.model_dump()))
            msg = f"\nPIPELINE FAILED\n  step        : {step_id}\n  code        : {e.code}\n  message     : {e.message}\n  rows in/out : {len(df)} / -\n  report      : {os.path.join(paths.reports, 'run_report.json')}\n"
            sys.stderr.write(msg.lstrip())
            if fail_fast:
                break
        except Exception as e:
            import traceback
            status_final = "failed"
            failed_step = step_id
            exit_code = 2
            tb = traceback.format_exc().splitlines()[-50:]
            step_reports.append(_failure_report(
                step_id, _module_name(runner), "failed", f"{step_id}.UNEXPECTED_EXCEPTION",
                str(e), {"traceback": tb}, df, step_started_at, time.time() - step_t0,
                step_cfg.model_dump()))
            msg = f"\nPIPELINE FAILED\n  step        : {step_id}\n  code        : {step_id}.UNEXPECTED_EXCEPTION\n  message     : {str(e)}\n  rows in/out : {len(df)} / -\n  report      : {os.path.join(paths.reports, 'run_report.json')}\n"
            sys.stderr.write(msg.lstrip())
            if fail_fast:
                break
                
    duration_s = time.time() - start_time
    
    # Save final
    if not dry_run and exit_code == 0:
        write_data(df, os.path.join(paths.processed, "analysis_ready.parquet"))
        
    outputs_info = {
        "analysis_ready": os.path.join(paths.processed, "analysis_ready.parquet"),
        "artifacts": {}
    }
    
    context_final = {
        "adjustment_set": ctx.adjustment_set,
        "treatment_definition": ctx.treatment_definition,
        "cluster_column": ctx.cluster_column,
        "fold_column": ctx.fold_column,
        "outcome_observed_column": ctx.outcome_observed_column
    }
    
    if not dry_run:
        write_run_report(
            path=os.path.join(paths.reports, "run_report.json"),
            run_id=run_id,
            started_at=started_at.isoformat(),
            finished_at=pd.Timestamp.utcnow().isoformat(),
            duration_s=round(duration_s, 3),
            status=status_final,
            failed_step=failed_step,
            config_dict=prep_cfg,
            schema_version=schema.version,
            input_info=input_info,
            steps=step_reports,
            context_final=context_final,
            outputs_info=outputs_info
        )
        
    return exit_code

