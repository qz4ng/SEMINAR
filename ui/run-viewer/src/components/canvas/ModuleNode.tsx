import { Handle, Position } from '@xyflow/react';
import { useUIStore } from '../../store/uiStore';
import { StatusBadge } from '../common/StatusBadge';
import { SeverityDot } from '../common/SeverityDot';
import { ChevronRight, Target, SlidersHorizontal, Package } from 'lucide-react';
import clsx from 'clsx';
import { useRef } from 'react';

// Viền + nền pha màu theo trạng thái, như các ô biến trong DAG của Atlas.
const TONE: Record<string, string> = {
  ok: "border-ok/55 bg-ok/[0.06]",
  warning: "border-warn/60 bg-warn/[0.07]",
  blocked: "border-blocked/70 bg-blocked/[0.08]",
  failed: "border-failed/70 bg-failed/[0.08]",
  not_run: "border-dashed border-line-strong/45 bg-transparent",
};

export default function ModuleNode({ data, id }: any) {
  const selectedNodeId = useUIStore(s => s.selectedNodeId);
  const hoveredNodeId = useUIStore(s => s.hoveredNodeId);
  const setSelectedNodeId = useUIStore(s => s.setSelectedNodeId);
  const setHoveredNodeId = useUIStore(s => s.setHoveredNodeId);
  const setDrawerTab = useUIStore(s => s.setDrawerTab);
  const timer = useRef<ReturnType<typeof setTimeout>>();

  const isSelected = selectedNodeId === id;
  const isExpanded = isSelected || hoveredNodeId === id;
  const isNotRun = data.status === 'not_run';

  const openDrawer = (tab: "problem" | "params" | "result") => {
    setSelectedNodeId(id);
    setDrawerTab(tab);
  };

  const Row = ({ icon: Icon, text, tab, disabled }: any) => (
    <button
      className="group flex h-10 w-full items-center justify-between gap-2 border-t border-border/70 px-3 text-left hover:bg-surface-2/70 disabled:cursor-not-allowed disabled:opacity-50"
      disabled={disabled}
      onClick={(e) => { e.stopPropagation(); if (!disabled) openDrawer(tab); }}
    >
      <span className="flex min-w-0 items-center gap-2">
        <Icon className="h-3.5 w-3.5 shrink-0 text-text-faint group-hover:text-accent" />
        <span className="truncate text-[12px] text-text-muted group-hover:text-text">{text}</span>
      </span>
      <ChevronRight className="h-3.5 w-3.5 shrink-0 text-text-faint" />
    </button>
  );

  return (
    // Nền surface đặt ở lớp ngoài, lớp trong pha màu trạng thái: không bị nhìn xuyên qua
    // khung lane khi node nở ra phủ lên lane dưới.
    <div
      className={clsx(
        "relative w-[240px] cursor-pointer rounded-[10px] bg-surface transition-shadow duration-150",
        isSelected ? "shadow-lift ring-2 ring-accent ring-offset-2 ring-offset-bg" : isExpanded ? "shadow-lift" : "",
      )}
      onMouseEnter={() => { timer.current = setTimeout(() => setHoveredNodeId(id), 250); }}
      onMouseLeave={() => { clearTimeout(timer.current); if (useUIStore.getState().hoveredNodeId === id) setHoveredNodeId(null); }}
    >
      {/* Handle phải có `id`: cạnh trỏ tới sourceHandle/targetHandle theo id, thiếu id thì
          React Flow không vẽ được cạnh nào. Cạnh context lệch 25% / 75% để không đè cạnh dữ liệu. */}
      <Handle id="in-left" type="target" position={Position.Left} style={{ top: 48 }} className="!opacity-0" />
      <Handle id="out-right" type="source" position={Position.Right} style={{ top: 48 }} className="!opacity-0" />
      <Handle id="in-top" type="target" position={Position.Top} className="!opacity-0" />
      <Handle id="out-bottom" type="source" position={Position.Bottom} className="!opacity-0" />
      <Handle id="ctx-in-top" type="target" position={Position.Top} style={{ left: '25%' }} className="!opacity-0" />
      <Handle id="ctx-out-top" type="source" position={Position.Top} style={{ left: '75%' }} className="!opacity-0" />
      <Handle id="ctx-out-bottom" type="source" position={Position.Bottom} style={{ left: '75%' }} className="!opacity-0" />

      <div className={clsx("overflow-hidden rounded-[10px] border-[1.5px]", TONE[data.status] ?? TONE.not_run)}>
        {/* Tầng 1: luôn hiện */}
        <div className={clsx("flex h-[93px] flex-col justify-between px-3.5 py-3", isNotRun && "opacity-60")}>
          <div className="flex items-center justify-between gap-2">
            <div className="flex min-w-0 items-baseline gap-2" title={data.file}>
              <span className="font-mono text-[13.5px] font-semibold text-text">{id}</span>
              <span className="truncate font-mono text-[12px] text-text-muted">{data.moduleName}</span>
            </div>
            <StatusBadge status={data.status} compact />
          </div>

          <div className="truncate text-[12.5px] text-text-muted tabular-nums">
            {isNotRun ? "chưa chạy" : (
              <>
                {data.n_rows_in} <span className="text-text-faint">→</span>{' '}
                <span className={data.rowsDropped ? "font-semibold text-blocked" : "text-text"}>{data.rowsOut}</span> dòng
                <span className="text-text-faint"> · {data.duration_s?.toFixed(2)}s</span>
              </>
            )}
          </div>

          <div className="flex min-w-0 items-center gap-1.5 font-mono text-[11px]">
            {isNotRun ? (
              <span className="text-text-faint">Chưa chạy trong lần này</span>
            ) : data.finding ? (
              <>
                <SeverityDot severity={data.finding.severity} />
                <span className="truncate text-text-muted">{data.finding.code.split('.')[1]}</span>
                <span className="shrink-0 text-text-faint">· {data.finding.count}</span>
              </>
            ) : (
              <span className="text-text-faint">Không có phát hiện</span>
            )}
          </div>
        </div>

        {/* Tầng 2: nở ra khi rê chuột 250ms hoặc khi đang chọn */}
        <div className={clsx(
          "grid bg-surface transition-[grid-template-rows,opacity] duration-150 ease-out",
          isExpanded ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0",
        )}>
          <div className="overflow-hidden">
            <Row icon={Target} tab="problem" text={data.shortDesc} />
            <Row
              icon={SlidersHorizontal} tab="params"
              text={data.changedParams > 0
                ? `${data.firstChangedParam} = ${data.firstChangedVal}${data.changedParams > 1 ? ` · +${data.changedParams - 1}` : ''}`
                : `${data.paramCount} tham số · đều mặc định`}
            />
            <Row
              icon={Package} tab="result" disabled={isNotRun}
              text={isNotRun ? "Chưa có kết quả" : `${data.findingCount} phát hiện · ${data.artifactCount} artifact · ghi ${data.firstContextWrite || '—'}${data.extraContextWrites ? ` +${data.extraContextWrites}` : ''}`}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
