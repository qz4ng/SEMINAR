import { RunReport } from '../data/types';
import { useUIStore } from '../store/uiStore';
import { funnelPoints } from '../data/derive';
import modulesData from '../content/modules.json';
import * as Tooltip from '@radix-ui/react-tooltip';
import clsx from 'clsx';

// Phễu dòng (DESIGN §7.3). Tự dựng bằng flex thay vì thư viện biểu đồ để số dòng,
// tên bước và độ lệch nằm đúng cùng một cột — bản dùng Recharts để nhãn "−2" trôi
// sang cột bên cạnh.
const BAR_MAX_PX = 34;

const HATCH: Record<string, string> = {
  blocked: 'repeating-linear-gradient(135deg, rgb(var(--blocked)) 0 4px, rgb(var(--blocked) / .25) 4px 8px)',
  failed: 'repeating-linear-gradient(135deg, rgb(var(--failed)) 0 4px, rgb(var(--failed) / .25) 4px 8px)',
};

export default function RowFunnel({ run }: { run: RunReport }) {
  const points = funnelPoints(run, modulesData.modules as any);
  const selectedNodeId = useUIStore(s => s.selectedNodeId);
  const setSelectedNodeId = useUIStore(s => s.setSelectedNodeId);
  // Trục bắt đầu từ 0: không cắt trục để phóng đại chênh lệch vài dòng.
  const max = Math.max(...points.map(p => (typeof p.value === 'number' ? p.value : 0)), 1);

  return (
    // Drawer (520px) đè lên mép phải: khi mở thì dồn phễu sang trái để vẫn thấy đủ 10 cột.
    <div
      className="shrink-0 border-t border-border bg-surface pl-6 pt-2.5 pb-2 z-10 transition-[padding] duration-300"
      style={{ paddingRight: selectedNodeId ? 520 + 24 : 24 }}
    >
      <div className="mb-1 flex items-center justify-between gap-4">
        <span className="flex items-baseline gap-2">
          <span className="section-label">Số dòng sau mỗi bước</span>
          <span className="font-mono text-[10.5px] text-text-faint">theo thứ tự chạy · trục từ 0</span>
        </span>
        <span className={clsx("flex items-center gap-1.5 text-[11.5px] text-text-faint", selectedNodeId && "hidden")}>
          Rê chuột vào bước: xem nhanh · nhấn: mở chi tiết · <span className="kbd">←</span><span className="kbd">→</span> chuyển bước · <span className="kbd">Esc</span> đóng
        </span>
      </div>
      <Tooltip.Provider delayDuration={200}>
        <div className="flex items-end gap-2">
          {points.map((p) => {
            const isInput = p.name === 'Vào';
            const status = p.status as string;
            const notRun = status === 'not_run';
            const halted = status === 'blocked' || status === 'failed';
            const selected = p.name === selectedNodeId;
            const barH = typeof p.value === 'number' ? Math.max((p.value / max) * BAR_MAX_PX, 2) : BAR_MAX_PX;

            const valueLabel = notRun ? '—' : halted ? (status === 'blocked' ? 'chặn' : 'lỗi') : String(p.value);
            const tip = isInput
              ? `Dữ liệu vào · ${p.value} dòng`
              : notRun
                ? `${p.name} · chưa chạy`
                : halted
                  ? `${p.name} · ${status === 'blocked' ? 'bị chặn' : 'lỗi'} — không có số dòng ra`
                  : `${p.name} · ${p.value} dòng${p.delta ? ` (${p.delta})` : ''}`;

            return (
              <Tooltip.Root key={p.name}>
                <Tooltip.Trigger asChild>
                  <button
                    className={clsx(
                      'flex-1 min-w-0 flex flex-col items-center gap-1 rounded-md py-1 transition-colors',
                      isInput ? 'cursor-default' : 'hover:bg-surface-2',
                    )}
                    onClick={() => { if (!isInput) setSelectedNodeId(p.name); }}
                  >
                    <span className={clsx(
                      'font-mono text-[11px] tabular-nums leading-none',
                      halted ? (status === 'blocked' ? 'text-blocked' : 'text-failed') : notRun ? 'text-text-faint' : selected ? 'text-text font-semibold' : 'text-text-muted',
                    )}>
                      {valueLabel}
                    </span>
                    <div className="w-full flex items-end justify-center" style={{ height: BAR_MAX_PX }}>
                      <div
                        className={clsx(
                          'w-[70%] rounded-t-[3px] transition-colors',
                          notRun && 'border border-dashed border-line-strong/50 bg-transparent',
                          !notRun && !halted && (selected ? 'bg-accent' : isInput ? 'bg-line-strong/30' : 'bg-line-strong/45'),
                        )}
                        style={{ height: barH, background: halted ? HATCH[status] : undefined }}
                      />
                    </div>
                    <span className={clsx(
                      'font-mono text-[11px] leading-none',
                      selected ? 'text-accent font-semibold' : notRun ? 'text-text-faint' : 'text-text-muted',
                    )}>
                      {p.name}
                    </span>
                    <span className="font-mono text-[11px] leading-none h-3 text-blocked tabular-nums">
                      {p.delta ?? ''}
                    </span>
                  </button>
                </Tooltip.Trigger>
                <Tooltip.Portal>
                  <Tooltip.Content side="top" sideOffset={4} className="bg-surface border border-border text-text px-2.5 py-1 rounded-lg text-[12px] font-mono z-50 shadow-panel">
                    {tip}
                  </Tooltip.Content>
                </Tooltip.Portal>
              </Tooltip.Root>
            );
          })}
        </div>
      </Tooltip.Provider>
    </div>
  );
}
