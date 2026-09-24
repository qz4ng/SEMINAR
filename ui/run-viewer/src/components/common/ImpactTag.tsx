import { OctagonMinus, ListX, PenLine, Flag, Columns3, ListFilter, FileText, CircleDashed } from 'lucide-react';
import clsx from 'clsx';

/** Mỗi lựa chọn tham số kéo theo loại tác động nào lên dữ liệu (param_guide.json → tags). */
export const IMPACT = {
  stop: { icon: OctagonMinus, label: "Dừng pipeline", color: "text-blocked" },
  drop: { icon: ListX, label: "Bỏ dòng", color: "text-failed" },
  modify: { icon: PenLine, label: "Sửa giá trị", color: "text-warn" },
  flag: { icon: Flag, label: "Gắn cờ, giữ dòng", color: "text-info" },
  cols: { icon: Columns3, label: "Thêm / bỏ cột", color: "text-teal" },
  select: { icon: ListFilter, label: "Đổi tập biến", color: "text-context-edge" },
  report: { icon: FileText, label: "Chỉ báo cáo", color: "text-text-muted" },
  noop: { icon: CircleDashed, label: "Chưa có trong code", color: "text-text-faint" },
} as const;

export type Impact = keyof typeof IMPACT;

export function ImpactTag({ tag, className }: { tag: Impact; className?: string }) {
  const t = IMPACT[tag];
  if (!t) return null;
  const Icon = t.icon;
  return (
    <span className={clsx(
      "inline-flex items-center gap-1 rounded-md border px-1.5 py-[1px] text-[11px] leading-[18px] whitespace-nowrap",
      tag === 'noop' ? "border-dashed border-border text-text-faint" : "border-border bg-surface text-text-muted",
      className,
    )}>
      <Icon className={clsx("w-3 h-3 shrink-0", t.color)} strokeWidth={2.2} />
      {t.label}
    </span>
  );
}
