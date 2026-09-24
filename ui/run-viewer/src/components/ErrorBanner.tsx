import { RunReport } from '../data/types';
import { useUIStore } from '../store/uiStore';
import modulesData from '../content/modules.json';
import { OctagonMinus, CircleX, ArrowRight } from 'lucide-react';
import { stepsInRunOrder, visibleFindings } from '../data/derive';
import clsx from 'clsx';

/** Chỉ hiện khi báo cáo có bước bị chặn/lỗi (dữ liệu mẫu hiện tại chạy hết nên không hiện). */
export default function ErrorBanner({ run }: { run: RunReport }) {
  const setSelectedNodeId = useUIStore(s => s.setSelectedNodeId);
  const setDrawerTab = useUIStore(s => s.setDrawerTab);

  if (run.status !== 'blocked' && run.status !== 'failed') return null;
  if (!run.failed_step) return null;

  const failedStep = run.steps.find(s => s.module_id === run.failed_step);
  const mainFinding = failedStep ? visibleFindings(failedStep)[0] : undefined;
  const skipped = stepsInRunOrder(run, modulesData.modules as any).filter(s => s.status === 'not_run').map(s => s.module_id);
  const isBlocked = run.status === 'blocked';

  return (
    <div className={clsx(
      "shrink-0 z-10 flex h-11 items-center justify-between gap-4 border-b px-6 text-[13px]",
      isBlocked ? "border-blocked/30 bg-blocked/[0.07] text-blocked" : "border-failed/30 bg-failed/[0.07] text-failed",
    )}>
      <div className="flex min-w-0 items-center gap-2">
        {isBlocked ? <OctagonMinus className="w-4 h-4 shrink-0" /> : <CircleX className="w-4 h-4 shrink-0" />}
        <span className="font-semibold shrink-0">Dừng tại {run.failed_step}</span>
        {mainFinding && <span className="truncate font-mono text-[12px]">· {mainFinding.code} · {mainFinding.message}</span>}
        <button
          onClick={() => { setSelectedNodeId(run.failed_step); setDrawerTab('result'); }}
          className="ml-2 inline-flex shrink-0 items-center gap-1 rounded-full border border-current/30 bg-surface px-2.5 py-0.5 text-[12px] font-medium text-text hover:bg-surface-2"
        >
          Mở bước {run.failed_step} <ArrowRight className="w-3 h-3" />
        </button>
      </div>
      {skipped.length > 0 && <div className="shrink-0 text-text-muted">Không chạy: {skipped.join(', ')}</div>}
    </div>
  );
}
