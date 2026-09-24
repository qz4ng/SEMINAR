import clsx from 'clsx';

/**
 * Hiện `details` của một finding dạng bảng khóa–giá trị dễ đọc, thay cho cây JSON thô.
 * Số trong khoảng 0–1 ở khóa kiểu tỷ lệ (rate, limit, share…) kèm thêm dạng phần trăm.
 */
const RATE_KEY = /(rate|limit|share|prop|frac|threshold|pct)$/i;

function fmtNumber(key: string, n: number) {
  const raw = Number.isInteger(n) ? String(n) : n.toPrecision(4).replace(/\.?0+$/, '');
  if (RATE_KEY.test(key) && n >= 0 && n <= 1) {
    return (
      <span className="tabular-nums">
        <span className="font-semibold text-text">{(n * 100).toFixed(n * 100 < 10 ? 2 : 1)}%</span>
        <span className="ml-2 text-text-faint">{raw}</span>
      </span>
    );
  }
  return <span className="tabular-nums text-text">{raw}</span>;
}

function Value({ k, v, depth }: { k: string; v: any; depth: number }) {
  if (v === null || v === undefined) return <span className="text-text-faint">—</span>;
  if (typeof v === 'number') return fmtNumber(k, v);
  if (typeof v === 'boolean') return <span className={v ? "text-accent" : "text-text-muted"}>{v ? 'có' : 'không'}</span>;
  if (typeof v === 'string') return <span className="break-all text-text">{v}</span>;
  if (Array.isArray(v)) {
    if (v.length === 0) return <span className="text-text-faint">[ ]</span>;
    if (v.every(x => typeof x !== 'object' || x === null)) {
      return (
        <span className="flex flex-wrap gap-1">
          {v.map((x, i) => <span key={i} className="rounded border border-border bg-bg px-1.5 text-[11.5px]">{String(x)}</span>)}
        </span>
      );
    }
    // Mảng các object phẳng cùng khóa (vd column_time_table của P07) → bảng
    const flat = v.every(x => x && typeof x === 'object' && !Array.isArray(x) && Object.values(x).every(y => y === null || typeof y !== 'object'));
    if (flat) {
      const cols = Array.from(new Set(v.flatMap(x => Object.keys(x))));
      return (
        <div className="mt-1 overflow-x-auto rounded-lg border border-border bg-surface">
          <table className="w-full text-left text-[11.5px]">
            <thead><tr className="border-b border-border bg-surface-2/60">{cols.map(c => <th key={c} className="px-2 py-1 font-normal text-text-faint">{c}</th>)}</tr></thead>
            <tbody>
              {v.map((row, i) => (
                <tr key={i} className="border-t border-border/60 first:border-0">
                  {cols.map(c => <td key={c} className="whitespace-nowrap px-2 py-1"><Value k={c} v={row[c]} depth={depth + 1} /></td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }
    return <div className="flex flex-col gap-1.5">{v.map((x, i) => <Rows key={i} obj={x} depth={depth + 1} />)}</div>;
  }
  return <Rows obj={v} depth={depth + 1} />;
}

function Rows({ obj, depth }: { obj: Record<string, any>; depth: number }) {
  const entries = Object.entries(obj ?? {}).filter(([k]) => k !== '_trimmed');
  if (entries.length === 0) return <span className="text-text-faint">{'{ }'}</span>;
  return (
    <div className={clsx("flex flex-col", depth > 0 && "mt-1 border-l-2 border-border pl-3")}>
      {entries.map(([k, v]) => {
        const nested = v !== null && typeof v === 'object' && !(Array.isArray(v) && v.every(x => typeof x !== 'object'));
        return (
          <div key={k} className={clsx("py-1.5", nested ? "" : "grid grid-cols-[minmax(110px,40%)_1fr] gap-3", depth === 0 && "border-b border-border/70 last:border-0")}>
            <span className="text-text-muted">{k}</span>
            <div className="min-w-0"><Value k={k} v={v} depth={depth} /></div>
          </div>
        );
      })}
    </div>
  );
}

export default function DetailsView({ details }: { details: any }) {
  if (details === null || details === undefined || (typeof details === 'object' && Object.keys(details).length === 0)) {
    return <div className="text-[13px] text-text-faint">Finding này không có chi tiết.</div>;
  }
  return (
    <div className="font-mono text-[12.5px]">
      {typeof details === 'object' ? <Rows obj={details} depth={0} /> : <Value k="" v={details} depth={0} />}
    </div>
  );
}

/** Biến màu cho @uiw/react-json-view theo theme của app (thay theme tối mặc định khó đọc). */
export const jsonViewStyle: React.CSSProperties = {
  '--w-rjv-font-family': '"IBM Plex Mono", ui-monospace, monospace',
  '--w-rjv-background-color': 'transparent',
  '--w-rjv-color': 'rgb(var(--ink))',
  '--w-rjv-key-string': 'rgb(var(--ink))',
  '--w-rjv-line-color': 'rgb(var(--line))',
  '--w-rjv-arrow-color': 'rgb(var(--muted))',
  '--w-rjv-info-color': 'rgb(var(--faint))',
  '--w-rjv-curlybraces-color': 'rgb(var(--muted))',
  '--w-rjv-brackets-color': 'rgb(var(--muted))',
  '--w-rjv-colon-color': 'rgb(var(--faint))',
  '--w-rjv-quotes-color': 'rgb(var(--ink))',
  '--w-rjv-quotes-string-color': 'rgb(var(--accent))',
  '--w-rjv-type-string-color': 'rgb(var(--accent))',
  '--w-rjv-type-int-color': 'rgb(var(--info))',
  '--w-rjv-type-float-color': 'rgb(var(--info))',
  '--w-rjv-type-bigint-color': 'rgb(var(--info))',
  '--w-rjv-type-boolean-color': 'rgb(var(--warn))',
  '--w-rjv-type-null-color': 'rgb(var(--failed))',
  '--w-rjv-type-nan-color': 'rgb(var(--failed))',
  '--w-rjv-type-undefined-color': 'rgb(var(--faint))',
  '--w-rjv-copied-color': 'rgb(var(--muted))',
  '--w-rjv-copied-success-color': 'rgb(var(--accent))',
  fontSize: 12.5,
  lineHeight: 1.6,
} as React.CSSProperties;
