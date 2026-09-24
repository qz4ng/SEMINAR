import { RunReport, StepReport, Finding, ModuleContent } from './types';

// Sort functions and helpers

export function stepsInRunOrder(run: RunReport, modules: ModuleContent[]): StepReport[] {
  return modules.map(m => {
    const step = run.steps.find(s => s.module_id === m.id);
    if (step) return step;
    return {
      module_id: m.id,
      module_name: m.name,
      spec_version: "1.0",
      status: "not_run" as const
    };
  });
}

export function notableFinding(step: StepReport): Finding | null {
  if (!step.findings || step.findings.length === 0) return null;
  const filtered = step.findings.filter(f => !f.code.endsWith(".SUMMARY"));
  if (filtered.length === 0) return null;
  
  const severityScore = {
    blocking: 4,
    error: 3,
    warning: 2,
    info: 1
  };
  
  filtered.sort((a, b) => {
    if (severityScore[a.severity] !== severityScore[b.severity]) {
      return severityScore[b.severity] - severityScore[a.severity];
    }
    if (a.count !== b.count) {
      return b.count - a.count;
    }
    return a.code.localeCompare(b.code);
  });
  
  return filtered[0];
}

export function visibleFindings(step: StepReport): Finding[] {
  if (!step.findings) return [];
  return step.findings.filter(f => !f.code.endsWith(".SUMMARY"));
}

export function newFlagColumns(step: StepReport): string[] {
  if (!step.columns_added) return [];
  return step.columns_added.filter(c => c.startsWith("flag__"));
}

export function rowsOutLabel(step: StepReport): string {
  if (step.status === "blocked" || step.status === "failed" || step.status === "not_run") {
    return "—";
  }
  return String(step.n_rows_out ?? "—");
}

export function funnelPoints(run: RunReport, modules: ModuleContent[]): any[] {
  const points = [];
  points.push({ name: "Vào", value: run.input.n_rows, delta: null, status: "ok" });
  const steps = stepsInRunOrder(run, modules);
  for (const step of steps) {
    let delta = null;
    let val = step.n_rows_out;
    if (step.status === "ok" || step.status === "warning") {
       delta = (step.n_rows_out !== undefined && step.n_rows_in !== undefined) ? step.n_rows_in - step.n_rows_out : 0;
       if (delta === 0) delta = null;
       else delta = -delta;
    } else {
       val = undefined;
    }
    points.push({
      name: step.module_id,
      value: val,
      delta,
      status: step.status
    });
  }
  return points;
}

function sortObjectKeys(obj: any): string {
  if (typeof obj !== 'object' || obj === null) return JSON.stringify(obj);
  if (Array.isArray(obj)) return JSON.stringify(obj.map(item => JSON.parse(sortObjectKeys(item))));
  const sortedKeys = Object.keys(obj).sort();
  const sortedObj: any = {};
  for (const key of sortedKeys) {
    sortedObj[key] = JSON.parse(sortObjectKeys(obj[key]));
  }
  return JSON.stringify(sortedObj);
}

export function changedParams(step: StepReport, defaults: any): string[] {
  if (!step.params_effective || !defaults) return [];
  const changed: string[] = [];
  for (const [key, value] of Object.entries(step.params_effective)) {
    if (key in defaults) {
      const valStr = sortObjectKeys(value);
      const defaultStr = sortObjectKeys(defaults[key]);
      if (valStr !== defaultStr) {
        changed.push(key);
      }
    } else {
      changed.push(key);
    }
  }
  return changed;
}

export function explainCode(code: string, dict: {code: string, explain: string}[]): string {
  const exact = dict.find(d => d.code === code);
  if (exact) return exact.explain;
  const suffix = code.substring(code.indexOf("."));
  const wild = dict.find(d => d.code === `*${suffix}`);
  if (wild) return wild.explain;
  return "Không có giải thích";
}

export function finalRowCount(run: RunReport, modules: ModuleContent[]): number | null {
  if (run.failed_step) return null;
  const steps = stepsInRunOrder(run, modules);
  for (let i = steps.length - 1; i >= 0; i--) {
    if (steps[i].status === "ok" || steps[i].status === "warning") {
      return steps[i].n_rows_out ?? null;
    }
  }
  return null;
}
