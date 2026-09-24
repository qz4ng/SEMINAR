import runs from '../mock/runs.json';
import { RunReport } from './types';

/** Lượt chạy mẫu (dirty.csv, chạy hết 9 bước). Khi nối backend thật, thay bằng đọc run_report.json. */
export function getRun(): RunReport {
  return (runs as any).A as RunReport;
}
