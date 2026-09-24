import { RunReport } from '../../data/types';
import variableRoles from '../../mock/variable_roles.json';
import * as ToggleGroup from '@radix-ui/react-toggle-group';
import { useState } from 'react';
import { ClipboardList } from 'lucide-react';

export default function AdjustmentSetPanel({ run }: { run: RunReport }) {
  const [variant, setVariant] = useState('O_as_confounder');
  const p08 = run.steps.find(s => s.module_id === 'P08');
  
  if (!p08 || p08.status === 'not_run' || run.status === 'blocked') {
    return (
      <div className="mt-10 w-[300px] p-4 text-center text-text-muted">
        <ClipboardList className="mx-auto mb-2 h-6 w-6 text-text-faint" />
        <div>Chưa có tập L — P08 chưa chạy trong lần này.</div>
      </div>
    );
  }

  const lVars = variableRoles.filter(v => v.in_L && v.variant_membership.includes(variant));
  const count = (name: string) => variableRoles.filter(v => v.in_L && v.variant_membership.includes(name)).length;
  const blockedVars = variableRoles.filter(v => !v.in_L);

  return (
    <div className="flex h-full w-[300px] flex-col overflow-y-auto px-4 py-4 text-sm">
      <div className="kicker">Kết quả P08 → P06</div>
      <div className="mt-1 mb-4 font-display text-[16px] font-semibold text-text">Tập điều chỉnh L · {lVars.length} biến</div>
      
      <ToggleGroup.Root
        type="single"
        value={variant}
        onValueChange={(v) => v && setVariant(v)}
        className="mb-4 flex rounded-full border border-border p-0.5"
      >
        <ToggleGroup.Item value="O_as_confounder" className="flex-1 rounded-full py-1 font-mono text-[11px] text-text-muted data-[state=on]:bg-text data-[state=on]:text-bg">
          O_as_confounder ({count('O_as_confounder')})
        </ToggleGroup.Item>
        <ToggleGroup.Item value="O_as_mediator" className="flex-1 rounded-full py-1 font-mono text-[11px] text-text-muted data-[state=on]:bg-text data-[state=on]:text-bg">
          O_as_mediator ({count('O_as_mediator')})
        </ToggleGroup.Item>
      </ToggleGroup.Root>

      <div className="mb-6 flex flex-wrap gap-1.5">
        {lVars.map(v => (
          <div key={v.column} className="flex items-center gap-1.5 rounded-full border border-ok/40 bg-ok/[0.07] px-2.5 py-0.5 font-mono text-[11.5px] text-text">
            {v.variant_membership === "['O_as_confounder']" && (
               <div className="w-1.5 h-1.5 rounded-full bg-context-edge" title="Practice RA khác, vai trò chưa rõ" />
            )}
            {v.column}
          </div>
        ))}
      </div>

      <div className="mb-3 font-display text-[14px] font-semibold text-text">Bị chặn / không dùng</div>
      <div className="space-y-4">
        {['post', 'pre', 'at'].map(timing => {
          const vars = blockedVars.filter(v => v.measured_at === timing || (!v.measured_at && timing === 'pre'));
          if (vars.length === 0) return null;
          return (
            <div key={timing}>
              <div className="section-label mb-2">
                {timing === 'post' ? 'Đo sau can thiệp' : 'Không phải biến điều chỉnh'}
              </div>
              <div className="space-y-2">
                {vars.map(v => (
                  <div key={v.column} className="flex items-center justify-between gap-2 rounded-lg border border-border bg-bg/50 px-2.5 py-1.5">
                    <div className="font-mono text-[12px] text-text-muted">{v.column}</div>
                    {/* Hardcoding reasons since reasoning is in blocked_reason_rules */}
                    <div className="text-[11.5px] text-text-faint">{v.dag_role}</div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
      
      <div className="mt-8 border-t border-border pt-4 text-[12px] italic text-text-faint">
        Vai trò biến là giả định DAG v0, chưa được CIAT xác nhận.
      </div>
    </div>
  );
}
