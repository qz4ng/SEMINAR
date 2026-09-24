import { Handle, Position } from '@xyflow/react';
import clsx from 'clsx';
import { Concept, ROLE_META, TONE_META } from '../../content/dataContext';
import { lensAction, ROLES } from '../../data/contextDerive';
import { useUIStore } from '../../store/uiStore';
import { ROLE_CLS, TONE_CLS } from './styles';

const SIDES: [string, Position][] = [['t', Position.Top], ['b', Position.Bottom], ['l', Position.Left], ['r', Position.Right]];

/** Một nút của DAG = một khái niệm (C, K, A, Y…) chứa các cột dữ liệu đo nó. */
export default function ConceptNode({ data }: { data: { concept: Concept; dim: boolean; hot: boolean } }) {
  const { concept: c, dim, hot } = data;
  const lens = useUIStore(s => s.lens);
  const ctxSel = useUIStore(s => s.ctxSel);
  const setCtxSel = useUIStore(s => s.setCtxSel);
  const cls = ROLE_CLS[c.role];
  const selected = ctxSel === `c:${c.id}`;

  return (
    <div
      className={clsx(
        "rounded-[10px] bg-surface transition-[opacity,box-shadow] duration-150",
        dim ? "opacity-35" : "opacity-100",
        selected ? "shadow-lift ring-2 ring-accent ring-offset-2 ring-offset-bg" : hot && "shadow-lift",
      )}
      style={{ width: c.w }}
    >
      {SIDES.map(([id, pos]) => (
        <span key={id}>
          <Handle id={`s${id}`} type="source" position={pos} className="!opacity-0" />
          <Handle id={`t${id}`} type="target" position={pos} className="!opacity-0" />
        </span>
      ))}
      <div className={clsx("rounded-[10px]", c.strong ? "border-2" : "border-[1.5px]", cls.box)}>
        <button className="block w-full px-3 pt-2 pb-1.5 text-left" title={ROLE_META[c.role].label} onClick={(e) => { e.stopPropagation(); setCtxSel(`c:${c.id}`); }}>
          <div className="flex items-baseline gap-1.5">
            <span className={clsx("font-mono text-[13px] font-semibold", cls.text)}>{c.code}</span>
            <span className={clsx("font-display leading-tight text-text", c.strong ? "text-[15px] font-bold" : "text-[13.5px] font-semibold")}>{c.label}</span>
          </div>
        </button>
        <div className={clsx("px-2 pb-2", c.cols === 2 ? "grid grid-cols-2 gap-1" : "flex flex-col gap-1")}>
          {c.vars.length === 0 && <div className="px-1 pb-1 text-[11.5px] italic text-text-faint">không có cột trong dữ liệu</div>}
          {c.vars.map(v => <VarChip key={v} col={v} lens={lens} selected={ctxSel === `v:${v}`} onClick={() => setCtxSel(`v:${v}`)} />)}
        </div>
      </div>
    </div>
  );
}

export function VarChip({ col, lens, selected, onClick }: { col: string; lens: string; selected: boolean; onClick: () => void }) {
  const act = lens === 'roles' ? null : lensAction(lens, col);
  const role = ROLES[col];
  const inL = role?.in_L;
  const ambiguous = role?.dag_role === 'ambiguous';
  const tone = act && !act.rest ? TONE_CLS[act.tone] : null;
  const faded = lens !== 'roles' && (!act || act.rest);

  return (
    <button
      title={act ? `${lens}: ${act.text}` : undefined}
      onClick={(e) => { e.stopPropagation(); onClick(); }}
      className={clsx(
        "flex h-[25px] min-w-0 items-center justify-between gap-1.5 rounded-md border px-2 text-left transition-colors",
        tone ? tone.chip : "border-border bg-surface hover:border-line-strong/60",
        selected && "ring-2 ring-accent",
        faded && "opacity-45",
      )}
    >
      <span className="truncate font-mono text-[12px] text-text">{col}</span>
      {lens === 'roles' && inL && (
        <span className="shrink-0 rounded-[4px] bg-ok px-1 font-mono text-[9.5px] font-semibold leading-[15px] text-accent-ink" title={ambiguous ? 'Trong L ở biến thể O_as_confounder' : 'Trong tập điều chỉnh L'}>
          L{ambiguous ? '*' : ''}
        </span>
      )}
      {tone && act && (
        <span className={clsx("shrink-0 font-mono text-[9.5px] font-semibold uppercase", tone.text)}>{TONE_SHORT[act.tone]}</span>
      )}
    </button>
  );
}

const TONE_SHORT: Record<string, string> = {
  check: 'xem', use: 'dùng', keep: 'giữ', flag: 'cờ', fix: 'sửa', drop: 'bỏ', block: 'chặn', create: 'mới',
};

export { TONE_META };
