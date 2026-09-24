import { Role, Tone } from '../../content/dataContext';

// Tailwind chỉ sinh lớp nó thấy nguyên văn trong mã, nên liệt kê đủ từng lớp ở đây
// thay vì ghép chuỗi `border-${màu}`.
export const ROLE_CLS: Record<Role, { box: string; text: string; dot: string; chip: string }> = {
  conf: { box: 'border-conf/60 bg-conf/[0.07]', text: 'text-conf', dot: 'bg-conf', chip: 'border-conf/40' },
  trt: { box: 'border-accent/70 bg-accent/[0.08]', text: 'text-accent', dot: 'bg-accent', chip: 'border-accent/45' },
  out: { box: 'border-info/70 bg-info/[0.08]', text: 'text-info', dot: 'bg-info', chip: 'border-info/45' },
  med: { box: 'border-teal/60 bg-teal/[0.07]', text: 'text-teal', dot: 'bg-teal', chip: 'border-teal/40' },
  col: { box: 'border-failed/60 bg-failed/[0.07]', text: 'text-failed', dot: 'bg-failed', chip: 'border-failed/40' },
  prec: { box: 'border-prec/60 bg-prec/[0.08]', text: 'text-prec', dot: 'bg-prec', chip: 'border-prec/40' },
  instr: { box: 'border-instr/60 bg-instr/[0.08]', text: 'text-instr', dot: 'bg-instr', chip: 'border-instr/40' },
  unc: { box: 'border-warn/60 bg-warn/[0.06] border-dashed', text: 'text-warn', dot: 'bg-warn', chip: 'border-warn/40' },
  unm: { box: 'border-unm/60 bg-unm/[0.06] border-dashed', text: 'text-unm', dot: 'bg-unm', chip: 'border-unm/40' },
  tech: { box: 'border-border bg-surface-2/40 border-dashed', text: 'text-text-faint', dot: 'bg-text-faint', chip: 'border-border' },
};

export const TONE_CLS: Record<Tone, { chip: string; text: string; dot: string }> = {
  check: { chip: 'border-line-strong/40 bg-surface', text: 'text-text-muted', dot: 'bg-line-strong/60' },
  use: { chip: 'border-context-edge/60 bg-context-edge/[0.10]', text: 'text-context-edge', dot: 'bg-context-edge' },
  keep: { chip: 'border-ok/60 bg-ok/[0.12]', text: 'text-ok', dot: 'bg-ok' },
  flag: { chip: 'border-info/60 bg-info/[0.10]', text: 'text-info', dot: 'bg-info' },
  fix: { chip: 'border-warn/70 bg-warn/[0.12]', text: 'text-warn', dot: 'bg-warn' },
  drop: { chip: 'border-failed/60 bg-failed/[0.10]', text: 'text-failed', dot: 'bg-failed' },
  block: { chip: 'border-blocked/60 bg-blocked/[0.10]', text: 'text-blocked', dot: 'bg-blocked' },
  create: { chip: 'border-teal/60 bg-teal/[0.10]', text: 'text-teal', dot: 'bg-teal' },
};
