import { BaseEdge, EdgeProps } from '@xyflow/react';

/**
 * Cạnh chuyển làn (P04 → P05, P08 → P06).
 *
 * smoothstep mặc định chọn chỗ rẽ ngang ở ngang tầm node đích, nên đường kẻ chạy xuyên
 * qua giữa làn dưới và chồng lên các cạnh cùng làn. Cạnh này đi theo lộ trình cố định:
 * đáy node nguồn → xuống khe giữa hai làn (gapY) → sang trái tới lề làn (leftX) →
 * xuống ngang tâm node đích → vào cạnh trái node đích. Các góc được bo tròn.
 */
export default function LaneTransferEdge({
  sourceX, sourceY, targetX, targetY, markerEnd, style, data,
}: EdgeProps) {
  const gapY = (data?.gapY as number) ?? (sourceY + targetY) / 2;
  const leftX = targetX - 14;
  const r = 10;

  const d = [
    `M ${sourceX} ${sourceY}`,
    `L ${sourceX} ${gapY - r}`,
    `Q ${sourceX} ${gapY} ${sourceX - r} ${gapY}`,
    `L ${leftX + r} ${gapY}`,
    `Q ${leftX} ${gapY} ${leftX} ${gapY + r}`,
    `L ${leftX} ${targetY - r}`,
    `Q ${leftX} ${targetY} ${leftX + r} ${targetY}`,
    `L ${targetX} ${targetY}`,
  ].join(' ');

  return <BaseEdge path={d} markerEnd={markerEnd} style={style} />;
}
