import { StepReport } from '../../data/types';
import { visibleFindings, newFlagColumns } from '../../data/derive';
import errorCodes from '../../content/error_codes.json';
import * as Accordion from '@radix-ui/react-accordion';
import * as Dialog from '@radix-ui/react-dialog';
import JsonView from '@uiw/react-json-view';
import { SeverityDot } from '../common/SeverityDot';
import { ChevronDown, Braces, X, Maximize2 } from 'lucide-react';
import DetailsView, { jsonViewStyle } from '../common/DetailsView';
import { useState } from 'react';
import { explainCode } from '../../data/derive';
import * as Tooltip from '@radix-ui/react-tooltip';
import clsx from 'clsx';
import artifactsPreview from '../../mock/artifacts_preview.json';

export default function ResultTab({ step }: { step: StepReport }) {
  if (step.status === 'not_run') {
    return <div className="px-6 py-5 text-text-muted">Chưa có kết quả.</div>;
  }

  const findings = visibleFindings(step);
  // Bước bị chặn/lỗi: backend ghi n_rows_out = 0 nhưng đó KHÔNG phải mất dòng (DESIGN §4.2, §6.3)
  const halted = step.status === 'blocked' || step.status === 'failed';
  const dropped = !halted && step.n_rows_in !== undefined && step.n_rows_out !== undefined ? step.n_rows_in - step.n_rows_out : undefined;
  const newFlags = newFlagColumns(step);

  const bySeverity = {
    blocking: findings.filter(f => f.severity === 'blocking'),
    error: findings.filter(f => f.severity === 'error'),
    warning: findings.filter(f => f.severity === 'warning'),
    info: findings.filter(f => f.severity === 'info'),
  };

  const defaultAccordionValue = [];
  if (bySeverity.blocking.length) defaultAccordionValue.push('blocking');
  if (bySeverity.error.length) defaultAccordionValue.push('error');
  if (bySeverity.warning.length) defaultAccordionValue.push('warning');

  const StatCard = ({ label, value, highlight }: any) => (
    <div className="flex flex-col justify-center rounded-lg border border-border bg-surface px-3 py-2.5">
      <div className="section-label">{label}</div>
      <div className={clsx("mt-1 font-display text-[18px] font-semibold tabular-nums leading-none", highlight ? "text-blocked" : "text-text")}>{value}</div>
    </div>
  );

  return (
    <div className="flex flex-col gap-6 px-6 py-5">
      <div className="grid grid-cols-3 gap-2">
        <StatCard label="Dòng vào" value={step.n_rows_in ?? '—'} />
        <StatCard label="Dòng ra" value={halted ? '—' : (step.n_rows_out ?? '—')} />
        <StatCard label="Dòng bị loại" value={dropped ?? '—'} highlight={dropped && dropped > 0} />
        <StatCard label="Cột mới" value={step.columns_added?.length || 0} />
        <StatCard label="Cột cờ mới" value={newFlags.length} />
        <StatCard label="Cột bị sửa" value={step.columns_modified?.length || 0} />
      </div>

      <StepSummary step={step} />

      <div>
        <SectionTitle>Phát hiện <span className="text-text-faint">({findings.length})</span></SectionTitle>
        {findings.length === 0 ? (
          <div className="text-text-muted text-[13px]">Không có phát hiện nào ở bước này.</div>
        ) : (
          <Accordion.Root type="multiple" defaultValue={defaultAccordionValue} className="space-y-2.5">
            {(['blocking', 'error', 'warning', 'info'] as const).map(sev => {
               const list = bySeverity[sev];
               if (list.length === 0) return null;
               
               return (
                 <Accordion.Item value={sev} key={sev} className="overflow-hidden rounded-xl border border-border bg-surface">
                   <Accordion.Header>
                     <Accordion.Trigger className="group flex w-full items-center justify-between px-4 py-2.5 transition-colors hover:bg-surface-2/60">
                       <div className="flex items-center gap-2">
                         <SeverityDot severity={sev} />
                         <span className="text-[13px] font-semibold">{SEV_LABEL[sev]}</span>
                         <span className="font-mono text-[12px] text-text-faint">{list.length}</span>
                       </div>
                       <ChevronDown className="w-4 h-4 text-text-muted transition-transform group-data-[state=open]:rotate-180" />
                     </Accordion.Trigger>
                   </Accordion.Header>
                   <Accordion.Content className="space-y-2 border-t border-border/80 bg-bg/40 p-2.5">
                     {list.map((f, i) => (
                       <div key={i} className="rounded-lg border border-border bg-surface p-3 text-[13px]">
                         <div className="flex justify-between items-start mb-2">
                           <Tooltip.Provider>
                             <Tooltip.Root delayDuration={300}>
                               <Tooltip.Trigger className="cursor-help font-mono text-[12px] font-semibold text-accent underline decoration-accent/40 decoration-dashed underline-offset-4">
                                 {f.code}
                               </Tooltip.Trigger>
                               <Tooltip.Portal>
                                 <Tooltip.Content sideOffset={6} className="z-50 max-w-[280px] rounded-lg border border-border bg-surface px-3 py-2 text-[12.5px] leading-relaxed text-text shadow-panel">
                                   {explainCode(f.code, errorCodes)}
                                 </Tooltip.Content>
                               </Tooltip.Portal>
                             </Tooltip.Root>
                           </Tooltip.Provider>
                           {f.count > 0 && <div className="font-mono text-[12px] text-text-muted tabular-nums" title="Số lượng (count)">×{f.count}</div>}
                         </div>
                         {f.column && <div className="mb-1.5 font-mono text-[11.5px] text-text-faint">cột {f.column}</div>}
                         <div className="leading-snug text-text">{f.message}</div>
                         
                         <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                           {f.sample_ids.map(id => (
                             <button key={id} title="Bấm để chép" onClick={() => navigator.clipboard?.writeText(id)} className="rounded border border-border bg-bg px-1.5 py-0.5 font-mono text-[11px] text-text-muted transition-colors hover:text-text">
                               {id}
                             </button>
                           ))}
                           <FindingDetails finding={f} />
                         </div>
                       </div>
                     ))}
                   </Accordion.Content>
                 </Accordion.Item>
               );
            })}
          </Accordion.Root>
        )}
      </div>

      {step.artifacts && Object.keys(step.artifacts).length > 0 && (
        <div>
          <SectionTitle>Artifact <span className="text-text-faint">({Object.keys(step.artifacts).length})</span></SectionTitle>
          <div className="space-y-2">
            {Object.entries(step.artifacts).map(([key, file]) => {
              const preview = (artifactsPreview as any)[key];
              return (
                <div key={key} className="flex items-center justify-between rounded-lg border border-border bg-surface px-3 py-2.5 text-[13px]">
                  <div className="flex flex-col gap-1">
                    <span className="font-mono font-semibold text-text">{key}</span>
                    <span className="text-[12px] text-text-faint">{file}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    {preview && <span className="text-text-muted text-[12px]">{preview.n_rows} dòng</span>}
                    <button 
                      disabled={!preview}
                      className="rounded-full border border-border px-2.5 py-0.5 text-[12px] text-text-muted transition-colors hover:text-text disabled:opacity-50"
                      title={!preview ? "Chưa có bản xem trước" : ""}
                    >
                      Xem bảng
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
      
      {step.context_updates && step.context_updates.length > 0 && (
        <div>
          <SectionTitle>Context đã ghi</SectionTitle>
          <div className="flex flex-wrap gap-2">
            {step.context_updates.map(u => (
               <div key={u} className="rounded-full border border-context-edge/40 bg-context-edge/[0.07] px-2.5 py-0.5 font-mono text-[12px] text-context-edge">
                 {u}
               </div>
            ))}
          </div>
        </div>
      )}

      <div className="mt-2">
        <Dialog.Root>
           <Dialog.Trigger className="flex w-full items-center justify-center gap-2 rounded-full border border-border bg-surface py-2 text-[13px] text-text-muted transition-colors hover:border-line-strong/60 hover:text-text">
             <Braces className="w-4 h-4 text-text-muted" />
             Xem JSON gốc
           </Dialog.Trigger>
           <Dialog.Portal>
             <Dialog.Overlay className="fixed inset-0 z-40 bg-text/25 backdrop-blur-[2px]" />
             <Dialog.Content className="fixed left-1/2 top-1/2 z-50 flex h-[80vh] w-[min(80vw,1000px)] -translate-x-1/2 -translate-y-1/2 flex-col gap-4 rounded-2xl border border-border bg-surface p-6 shadow-panel">
               <div className="flex shrink-0 items-start justify-between">
                 <div>
                   <div className="kicker">Báo cáo gốc</div>
                   <Dialog.Title className="mt-1 font-display text-[18px] font-bold text-text">{step.module_id} · JSON</Dialog.Title>
                 </div>
                 <Dialog.Close className="rounded-full p-1.5 text-text-muted hover:bg-surface-2 hover:text-text"><X className="h-4 w-4" /></Dialog.Close>
               </div>
               <div className="flex-1 overflow-auto rounded-xl border border-border bg-bg/60 p-4">
                 <JsonView value={step} collapsed={1} enableClipboard displayDataTypes={false} style={jsonViewStyle} />
               </div>
             </Dialog.Content>
           </Dialog.Portal>
        </Dialog.Root>
      </div>
    </div>
  );
}

const SEV_LABEL = { blocking: 'Chặn pipeline', error: 'Lỗi dữ liệu', warning: 'Cảnh báo', info: 'Thông tin' } as const;

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <div className="mb-3 font-display text-[15px] font-semibold text-text">{children}</div>;
}

/** Nút "Chi tiết" của một finding: bảng khóa–giá trị dễ đọc, có thể chuyển sang JSON. */
function FindingDetails({ finding }: { finding: any }) {
  const [raw, setRaw] = useState(false);
  const empty = !finding.details || Object.keys(finding.details).length === 0;
  if (empty) return null;
  return (
    <Dialog.Root>
      <Dialog.Trigger className="ml-auto inline-flex items-center gap-1 rounded-full border border-border px-2.5 py-0.5 text-[11.5px] text-text-muted hover:border-line-strong/60 hover:text-text">
        Chi tiết <Maximize2 className="h-3 w-3" />
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-text/25 backdrop-blur-[2px]" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 flex max-h-[80vh] w-[min(92vw,620px)] -translate-x-1/2 -translate-y-1/2 flex-col gap-4 rounded-2xl border border-border bg-surface p-6 shadow-panel">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="kicker">Chi tiết phát hiện</div>
              <Dialog.Title className="mt-1 break-all font-mono text-[15px] font-semibold text-text">{finding.code}</Dialog.Title>
              <Dialog.Description className="mt-1 text-[13px] leading-snug text-text-muted">{finding.message}</Dialog.Description>
            </div>
            <Dialog.Close className="rounded-full p-1.5 text-text-muted hover:bg-surface-2 hover:text-text"><X className="h-4 w-4" /></Dialog.Close>
          </div>
          <div className="flex items-center gap-1 self-start rounded-full border border-border p-0.5 text-[12px]">
            {([false, true] as const).map(r => (
              <button key={String(r)} onClick={() => setRaw(r)}
                className={clsx("rounded-full px-3 py-0.5", raw === r ? "bg-text text-bg" : "text-text-muted hover:text-text")}>
                {r ? 'JSON' : 'Bảng'}
              </button>
            ))}
          </div>
          <div className="min-h-0 flex-1 overflow-auto rounded-xl border border-border bg-bg/60 px-4 py-2">
            {raw
              ? <div className="py-2"><JsonView value={finding.details} displayDataTypes={false} enableClipboard style={jsonViewStyle} /></div>
              : <DetailsView details={finding.details} />}
          </div>
          {finding.details?._trimmed && <div className="text-[12px] italic text-warn">Chi tiết lớn, đã rút gọn trong dữ liệu mẫu.</div>}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/** Số liệu tóm tắt của bước (finding *.SUMMARY): ngưỡng, tỷ lệ, bảng… — mặc định thu gọn. */
function StepSummary({ step }: { step: StepReport }) {
  const summary = step.findings?.find(f => f.code.endsWith('.SUMMARY'));
  if (!summary?.details || Object.keys(summary.details).length === 0) return null;
  return (
    <Accordion.Root type="single" collapsible>
      <Accordion.Item value="s" className="overflow-hidden rounded-xl border border-border bg-surface">
        <Accordion.Header>
          <Accordion.Trigger className="group flex w-full items-center justify-between px-4 py-2.5 hover:bg-surface-2/60">
            <span className="flex min-w-0 items-baseline gap-2">
              <span className="shrink-0 text-[13px] font-semibold text-text">Số liệu tóm tắt</span>
              <span className="truncate font-mono text-[11px] text-text-faint">{Object.keys(summary.details).filter(k => !k.startsWith('_')).join(' · ')}</span>
            </span>
            <ChevronDown className="h-4 w-4 text-text-muted transition-transform group-data-[state=open]:rotate-180" />
          </Accordion.Trigger>
        </Accordion.Header>
        <Accordion.Content className="max-h-[420px] overflow-auto border-t border-border/80 bg-bg/40 px-4 py-2">
          <DetailsView details={summary.details} />
        </Accordion.Content>
      </Accordion.Item>
    </Accordion.Root>
  );
}
