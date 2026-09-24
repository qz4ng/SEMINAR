import { BaseEdge, EdgeProps, Position, getBezierPath } from '@xyflow/react';
import * as Tooltip from '@radix-ui/react-tooltip';

// Điểm điều khiển giống hệt getBezierPath của React Flow (curvature 0.25), để tính
// được một điểm bất kỳ trên đường cong chứ không chỉ điểm giữa.
function controlOffset(d: number) { return d >= 0 ? 0.5 * d : 0.25 * 25 * Math.sqrt(-d); }
function control(pos: Position, x1: number, y1: number, x2: number, y2: number): [number, number] {
  switch (pos) {
    case Position.Left: return [x1 - controlOffset(x1 - x2), y1];
    case Position.Right: return [x1 + controlOffset(x2 - x1), y1];
    case Position.Top: return [x1, y1 - controlOffset(y1 - y2)];
    default: return [x1, y1 + controlOffset(y2 - y1)];
  }
}
function pointAt(t: number, p0: [number, number], p1: [number, number], p2: [number, number], p3: [number, number]) {
  const u = 1 - t;
  const f = (i: 0 | 1) => u * u * u * p0[i] + 3 * u * u * t * p1[i] + 3 * u * t * t * p2[i] + t * t * t * p3[i];
  return [f(0), f(1)];
}

export default function ContextEdge({
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  markerEnd,
  data
}: EdgeProps) {
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });
  // Cùng làn: nhãn ở đỉnh vòng cung (t=0.5). Khác làn: điểm giữa rơi đúng lên đầu node
  // ở làn dưới và che tên node, nên đặt nhãn sát node nguồn (t=0.2).
  const t = sourcePosition === Position.Top ? 0.5 : 0.2;
  const [labelX, labelY] = pointAt(
    t,
    [sourceX, sourceY],
    control(sourcePosition, sourceX, sourceY, targetX, targetY),
    control(targetPosition, targetX, targetY, sourceX, sourceY),
    [targetX, targetY],
  );
  const showLabel = data?.showLabel !== false;

  return (
    <>
      <BaseEdge path={edgePath} markerEnd={markerEnd} style={{ stroke: 'rgb(var(--context))', strokeWidth: 1.6, strokeDasharray: '5 4' }} />
      {showLabel && <foreignObject
        width={100}
        height={40}
        x={labelX - 50}
        y={labelY - 20}
        className="overflow-visible"
        requiredExtensions="http://www.w3.org/1999/xhtml"
      >
        <div className="flex items-center justify-center h-full w-full">
          <Tooltip.Provider>
            <Tooltip.Root>
              <Tooltip.Trigger asChild>
                <div className="bg-surface border border-context-edge/50 px-1.5 py-[1px] rounded-full text-[10.5px] font-mono text-context-edge shadow-sm cursor-help whitespace-nowrap">
                  {data?.key as string}
                </div>
              </Tooltip.Trigger>
              <Tooltip.Portal>
                <Tooltip.Content side="top" className="bg-surface border border-border text-text px-2.5 py-1.5 rounded-lg text-[12px] z-50 shadow-panel max-w-[260px]">
                  {data?.meaning as string}
                  <Tooltip.Arrow className="fill-surface" />
                </Tooltip.Content>
              </Tooltip.Portal>
            </Tooltip.Root>
          </Tooltip.Provider>
        </div>
      </foreignObject>}
    </>
  );
}
