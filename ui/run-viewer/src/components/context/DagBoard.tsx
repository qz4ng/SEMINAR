import { ReactFlow, ReactFlowProvider, Background, BackgroundVariant, Controls, Edge, Node, MarkerType, useReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useEffect, useMemo, useState } from 'react';
import clsx from 'clsx';
import { CONCEPTS, DAG_EDGES } from '../../content/dataContext';
import { lensAction, RUN_ORDER, conceptOf } from '../../data/contextDerive';
import { useThemeColors } from '../../data/useThemeColors';
import { useUIStore } from '../../store/uiStore';
import modulesData from '../../content/modules.json';
import { RunReport } from '../../data/types';
import ConceptNode, { VarChip } from './ConceptNode';
import Inspector from './Inspector';

const nodeTypes = { concept: ConceptNode };

/** Khái niệm nào có ít nhất một cột bị bước `lens` đụng tới (không tính hành động mặc định). */
function touched(lens: string, conceptId: string) {
  const c = CONCEPTS.find(x => x.id === conceptId)!;
  return c.vars.some(v => { const a = lensAction(lens, v); return a && !a.rest; });
}

function Canvas() {
  const lens = useUIStore(s => s.lens);
  const ctxSel = useUIStore(s => s.ctxSel);
  const setCtxSel = useUIStore(s => s.setCtxSel);
  const [hover, setHover] = useState<string | null>(null);
  const c = useThemeColors();
  const { fitView } = useReactFlow();
  const [ready, setReady] = useState(false);

  // Khái niệm đang được "soi": rê chuột ưu tiên, sau đó tới mục đang chọn
  const selConcept = ctxSel?.startsWith('c:') ? ctxSel.slice(2) : ctxSel?.startsWith('v:') ? conceptOf(ctxSel.slice(2))?.id : undefined;
  const focus = hover ?? selConcept ?? null;

  useEffect(() => {
    if (!ready) return;
    const id = requestAnimationFrame(() => fitView({ padding: 0.04, duration: 200 }));
    return () => cancelAnimationFrame(id);
  }, [ready, fitView]);

  const nodes: Node[] = useMemo(() => CONCEPTS.filter(cp => cp.role !== 'tech').map(cp => ({
    id: cp.id, type: 'concept', position: { x: cp.x, y: cp.y },
    data: {
      concept: cp,
      hot: focus === cp.id,
      dim: lens !== 'roles' ? !touched(lens, cp.id) : !!focus && focus !== cp.id && !DAG_EDGES.some(([a, b]) => (a === focus && b === cp.id) || (b === focus && a === cp.id)),
    },
    draggable: false, selectable: false,
  })), [lens, focus]);

  const edges: Edge[] = useMemo(() => DAG_EDGES.map(([from, to, fs, ts, kind, label]) => {
    const on = !!focus && (from === focus || to === focus);
    const faded = (!!focus && !on) || lens !== 'roles';
    const stroke = on ? c.accent : kind === 'main' ? c.ink : c['line-strong'];
    return {
      id: `${from}-${to}`, source: from, target: to, sourceHandle: `s${fs}`, targetHandle: `t${ts}`,
      type: 'default',
      label, labelStyle: { fontFamily: 'IBM Plex Mono', fontSize: 11, fill: c.muted },
      labelBgStyle: { fill: c.surface }, labelBgPadding: [4, 2] as [number, number],
      style: {
        stroke, strokeWidth: kind === 'main' ? 2.6 : on ? 2 : 1.3,
        strokeDasharray: kind === 'dashed' ? '6 5' : undefined,
        opacity: faded ? (kind === 'main' ? 0.5 : 0.18) : on || kind === 'main' ? 1 : 0.6,
      },
      markerEnd: { type: MarkerType.ArrowClosed, color: stroke, width: kind === 'main' ? 16 : 13, height: kind === 'main' ? 16 : 13 },
      zIndex: on ? 5 : 0,
    } as Edge;
  }), [focus, lens, c]);

  return (
    <ReactFlow
      nodes={nodes} edges={edges} nodeTypes={nodeTypes}
      minZoom={0.3} maxZoom={1.6}
      nodesConnectable={false} nodesDraggable={false} elementsSelectable={false}
      zoomOnDoubleClick={false} proOptions={{ hideAttribution: true }}
      onInit={() => setReady(true)}
      onNodeMouseEnter={(_, n) => setHover(n.id)}
      onNodeMouseLeave={() => setHover(null)}
      onNodeClick={() => { /* nút/cột tự xử lý click */ }}
      onPaneClick={() => setCtxSel(null)}
    >
      <Background variant={BackgroundVariant.Dots} color={c.line} gap={22} size={1.3} />
      <Controls position="bottom-left" showInteractive={false} />
    </ReactFlow>
  );
}

/** Thanh chọn lăng kính: xem DAG theo vai trò, hoặc theo việc một module làm với từng cột. */
function LensBar() {
  const lens = useUIStore(s => s.lens);
  const setLens = useUIStore(s => s.setLens);
  const btn = (id: string, label: React.ReactNode, title?: string) => (
    <button
      key={id} title={title} onClick={() => setLens(id)}
      className={clsx(
        "rounded-full px-3 py-1 text-[12px] transition-colors",
        lens === id ? "bg-text text-bg" : "text-text-muted hover:bg-surface-2 hover:text-text",
      )}
    >
      {label}
    </button>
  );
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="section-label mr-1">Lăng kính</span>
      <div className="flex items-center gap-0.5 rounded-full border border-border bg-surface p-0.5">
        {btn('roles', 'Vai trò DAG')}
      </div>
      <div className="flex items-center gap-0.5 rounded-full border border-border bg-surface p-0.5">
        {RUN_ORDER.map(m => {
          const mod = modulesData.modules.find(x => x.id === m)!;
          return btn(m, <span className="font-mono">{m}</span>, `${m} · ${mod.name}: ${mod.short}`);
        })}
      </div>
      <span className="text-[11.5px] text-text-faint">theo thứ tự chạy</span>
    </div>
  );
}

export default function DagBoard({ run }: { run: RunReport }) {
  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="kicker">02 · DAG v0 → cột dữ liệu</div>
          <h2 className="mt-1 font-display text-[20px] font-bold text-text">Mối liên hệ giữa các biến và cách từng module xử lý</h2>
          <p className="mt-1 max-w-[760px] text-[13px] leading-relaxed text-text-muted">
            Mỗi ô là một khái niệm trong DAG, bên trong là các cột đo nó. Rê chuột vào một ô để thấy mũi tên vào/ra; nhấn vào ô hoặc cột để xem chi tiết.
            Chọn một module ở lăng kính để thấy bước đó làm gì với từng cột.
          </p>
        </div>
        <LensBar />
      </div>
      <div className="grid h-[800px] grid-cols-[minmax(0,1fr)_380px] overflow-hidden rounded-2xl border border-border bg-surface shadow-panel">
        <div className="flex min-w-0 flex-col bg-bg/50">
          <div className="relative min-h-0 flex-1">
            <ReactFlowProvider><Canvas /></ReactFlowProvider>
          </div>
          <TechStrip />
        </div>
        <Inspector run={run} />
      </div>
    </section>
  );
}

/** Cột không thuộc DAG (mã, đơn vị thô, nhiễu): dải chip dưới canvas, vẫn nhận lăng kính. */
function TechStrip() {
  const lens = useUIStore(s => s.lens);
  const ctxSel = useUIStore(s => s.ctxSel);
  const setCtxSel = useUIStore(s => s.setCtxSel);
  const t = CONCEPTS.find(c => c.role === 'tech')!;
  return (
    <div className="flex shrink-0 items-center gap-3 border-t border-border bg-surface px-4 py-2">
      <button onClick={() => setCtxSel(`c:${t.id}`)} className="shrink-0 text-left">
        <div className="section-label">Ngoài DAG</div>
        <div className="text-[12px] text-text-muted">mã · đơn vị thô · nhiễu</div>
      </button>
      <div className="grid min-w-0 flex-1 grid-cols-5 gap-1">
        {t.vars.map(v => <VarChip key={v} col={v} lens={lens} selected={ctxSel === `v:${v}`} onClick={() => setCtxSel(`v:${v}`)} />)}
      </div>
    </div>
  );
}
