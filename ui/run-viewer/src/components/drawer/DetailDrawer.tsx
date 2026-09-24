import { useUIStore, DrawerTab } from '../../store/uiStore';
import { RunReport } from '../../data/types';
import modulesData from '../../content/modules.json';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';
import { StatusBadge } from '../common/StatusBadge';
import * as Tabs from '@radix-ui/react-tabs';
import { useEffect } from 'react';
import ProblemTab from './ProblemTab';
import ParamsTab from './ParamsTab';
import ResultTab from './ResultTab';
import { stepsInRunOrder } from '../../data/derive';
import clsx from 'clsx';

const TABS: { id: DrawerTab; n: string; label: string }[] = [
  { id: 'problem', n: '01', label: 'Vấn đề' },
  { id: 'params', n: '02', label: 'Tham số' },
  { id: 'result', n: '03', label: 'Kết quả' },
];

export default function DetailDrawer({ run }: { run: RunReport }) {
  const selectedNodeId = useUIStore(s => s.selectedNodeId);
  const setSelectedNodeId = useUIStore(s => s.setSelectedNodeId);
  const drawerTab = useUIStore(s => s.drawerTab);
  const setDrawerTab = useUIStore(s => s.setDrawerTab);

  const isOpen = !!selectedNodeId;
  const steps = stepsInRunOrder(run, modulesData.modules as any);
  const stepIdx = steps.findIndex(s => s.module_id === selectedNodeId);
  const step = steps[stepIdx];
  const moduleInfo = modulesData.modules.find(m => m.id === selectedNodeId);
  const lane = modulesData.lanes.find(l => l.modules.includes(selectedNodeId ?? ''));

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!isOpen) return;
      // Không cướp phím khi người dùng đang gõ (ô tìm kiếm của từ điển mã)
      if ((e.target as HTMLElement)?.closest('input, textarea')) return;
      if (e.key === 'Escape') setSelectedNodeId(null);
      else if (e.key === 'ArrowLeft' && stepIdx > 0) setSelectedNodeId(steps[stepIdx - 1].module_id);
      else if (e.key === 'ArrowRight' && stepIdx < steps.length - 1) setSelectedNodeId(steps[stepIdx + 1].module_id);
      else if (e.key === '1') setDrawerTab('problem');
      else if (e.key === '2') setDrawerTab('params');
      else if (e.key === '3' && step?.status !== 'not_run') setDrawerTab('result');
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [isOpen, stepIdx, steps, setSelectedNodeId, setDrawerTab, step?.status]);

  if (!isOpen || !step || !moduleInfo) return null;

  const NavBtn = ({ dir }: { dir: -1 | 1 }) => {
    const target = steps[stepIdx + dir];
    return (
      <button
        className="flex h-8 w-8 items-center justify-center rounded-full border border-border text-text-muted hover:border-line-strong/60 hover:text-text disabled:opacity-30"
        disabled={!target}
        title={target ? `${dir < 0 ? 'Bước trước' : 'Bước sau'}: ${target.module_id}` : undefined}
        onClick={() => target && setSelectedNodeId(target.module_id)}
      >
        {dir < 0 ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
      </button>
    );
  };

  return (
    <aside className="absolute right-0 top-0 bottom-0 z-30 flex w-[520px] flex-col border-l border-border bg-surface shadow-panel">
      <div className="shrink-0 border-b border-border px-6 pt-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="kicker">
              Bước {stepIdx + 1}/{steps.length} · {lane?.label.split(' · ')[1]}
            </div>
            <div className="mt-1.5 flex items-center gap-2.5">
              <span className="font-mono text-[20px] font-semibold text-accent">{step.module_id}</span>
              <span className="font-display text-[20px] font-bold text-text">{step.module_name}</span>
              <StatusBadge status={step.status} />
            </div>
            <div className="mt-1 font-mono text-[11.5px] text-text-faint">
              {moduleInfo.file} · spec {step.spec_version}
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <NavBtn dir={-1} />
            <NavBtn dir={1} />
            <button
              className="ml-1 flex h-8 w-8 items-center justify-center rounded-full text-text-muted hover:bg-surface-2 hover:text-text"
              title="Đóng (Esc)"
              onClick={() => setSelectedNodeId(null)}
            >
              <X className="h-[18px] w-[18px]" />
            </button>
          </div>
        </div>

        <Tabs.Root value={drawerTab} onValueChange={(v) => setDrawerTab(v as DrawerTab)} className="mt-4">
          <Tabs.List className="-mb-px flex gap-6">
            {TABS.map(t => (
              <Tabs.Trigger
                key={t.id}
                value={t.id}
                disabled={t.id === 'result' && step.status === 'not_run'}
                className={clsx(
                  "flex items-baseline gap-1.5 border-b-2 pb-2.5 text-[14px] font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-30",
                  drawerTab === t.id ? "border-accent text-text" : "border-transparent text-text-muted hover:text-text",
                )}
              >
                <span className="font-mono text-[11px] font-normal text-text-faint">{t.n}</span>
                {t.label}
              </Tabs.Trigger>
            ))}
          </Tabs.List>
        </Tabs.Root>
      </div>

      <div className="relative min-h-0 flex-1 overflow-y-auto bg-bg/40">
        {drawerTab === 'problem' && <ProblemTab step={step} moduleInfo={moduleInfo} />}
        {drawerTab === 'params' && <ParamsTab step={step} />}
        {drawerTab === 'result' && <ResultTab step={step} />}
      </div>
    </aside>
  );
}
