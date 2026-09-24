import { RunReport } from './types';
import { LENSES, VARS, Tone, CONCEPTS } from '../content/dataContext';
import variableRoles from '../mock/variable_roles.json';
import profile from '../mock/data_profile.json';

export const ROLES: Record<string, any> = Object.fromEntries((variableRoles as any[]).map(v => [v.column, v]));
export const PROFILE: any = profile;

/**
 * Thay chỗ giữ số trong văn bản bằng số của lượt chạy / dữ liệu:
 *   {P01.OUT_OF_RANGE@yield_t_ha}  → count của finding đó ở cột đó
 *   {P02.UNIT_CONVERTED}            → count của finding đầu tiên có mã đó
 *   {P09.ICC_ESTIMATE:icc}          → details.icc (làm tròn 3 chữ số)
 *   {ds.final.treated}              → data_profile.dataset.final.treated
 */
export function fillText(text: string, run: RunReport): string {
  return text.replace(/\{([^}]+)\}/g, (_, expr: string) => {
    if (expr.startsWith('ds.')) {
      const v = expr.slice(3).split('.').reduce((o: any, k) => o?.[k], PROFILE.dataset);
      return v === undefined ? '?' : String(v);
    }
    const [codeCol, key] = expr.split(':');
    const [code, col] = codeCol.split('@');
    const step = run.steps.find(s => s.module_id === code.split('.')[0]);
    const f = step?.findings?.find(x => x.code === code && (!col || x.column === col));
    if (!f) return '?';
    if (key) {
      const v = f.details?.[key];
      return typeof v === 'number' ? v.toFixed(3) : String(v ?? '?');
    }
    return String(f.count);
  });
}

const IN_SCHEMA = (c: string) => c in ROLES;

/** Bước `m` làm gì với cột `col`. `rest` = hành động mặc định (không đặc biệt). */
export function lensAction(m: string, col: string): { tone: Tone; text: string; rest?: boolean } | null {
  if (m === 'P08') return p08Action(col);
  const lens = LENSES[m];
  if (!lens) return null;
  const a = lens.actions[col];
  if (a) return { tone: a[0], text: a[1] };
  if (lens.rest && IN_SCHEMA(col) && col in VARS) return { tone: lens.rest[0], text: lens.rest[1], rest: true };
  return null;
}

/** P08 suy từ bảng vai trò biến (artifact data_dictionary của lượt chạy). */
function p08Action(col: string): { tone: Tone; text: string } | null {
  const r = ROLES[col];
  if (!r) return col === 'yield_unit' ? { tone: 'block', text: 'Không có trong danh sách hợp lệ của P07.' } : null;
  switch (r.dag_role) {
    case 'confounder': return r.in_L ? { tone: 'keep', text: 'Confounder → vào L (cả hai biến thể).' } : { tone: 'block', text: 'Confounder nhưng bị loại (thiếu nhiều / không biến thiên).' };
    case 'ambiguous': return { tone: 'keep', text: 'Vai trò chưa rõ → vào L ở biến thể O_as_confounder, ngoài L ở O_as_mediator.' };
    case 'instrument': return { tone: 'block', text: 'Instrument → loại (đưa vào PS làm khuếch đại bias).' };
    case 'noise': return { tone: 'block', text: 'Nhiễu → loại.' };
    case 'mediator': return { tone: 'block', text: 'Mediator → loại (P07 đã chặn vì đo sau).' };
    case 'collider': return { tone: 'block', text: 'Collider → loại (P07 đã chặn vì đo sau).' };
    case 'outcome_predictor': return { tone: 'block', text: 'Chỉ ảnh hưởng Y: include_precision_vars bật nhưng P07 đã chặn vì đo sau → không vào L.' };
    case 'treatment': return { tone: 'block', text: 'Can thiệp → không vào L.' };
    case 'treatment_version': return { tone: 'block', text: 'Phiên bản can thiệp → không vào L.' };
    case 'outcome': return { tone: 'block', text: 'Outcome → không vào L.' };
    case 'cluster': return { tone: 'check', text: 'Khóa cụm → không vào L (P09 dùng).' };
    case 'id': return { tone: 'check', text: 'Cột định danh.' };
    default: return null;
  }
}

export const RUN_ORDER = ['P01', 'P02', 'P03', 'P04', 'P05', 'P07', 'P08', 'P06', 'P09'];

export const conceptOf = (col: string) => CONCEPTS.find(c => c.vars.includes(col));
