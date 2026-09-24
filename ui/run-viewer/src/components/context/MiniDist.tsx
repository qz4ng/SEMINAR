import clsx from 'clsx';

const fmt = (n: number) => Math.abs(n) >= 1000 ? n.toLocaleString('vi-VN', { maximumFractionDigits: 0 }) : Number.isInteger(n) ? String(n) : n.toFixed(2);

/** Phân phối gọn của một cột: histogram (số), thanh theo mức (hạng mục), hoặc số mã (định danh). */
export function MiniDist({ p, label, accent }: { p: any; label: string; accent?: boolean }) {
  if (!p) return (
    <div className="rounded-lg border border-dashed border-border px-3 py-2 text-[12px] text-text-faint">
      <div className="section-label mb-1">{label}</div>không còn cột này
    </div>
  );
  return (
    <div className="min-w-0 rounded-lg border border-border bg-surface px-3 py-2">
      <div className="flex items-baseline justify-between gap-2">
        <span className="section-label">{label}</span>
        <span className="font-mono text-[10.5px] text-text-faint">{p.n} dòng</span>
      </div>
      {p.kind === 'num' && p.hist && <Hist p={p} accent={accent} />}
      {p.kind === 'cat' && <Bars p={p} accent={accent} />}
      {p.kind === 'id' && (
        <div className="mt-1.5 font-mono text-[12px] text-text-muted">
          {p.n_unique} mã khác nhau{p.duplicated > 0 && <span className="text-blocked"> · {p.duplicated} trùng</span>}
        </div>
      )}
      <div className="mt-1.5 flex flex-wrap gap-x-3 font-mono text-[10.5px]">
        <span className={p.missing > 0 ? "text-warn" : "text-text-faint"}>thiếu {p.missing}</span>
        {p.invalid > 0 && <span className="text-blocked">không phải số {p.invalid}</span>}
      </div>
    </div>
  );
}

function Hist({ p, accent }: { p: any; accent?: boolean }) {
  const max = Math.max(...p.hist, 1);
  return (
    <>
      <div className="mt-1.5 flex h-9 items-end gap-[2px]">
        {p.hist.map((h: number, i: number) => (
          <div key={i} className={clsx("flex-1 rounded-t-[2px]", accent ? "bg-accent/70" : "bg-line-strong/45")}
            style={{ height: h === 0 ? 1 : Math.max((h / max) * 36, 2) }} title={`${h} dòng`} />
        ))}
      </div>
      <div className="mt-0.5 flex justify-between font-mono text-[10.5px] text-text-muted">
        <span>{fmt(p.min)}</span><span className="text-text-faint">trung vị {fmt(p.median)}</span><span>{fmt(p.max)}</span>
      </div>
    </>
  );
}

function Bars({ p, accent }: { p: any; accent?: boolean }) {
  const max = Math.max(...p.top.map((t: any) => t[1]), 1);
  return (
    <div className="mt-1.5 flex flex-col gap-[3px]">
      {p.top.map(([k, n]: [string, number]) => (
        <div key={k} className="grid grid-cols-[72px_1fr_28px] items-center gap-1.5">
          <span className="truncate font-mono text-[10.5px] text-text-muted" title={JSON.stringify(k)}>{k === '' ? '(trống)' : k}</span>
          <div className="h-2 rounded-full bg-surface-2">
            <div className={clsx("h-2 rounded-full", accent ? "bg-accent/70" : "bg-line-strong/50")} style={{ width: `${(n / max) * 100}%` }} />
          </div>
          <span className="text-right font-mono text-[10.5px] text-text-faint">{n}</span>
        </div>
      ))}
    </div>
  );
}
