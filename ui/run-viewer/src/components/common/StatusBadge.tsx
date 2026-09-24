import { StepStatus } from '../../data/types';
import { CircleCheck, TriangleAlert, OctagonMinus, CircleX, CircleDashed } from 'lucide-react';
import * as Tooltip from '@radix-ui/react-tooltip';
import clsx from 'clsx';

export const STATUS = {
  ok: { icon: CircleCheck, label: "Ổn", tone: "text-ok bg-ok/10 border-ok/30", solid: "bg-ok text-accent-ink", tooltip: "Chạy xong, không có gì đáng ngại" },
  warning: { icon: TriangleAlert, label: "Cảnh báo", tone: "text-warn bg-warn/10 border-warn/35", solid: "bg-warn text-accent-ink", tooltip: "Chạy xong, có cảnh báo cần xem" },
  blocked: { icon: OctagonMinus, label: "Bị chặn", tone: "text-blocked bg-blocked/10 border-blocked/35", solid: "bg-blocked text-accent-ink", tooltip: "Module chạy đúng nhưng dữ liệu vi phạm ngưỡng — hãy xem lại dữ liệu" },
  failed: { icon: CircleX, label: "Lỗi", tone: "text-failed bg-failed/10 border-failed/35", solid: "bg-failed text-accent-ink", tooltip: "Lỗi kỹ thuật — hãy xem lại code hoặc cấu hình" },
  not_run: { icon: CircleDashed, label: "Chưa chạy", tone: "text-text-faint bg-transparent border-border border-dashed", solid: "bg-surface-2 text-text-faint", tooltip: "Không chạy vì một bước trước đó dừng pipeline" },
} as const;

/**
 * compact: chỉ icon trong vòng tròn (dùng trên node canvas — viền node đã mang màu trạng
 * thái, chữ nằm trong tooltip). Bình thường: pill viền mảnh, nền pha màu như chip của Atlas.
 */
export function StatusBadge({ status, label, compact }: { status: StepStatus, label?: string, compact?: boolean }) {
  const conf = STATUS[status] || STATUS.not_run;
  const Icon = conf.icon;
  const text = label ?? conf.label;

  return (
    <Tooltip.Provider>
      <Tooltip.Root delayDuration={300}>
        <Tooltip.Trigger asChild>
          <span
            aria-label={text}
            className={clsx(
              "inline-flex items-center rounded-full border whitespace-nowrap font-medium",
              compact ? "p-[3px]" : "gap-1.5 px-2.5 py-[2px] text-[12px]",
              conf.tone,
            )}
          >
            <Icon className={compact ? "w-3.5 h-3.5" : "w-3.5 h-3.5"} strokeWidth={2.2} />
            {!compact && <span>{text}</span>}
          </span>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content className="z-50 max-w-[260px] rounded-lg border border-border bg-surface px-3 py-2 text-[12.5px] text-text shadow-panel" sideOffset={6}>
            {compact && <div className="mb-0.5 font-semibold">{text}</div>}
            <div className="text-text-muted">{conf.tooltip}</div>
            <Tooltip.Arrow className="fill-surface" />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}
