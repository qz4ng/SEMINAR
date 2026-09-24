import { test, expect } from 'vitest';
import { stepsInRunOrder, notableFinding, rowsOutLabel, funnelPoints, changedParams, explainCode } from './derive';
import runs from '../mock/runs.json';
import modulesData from '../content/modules.json';
import errorCodes from '../content/error_codes.json';

const runA = (runs as any)["A"];
// Lượt chạy bị chặn tại P04 dựng tay từ lượt A: dữ liệu mẫu chỉ còn một lượt chạy xong,
// nhưng logic hiển thị bước bị chặn / chưa chạy vẫn phải đúng với báo cáo thật.
const runB = {
  ...runA,
  status: "blocked",
  failed_step: "P04",
  steps: runA.steps
    .filter((s: any) => ["P01", "P02", "P03", "P04"].includes(s.module_id))
    .map((s: any) => s.module_id === "P04" ? { ...s, status: "blocked", n_rows_out: 0 } : s),
};
const modules = modulesData.modules;

test('stepsInRunOrder', () => {
  const stepsA = stepsInRunOrder(runA, modules);
  expect(stepsA.length).toBe(9);
  expect(stepsA.map(s => s.module_id)).toEqual(["P01", "P02", "P03", "P04", "P05", "P07", "P08", "P06", "P09"]);
  
  const stepsB = stepsInRunOrder(runB, modules);
  expect(stepsB.filter(s => s.status === 'not_run').length).toBe(5);
});

test('notableFinding', () => {
  const p04A = runA.steps.find((s: any) => s.module_id === "P04");
  const finding = notableFinding(p04A);
  expect(finding?.code).toBe("P04.SUSPECTED_UNIT_ERROR");
});

test('rowsOutLabel', () => {
  const p04B = runB.steps.find((s: any) => s.module_id === "P04");
  expect(rowsOutLabel(p04B)).toBe("—");
});

test('funnelPoints', () => {
  const points = funnelPoints(runA, modules);
  expect(points.find(p => p.name === "P01")?.delta).toBe(-2);
  expect(points.find(p => p.name === "P03")?.delta).toBe(-3);
  expect(points.find(p => p.name === "P02")?.delta).toBe(null);
});

test('changedParams', () => {
  const p04A = runA.steps.find((s: any) => s.module_id === "P04");
  const defaults = { ...p04A.params_effective, method: "robust_z" };
  expect(changedParams(p04A, defaults)).toEqual([]);
  expect(changedParams(p04A, { ...p04A.params_effective, method: "iqr" })).toEqual(["method"]);
});

test('explainCode', () => {
  expect(explainCode("P01.EXCESSIVE_ROW_LOSS", errorCodes)).toBe(errorCodes.find((e: any) => e.code === "*.EXCESSIVE_ROW_LOSS")?.explain);
});
