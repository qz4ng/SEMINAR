import { ReactFlow, ReactFlowProvider, Background, BackgroundVariant, Controls, Node, Edge, MarkerType, useReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { RunReport } from '../../data/types';
import modulesData from '../../content/modules.json';
import paramsData from '../../mock/params.json';
import { stepsInRunOrder, notableFinding, visibleFindings, changedParams, rowsOutLabel } from '../../data/derive';
import ModuleNode from './ModuleNode';
import ContextEdge from './ContextEdge';
import LaneGroup from './LaneGroup';
import LaneTransferEdge from './LaneTransferEdge';
import { useUIStore } from '../../store/uiStore';
import { useEffect, useMemo, useState } from 'react';
import { useThemeColors } from '../../data/useThemeColors';

const nodeTypes = { module: ModuleNode, lane: LaneGroup };
const edgeTypes = { context: ContextEdge, laneTransfer: LaneTransferEdge };

// ---- Bố cục cố định (DESIGN §3.1) ----------------------------------------
// Mỗi làn: 56px cho nhãn + 96px node + đệm. Làn cách nhau 36px để cạnh chuyển làn
// có chỗ đi ngang mà không cắt qua nhãn của làn dưới.
const NODE_W = 240;
const NODE_H = 96;
const COL_GAP = 60;                 // khoảng trống giữa hai node cùng làn
const LANE_PAD_X = 24;
const LANE_HEADER = 56;
const LANE_H = LANE_HEADER + NODE_H + 24;
const LANE_GAP = 36;
const LANE_W = LANE_PAD_X * 2 + 4 * NODE_W + 3 * COL_GAP;
const DRAWER_W = 520;

const laneY = (lane: number) => (lane - 1) * (LANE_H + LANE_GAP);

function nodePosition(moduleId: string) {
  const lane = modulesData.lanes.find(l => l.modules.includes(moduleId))!;
  const col = lane.modules.indexOf(moduleId);
  return { x: LANE_PAD_X + col * (NODE_W + COL_GAP), y: laneY(lane.id) + LANE_HEADER, lane: lane.id };
}


/** Giữ node đang chọn nằm trong phần canvas KHÔNG bị drawer che (DESIGN §2). */
function ViewportFollower({ ready }: { ready: boolean }) {
  const selectedNodeId = useUIStore(s => s.selectedNodeId);
  const { setCenter, fitView } = useReactFlow();

  useEffect(() => {
    // Chỉ điều khiển khung nhìn sau khi React Flow khởi tạo xong (onInit). Làm sớm hơn
    // thì lệnh bị bỏ qua và khung nhìn đứng yên ở translate(0,0).
    if (!ready) return;
    const id = requestAnimationFrame(() => {
      if (!selectedNodeId) {
        fitView({ padding: 0.06, duration: 250 });
        return;
      }
      const p = nodePosition(selectedNodeId);
      const zoom = 0.9;
      // Tâm khung nhìn dời sang phải nửa bề rộng drawer => node nằm giữa vùng còn thấy.
      setCenter(p.x + NODE_W / 2 + DRAWER_W / 2 / zoom, p.y + NODE_H, { zoom, duration: 300 });
    });
    return () => cancelAnimationFrame(id);
  }, [ready, selectedNodeId, setCenter, fitView]);

  return null;
}

function Canvas({ run }: { run: RunReport }) {
  const selectedNodeId = useUIStore(s => s.selectedNodeId);
  const hoveredNodeId = useUIStore(s => s.hoveredNodeId);
  const setSelectedNodeId = useUIStore(s => s.setSelectedNodeId);
  const setDrawerTab = useUIStore(s => s.setDrawerTab);
  const [ready, setReady] = useState(false);
  const c = useThemeColors();

  const { nodes, edges } = useMemo(() => {
    const newNodes: Node[] = [];
    const newEdges: Edge[] = [];

    modulesData.lanes.forEach(lane => {
      newNodes.push({
        id: `lane${lane.id}`, type: 'lane', position: { x: 0, y: laneY(lane.id) },
        data: lane, style: { width: LANE_W, height: LANE_H, pointerEvents: 'none' }, zIndex: -1,
        selectable: false, draggable: false,
      });
    });

    const steps = stepsInRunOrder(run, modulesData.modules as any);

    steps.forEach((step) => {
      const info = modulesData.modules.find(m => m.id === step.module_id);
      const pos = nodePosition(step.module_id);
      const defaults = (paramsData as any)[step.module_id]?.defaults || {};
      const changes = changedParams(step, defaults);
      const ran = step.status === 'ok' || step.status === 'warning';

      let firstChangedVal: string | undefined;
      if (changes.length > 0) {
        const v = step.params_effective?.[changes[0]];
        firstChangedVal = typeof v === 'object' ? '{…}' : String(v);
      }

      newNodes.push({
        id: step.module_id,
        type: 'module',
        position: { x: pos.x, y: pos.y },
        zIndex: selectedNodeId === step.module_id || hoveredNodeId === step.module_id ? 10 : 1,
        data: {
          ...step,
          moduleName: info?.name ?? step.module_name,
          file: info?.file,
          shortDesc: info?.short,
          finding: notableFinding(step),
          rowsOut: rowsOutLabel(step),
          // Chỉ bước chạy thành công mới có "mất dòng"; bước hỏng ghi n_rows_out = 0 nhưng
          // đó không phải mất dữ liệu (DESIGN §4.2).
          rowsDropped: ran && (step.n_rows_in ?? 0) > (step.n_rows_out ?? 0),
          paramCount: Object.keys(defaults).length,
          changedParams: changes.length,
          firstChangedParam: changes[0],
          firstChangedVal,
          findingCount: visibleFindings(step).length,
          artifactCount: step.artifacts ? Object.keys(step.artifacts).length : 0,
          firstContextWrite: step.context_updates?.[0],
          extraContextWrites: Math.max((step.context_updates?.length ?? 0) - 1, 0),
        },
      });
    });

    // ---- Cạnh dữ liệu: luôn hiện, theo đúng thứ tự chạy ----------------------
    for (let i = 0; i < steps.length - 1; i++) {
      const source = steps[i];
      const target = steps[i + 1];
      const crossLane = nodePosition(source.module_id).lane !== nodePosition(target.module_id).lane;

      const touchesSelected = !!selectedNodeId && (source.module_id === selectedNodeId || target.module_id === selectedNodeId);
      // Như Atlas: cạnh thường màu xám-xanh, cạnh đang xét màu nhấn; bước dừng mang màu trạng thái.
      const stroke = target.status === 'blocked' ? c.blocked
        : target.status === 'failed' ? c.failed
        : target.status === 'not_run' ? c.line
        : touchesSelected ? c.accent : c['line-strong'];
      const opacity = !selectedNodeId || touchesSelected ? 1 : 0.4;

      newEdges.push({
        id: `e-${source.module_id}-${target.module_id}`,
        source: source.module_id,
        target: target.module_id,
        // Chuyển làn: từ đáy node nguồn, đi ngang ở khe giữa hai làn, xuống ở lề trái
        // làn dưới rồi vào cạnh TRÁI node đích — không cắt ngang nhãn làn.
        sourceHandle: crossLane ? 'out-bottom' : 'out-right',
        targetHandle: 'in-left',
        type: crossLane ? 'laneTransfer' : 'smoothstep',
        pathOptions: { borderRadius: 12 },
        // Khe giữa làn nguồn và làn đích: nơi cạnh chuyển làn đi ngang
        data: crossLane ? { gapY: laneY(nodePosition(target.module_id).lane) - LANE_GAP / 2 } : undefined,
        style: {
          stroke, strokeWidth: touchesSelected ? 2.2 : 1.5, opacity,
          strokeDasharray: target.status === 'not_run' ? '6 5' : undefined,
        },
        markerEnd: { type: MarkerType.ArrowClosed, color: stroke, width: 15, height: 15 },
      } as Edge);
    }

    // ---- Cạnh context: chỉ hiện khi hover/chọn node ở một đầu -----------------
    const focus = hoveredNodeId ?? selectedNodeId;
    const labelled = new Set<string>();
    modulesData.context_edges.forEach(ce => {
      if (focus !== ce.from && focus !== ce.to) return;
      const sameLane = nodePosition(ce.from).lane === nodePosition(ce.to).lane;
      // P05 ghi treatment_column cho cả P06 lẫn P09: hai nhãn nằm chồng nhau sát P05,
      // chỉ vẽ một lần.
      const labelKey = `${ce.from}:${ce.key}`;
      const showLabel = !labelled.has(labelKey);
      labelled.add(labelKey);
      newEdges.push({
        id: `ce-${ce.from}-${ce.to}-${ce.key}`,
        source: ce.from,
        target: ce.to,
        type: 'context',
        data: { ...ce, showLabel },
        // Cùng làn: cong vòng phía trên; khác làn: từ đáy (lệch 75%) xuống đỉnh (lệch 25%).
        sourceHandle: sameLane ? 'ctx-out-top' : 'ctx-out-bottom',
        targetHandle: 'ctx-in-top',
        markerEnd: { type: MarkerType.ArrowClosed, color: c.context, width: 14, height: 14 },
        zIndex: 20,
      });
    });

    return { nodes: newNodes, edges: newEdges };
  }, [run, selectedNodeId, hoveredNodeId, c]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      // Không dùng prop fitView: nó chạy sau ViewportFollower và ghi đè vị trí đã dời.
      // ViewportFollower là nơi DUY NHẤT điều khiển khung nhìn.
      minZoom={0.4}
      maxZoom={1.5}
      proOptions={{ hideAttribution: true }}
      nodesConnectable={false}
      nodesDraggable={false}
      elementsSelectable={false}
      zoomOnDoubleClick={false}
      onInit={() => setReady(true)}
      // BẮT BUỘC: khi node không chọn/kéo/nối được và KHÔNG có handler sự kiện nào,
      // React Flow gán pointer-events:none cho node => không click, không hover được.
      // Truyền onNodeClick là cách chính thức để node nhận sự kiện chuột trở lại.
      onNodeClick={(_, node) => {
        if (node.type !== 'module') return;
        setSelectedNodeId(node.id);
        setDrawerTab('problem');
      }}
    >
      <Background variant={BackgroundVariant.Dots} color={c.line} gap={22} size={1.4} />
      <Controls position="bottom-right" showInteractive={false} />
      <ViewportFollower ready={ready} />
    </ReactFlow>
  );
}

export default function PipelineCanvas({ run }: { run: RunReport }) {
  return (
    <div className="relative min-h-0 w-full flex-1">
      <ReactFlowProvider>
        <Canvas run={run} />
      </ReactFlowProvider>
    </div>
  );
}
