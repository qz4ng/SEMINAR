import { StepReport, ModuleContent } from '../../data/types';
import modulesData from '../../content/modules.json';
import variableRoles from '../../mock/variable_roles.json';
import * as ToggleGroup from '@radix-ui/react-toggle-group';
import * as Tooltip from '@radix-ui/react-tooltip';
import { useState } from 'react';
import { TriangleAlert, ArrowDownToLine, ArrowUpFromLine, Check, Minus } from 'lucide-react';
import clsx from 'clsx';

export default function ProblemTab({ step, moduleInfo }: { step: StepReport, moduleInfo: ModuleContent }) {
  const reads = modulesData.context_edges.filter(e => e.to === step.module_id);
  const writes = modulesData.context_edges.filter(e => e.from === step.module_id);
  const [filter, setFilter] = useState<'all' | 'in_L' | 'blocked'>('all');

  return (
    <div className="flex flex-col gap-6 px-6 py-5 text-[14px]">
      <div>
        <h3 className="font-display text-[17px] font-semibold leading-snug text-text">{moduleInfo.short}</h3>
        <p className="mt-2 leading-[1.65] text-text-muted">{moduleInfo.long}</p>
      </div>

      {/* Khối "nếu bỏ qua" kiểu thẻ viền trái của Atlas */}
      <div className="rounded-r-lg border-l-[3px] border-warn bg-warn/[0.07] px-4 py-3">
        <div className="flex items-center gap-1.5 text-[13px] font-semibold text-warn">
          <TriangleAlert className="h-3.5 w-3.5" /> Nếu bỏ qua bước này
        </div>
        <p className="mt-1 text-[13.5px] leading-relaxed text-text-muted">{moduleInfo.risk}</p>
      </div>

      {(reads.length > 0 || writes.length > 0) && (
        <div className="grid grid-cols-2 gap-3">
          <ContextList icon={ArrowDownToLine} title="Đọc từ context" items={reads} other={e => e.from} empty="Không đọc khóa nào" />
          <ContextList icon={ArrowUpFromLine} title="Ghi vào context" items={writes} other={e => e.to} empty="Không ghi khóa nào" />
        </div>
      )}

      {(step.module_id === 'P07' || step.module_id === 'P08') && (
        <div>
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-display text-[15px] font-semibold text-text">Vai trò biến</h3>
            {step.status !== 'not_run' && (
              <ToggleGroup.Root
                type="single" value={filter}
                onValueChange={(v) => v && setFilter(v as any)}
                className="flex rounded-full border border-border bg-surface p-0.5 text-[12px]"
              >
                {([['all', 'Tất cả'], ['in_L', 'Trong L'], ['blocked', 'Không dùng']] as const).map(([v, l]) => (
                  <ToggleGroup.Item key={v} value={v} className="rounded-full px-3 py-0.5 text-text-muted data-[state=on]:bg-text data-[state=on]:text-bg">
                    {l}
                  </ToggleGroup.Item>
                ))}
              </ToggleGroup.Root>
            )}
          </div>
          {step.status === 'not_run' ? (
            <div className="italic text-text-muted">Bước này chưa chạy trong lần này.</div>
          ) : (
            <>
              <div className="overflow-hidden rounded-xl border border-border bg-surface">
                <table className="w-full text-left text-[13px]">
                  <thead>
                    <tr className="border-b border-border bg-surface-2/60">
                      <th className="px-3 py-2 section-label font-normal">Cột</th>
                      <th className="px-3 py-2 section-label font-normal">Đo lúc</th>
                      <th className="px-3 py-2 section-label font-normal">Vai trò DAG</th>
                      <th className="px-3 py-2 section-label font-normal text-center">L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {variableRoles
                      .filter(v => filter === 'all' || (filter === 'in_L' && v.in_L) || (filter === 'blocked' && !v.in_L))
                      .map(v => (
                        <tr key={v.column} className="border-t border-border/60 first:border-0 hover:bg-surface-2/40">
                          <td className="px-3 py-1.5 font-mono text-[12px] text-text">{v.column}</td>
                          <td className={clsx("px-3 py-1.5 font-mono text-[12px]", v.measured_at === 'post' ? "text-blocked" : "text-text-muted")}>{v.measured_at || '—'}</td>
                          <td className="px-3 py-1.5 text-[12.5px] text-text-muted">{v.dag_role}</td>
                          <td className="px-3 py-1.5 text-center">
                            {v.in_L ? <Check className="mx-auto h-3.5 w-3.5 text-accent" strokeWidth={2.6} /> : <Minus className="mx-auto h-3.5 w-3.5 text-text-faint" />}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-2.5 text-[12px] italic text-text-faint">Vai trò biến là giả định DAG v0, chưa được CIAT xác nhận.</p>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function ContextList({ icon: Icon, title, items, other, empty }: {
  icon: any; title: string; items: { from: string; to: string; key: string; meaning: string }[];
  other: (e: any) => string; empty: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-surface px-3.5 py-3">
      <div className="mb-2 flex items-center gap-1.5 section-label"><Icon className="h-3 w-3" />{title}</div>
      {items.length === 0 ? <div className="text-[12.5px] text-text-faint">{empty}</div> : (
        <div className="flex flex-col gap-1.5">
          {items.map(e => (
            <Tooltip.Provider key={e.key + other(e)}>
              <Tooltip.Root delayDuration={200}>
                <Tooltip.Trigger asChild>
                  <div className="flex cursor-help items-center justify-between gap-2">
                    <span className="truncate rounded-full border border-context-edge/40 bg-context-edge/[0.07] px-2 py-[1px] font-mono text-[11.5px] text-context-edge">{e.key}</span>
                    <span className="shrink-0 font-mono text-[11px] text-text-faint">{title.startsWith('Đọc') ? '← ' : '→ '}{other(e)}</span>
                  </div>
                </Tooltip.Trigger>
                <Tooltip.Portal>
                  <Tooltip.Content sideOffset={6} className="z-50 max-w-[260px] rounded-lg border border-border bg-surface px-3 py-2 text-[12.5px] text-text shadow-panel">
                    {e.meaning}
                    <Tooltip.Arrow className="fill-surface" />
                  </Tooltip.Content>
                </Tooltip.Portal>
              </Tooltip.Root>
            </Tooltip.Provider>
          ))}
        </div>
      )}
    </div>
  );
}
