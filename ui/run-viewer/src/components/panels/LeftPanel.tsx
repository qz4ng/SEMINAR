import { useUIStore } from '../../store/uiStore';
import { RunReport } from '../../data/types';
import { ListChecks, Archive, BookOpen } from 'lucide-react';
import clsx from 'clsx';
import AdjustmentSetPanel from './AdjustmentSetPanel';
import ArtifactsPanel from './ArtifactsPanel';

const NAV = [
  { id: 'L', icon: ListChecks, label: 'Tập L', title: 'Tập điều chỉnh L' },
  { id: 'artifacts', icon: Archive, label: 'Artifact', title: 'Các bảng phụ đã xuất' },
  { id: 'dict', icon: BookOpen, label: 'Mã', title: 'Từ điển mã (phím /)' },
] as const;

export default function LeftPanel({ run }: { run: RunReport }) {
  const panel = useUIStore(s => s.leftPanel);
  const setPanel = useUIStore(s => s.setLeftPanel);

  return (
    <div className="z-20 flex h-full shrink-0">
      <nav className="flex h-full w-16 flex-col items-center gap-1 border-r border-border bg-bg py-3">
        {NAV.map(({ id, icon: Icon, label, title }) => (
          <button
            key={id}
            title={title}
            onClick={() => setPanel(panel === id ? null : id)}
            className={clsx(
              "flex w-12 flex-col items-center gap-1 rounded-lg py-2 text-[10.5px] transition-colors",
              panel === id ? "bg-accent/10 text-accent" : "text-text-muted hover:bg-surface-2 hover:text-text",
            )}
          >
            <Icon className="h-[18px] w-[18px]" />
            {label}
          </button>
        ))}
      </nav>
      <div className={clsx(
        "relative h-full overflow-hidden bg-surface transition-[width] duration-300 ease-in-out",
        panel && panel !== 'dict' ? "w-[300px] border-r border-border shadow-panel" : "w-0",
      )}>
        {panel === 'L' && <AdjustmentSetPanel run={run} />}
        {panel === 'artifacts' && <ArtifactsPanel run={run} />}
      </div>
    </div>
  );
}
