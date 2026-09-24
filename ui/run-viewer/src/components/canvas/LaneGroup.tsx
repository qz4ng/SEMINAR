/** Khung một lớp (lane): nhãn kiểu Atlas — "LỚP 1" mono xanh, tên lớp, câu hỏi lớp đó trả lời. */
export default function LaneGroup({ data }: any) {
  const [kicker, title] = String(data.label).split(' · ');
  return (
    <div className="pointer-events-none h-full w-full rounded-[14px] border border-border bg-surface/70 px-6 pt-3.5">
      <div className="flex items-baseline gap-3">
        <span className="kicker">{kicker}</span>
        <span className="font-display text-[15px] font-semibold text-text">{title}</span>
        <span className="text-[13px] text-text-muted">— {data.question}</span>
      </div>
    </div>
  );
}
