import { RunReport } from '../../data/types';
import artifactsPreview from '../../mock/artifacts_preview.json';
import { useUIStore } from '../../store/uiStore';

export default function ArtifactsPanel({ run }: { run: RunReport }) {
  const setSelectedNodeId = useUIStore(s => s.setSelectedNodeId);
  const setDrawerTab = useUIStore(s => s.setDrawerTab);
  const artifacts = run.steps.flatMap(step =>
    Object.entries(step.artifacts ?? {}).map(([name, filename]) => ({ step: step.module_id, name, filename })));

  return (
    <div className="flex h-full w-[300px] flex-col overflow-y-auto px-4 py-4 text-sm">
      <div className="kicker">Bảng phụ</div>
      <div className="mt-1 mb-4 font-display text-[16px] font-semibold text-text">Artifact · {artifacts.length}</div>
      <div className="flex flex-col gap-2">
        {artifacts.length === 0 && <div className="text-text-muted">Không có artifact nào.</div>}
        {artifacts.map((a, i) => {
          const preview = (artifactsPreview as any)[a.name];
          return (
            <button
              key={i}
              onClick={() => { setSelectedNodeId(a.step); setDrawerTab('result'); }}
              className="rounded-xl border border-border bg-bg/50 px-3 py-2.5 text-left transition-colors hover:border-line-strong/60"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-[12.5px] font-semibold text-text">{a.name}</span>
                <span className="rounded-full border border-border px-1.5 font-mono text-[10.5px] text-text-muted">{a.step}</span>
              </div>
              <div className="mt-1 font-mono text-[11px] text-text-faint">{a.filename}</div>
              <div className="mt-1.5 text-[12px] text-text-muted">{preview ? `${preview.n_rows} dòng` : 'Chưa có bản xem trước'}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
