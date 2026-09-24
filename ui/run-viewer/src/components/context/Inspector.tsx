import clsx from 'clsx';
import { ArrowRight, ArrowUpRight, Info, MousePointerClick } from 'lucide-react';
import { CONCEPTS, DAG_EDGES, JOURNEYS, LENSES, ROLE_META, TONE_META, VARS, Tone } from '../../content/dataContext';
import { fillText, lensAction, PROFILE, ROLES, RUN_ORDER, conceptOf } from '../../data/contextDerive';
import { RunReport } from '../../data/types';
import { useUIStore } from '../../store/uiStore';
import modulesData from '../../content/modules.json';
import { ROLE_CLS, TONE_CLS } from './styles';
import { MiniDist } from './MiniDist';

/** Mở một bước trong trang Lượt chạy. */
function useOpenStep() {
  const setView = useUIStore(s => s.setView);
  const setSelectedNodeId = useUIStore(s => s.setSelectedNodeId);
  const setDrawerTab = useUIStore(s => s.setDrawerTab);
  return (m: string, tab: 'problem' | 'params' | 'result' = 'result') => { setView('run'); setSelectedNodeId(m); setDrawerTab(tab); };
}

export default function Inspector({ run }: { run: RunReport }) {
  const ctxSel = useUIStore(s => s.ctxSel);
  const lens = useUIStore(s => s.lens);
  let body: React.ReactNode;
  if (ctxSel?.startsWith('v:')) body = <VarView col={ctxSel.slice(2)} run={run} />;
  else if (ctxSel?.startsWith('c:')) body = <ConceptView id={ctxSel.slice(2)} />;
  else if (lens !== 'roles') body = <LensView m={lens} run={run} />;
  else body = <Guide />;
  return <aside className="min-h-0 overflow-y-auto border-l border-border bg-surface px-5 py-4">{body}</aside>;
}

function Title({ kicker, children }: { kicker: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="mb-3">
      <div className="kicker">{kicker}</div>
      <h3 className="mt-1 font-display text-[18px] font-bold leading-snug text-text">{children}</h3>
    </div>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return <div className="section-label mb-1.5 mt-4">{children}</div>;
}

function ToneDot({ tone }: { tone: Tone }) {
  return <span className={clsx("mt-[6px] h-2 w-2 shrink-0 rounded-full", TONE_CLS[tone].dot)} />;
}

// ---- Mặc định: cách đọc ------------------------------------------------------
function Guide() {
  const setCtxSel = useUIStore(s => s.setCtxSel);
  const L = run_L();
  return (
    <div>
      <Title kicker="Cách đọc">DAG v0 gán xuống từng cột</Title>
      <p className="text-[13px] leading-relaxed text-text-muted">
        Mũi tên nghĩa là "ảnh hưởng tới" theo giả định nhân quả (DAG v0, chưa được CIAT xác nhận). Vai trò của từng ô quyết định cột đó có được đưa vào tập điều chỉnh L hay không.
      </p>
      <Label>Vai trò</Label>
      <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
        {(Object.keys(ROLE_META) as (keyof typeof ROLE_META)[]).map(r => (
          <span key={r} className="flex items-center gap-2 text-[12.5px] text-text-muted">
            <span className={clsx("h-3 w-3 rounded-[3px] border-[1.5px]", ROLE_CLS[r].box)} />{ROLE_META[r].label}
          </span>
        ))}
      </div>
      <Label>Mũi tên</Label>
      <div className="flex flex-col gap-1 text-[12.5px] text-text-muted">
        <span className="flex items-center gap-2"><svg width="28" height="6"><line x1="0" y1="3" x2="28" y2="3" stroke="rgb(var(--ink))" strokeWidth="2.6" /></svg>A → Y: tác động cần ước lượng</span>
        <span className="flex items-center gap-2"><svg width="28" height="6"><line x1="0" y1="3" x2="28" y2="3" stroke="rgb(var(--line-strong))" strokeWidth="1.4" /></svg>quan hệ nhân quả giả định</span>
        <span className="flex items-center gap-2"><svg width="28" height="6"><line x1="0" y1="3" x2="28" y2="3" stroke="rgb(var(--line-strong))" strokeWidth="1.4" strokeDasharray="5 4" /></svg>chưa chắc, hoặc qua biến không đo được</span>
      </div>
      <Label>Tập điều chỉnh L · {L.length} cột</Label>
      <div className="flex flex-wrap gap-1">
        {L.map(c => (
          <button key={c} onClick={() => setCtxSel(`v:${c}`)} className="rounded-md border border-ok/40 bg-ok/[0.08] px-1.5 py-[1px] font-mono text-[11.5px] text-text hover:border-ok">
            {c}{ROLES[c]?.dag_role === 'ambiguous' && <span className="text-ok">*</span>}
          </button>
        ))}
      </div>
      <p className="mt-1.5 text-[11.5px] text-text-faint">* chỉ có trong biến thể O_as_confounder. Trên DAG, cột trong L mang nhãn <span className="rounded-[3px] bg-ok px-1 font-mono text-[9.5px] text-accent-ink">L</span>.</p>
      <div className="mt-4 flex gap-2 rounded-lg border border-warn/30 bg-warn/[0.07] px-3 py-2.5 text-[12.5px] leading-relaxed text-text-muted">
        <Info className="mt-[3px] h-3.5 w-3.5 shrink-0 text-warn" />
        <span>Dữ liệu mock sinh các cột <b className="text-text">độc lập với nhau</b> (chỉ soil_om_post_pct phụ thuộc đất nền). Mũi tên ở đây là giả định để gán vai trò, chưa phải cơ chế sinh dữ liệu — không dùng mock này để ước lượng tác động.</span>
      </div>
      <div className="mt-4 flex items-center gap-2 text-[12px] text-text-faint"><MousePointerClick className="h-3.5 w-3.5" />Nhấn một ô hoặc một cột trên DAG để xem chi tiết.</div>
    </div>
  );
}

function run_L(): string[] {
  return (Object.values(ROLES) as any[]).filter(r => r.in_L).map(r => r.column).sort();
}

// ---- Một khái niệm -------------------------------------------------------------
function ConceptView({ id }: { id: string }) {
  const cp = CONCEPTS.find(c => c.id === id)!;
  const setCtxSel = useUIStore(s => s.setCtxSel);
  const outs = DAG_EDGES.filter(e => e[0] === id).map(e => e[1]);
  const ins = DAG_EDGES.filter(e => e[1] === id).map(e => e[0]);
  const name = (x: string) => CONCEPTS.find(c => c.id === x)!;
  const Link = ({ x }: { x: string }) => (
    <button onClick={() => setCtxSel(`c:${x}`)} className={clsx("rounded-md border px-1.5 py-[1px] text-[12px] hover:bg-surface-2", ROLE_CLS[name(x).role].chip)}>
      <span className={clsx("font-mono font-semibold", ROLE_CLS[name(x).role].text)}>{name(x).code}</span> {name(x).label}
    </button>
  );
  return (
    <div>
      <Title kicker={<span className={ROLE_CLS[cp.role].text}>{ROLE_META[cp.role].label}</span>}>
        <span className={clsx("font-mono", ROLE_CLS[cp.role].text)}>{cp.code}</span> · {cp.label}
      </Title>
      <dl className="flex flex-col gap-2">
        {cp.info.map(([k, v]) => (
          <div key={k} className="grid grid-cols-[88px_1fr] gap-2 text-[13px]">
            <dt className="text-text-faint">{k}</dt><dd className="leading-relaxed text-text-muted">{v}</dd>
          </div>
        ))}
      </dl>
      {(ins.length > 0 || outs.length > 0) && (
        <>
          <Label>Mũi tên</Label>
          {ins.length > 0 && <div className="mb-1.5 flex flex-wrap items-center gap-1 text-[12px] text-text-faint">bị ảnh hưởng bởi {ins.map(x => <Link key={x} x={x} />)}</div>}
          {outs.length > 0 && <div className="flex flex-wrap items-center gap-1 text-[12px] text-text-faint">ảnh hưởng tới {outs.map(x => <Link key={x} x={x} />)}</div>}
        </>
      )}
      <Label>Cột dữ liệu · {cp.vars.length}</Label>
      <div className="flex flex-col gap-1">
        {cp.vars.length === 0 && <div className="text-[12.5px] italic text-text-faint">Không có cột nào đo khái niệm này.</div>}
        {cp.vars.map(v => (
          <button key={v} onClick={() => setCtxSel(`v:${v}`)} className="flex items-center justify-between rounded-lg border border-border px-2.5 py-1.5 text-left hover:border-line-strong/60">
            <span><span className="font-mono text-[12px] text-text">{v}</span><span className="ml-2 text-[12px] text-text-muted">{VARS[v]?.label}</span></span>
            {ROLES[v]?.in_L && <span className="rounded-[3px] bg-ok px-1 font-mono text-[9.5px] text-accent-ink">L</span>}
          </button>
        ))}
      </div>
    </div>
  );
}

// ---- Một cột -------------------------------------------------------------------
function VarView({ col, run }: { col: string; run: RunReport }) {
  const v = VARS[col];
  const r = ROLES[col];
  const cp = conceptOf(col);
  const prof = PROFILE.columns[col];
  const lens = useUIStore(s => s.lens);
  const setLens = useUIStore(s => s.setLens);
  const setCtxSel = useUIStore(s => s.setCtxSel);
  const journeys = JOURNEYS.filter(j => j.cols.includes(col));
  const steps = RUN_ORDER.map(m => ({ m, a: lensAction(m, col) })).filter(x => x.a);

  const facts: [string, React.ReactNode][] = [
    ['Kiểu', r?.dtype ?? 'chuỗi (ngoài schema)'],
    ['Đơn vị', v?.unit ?? '—'],
    ['Đo lúc', r?.measured_at ? <span className={r.measured_at === 'post' ? 'text-blocked' : ''}>{({ pre: 'trước time zero', at: 'tại time zero', post: 'SAU time zero' } as any)[r.measured_at]}</span> : 'không rõ'],
    ['Vai trò', r?.dag_role ?? '—'],
    ['Trong L', r?.in_L ? <span className="text-ok">có{r.dag_role === 'ambiguous' ? ' (biến thể O_as_confounder)' : ''}</span> : 'không'],
  ];

  return (
    <div>
      <Title kicker={cp ? <button onClick={() => setCtxSel(`c:${cp.id}`)} className={clsx("hover:underline", ROLE_CLS[cp.role].text)}>{cp.code} · {cp.label}</button> : 'Cột'}>
        <span className="font-mono">{col}</span>
      </Title>
      <div className="-mt-2 mb-2 text-[13.5px] font-medium text-text">{v?.label}</div>
      <p className="text-[13px] leading-relaxed text-text-muted">{v?.desc}</p>

      <div className="mt-3 grid grid-cols-2 gap-1.5">
        {facts.map(([k, val]) => (
          <div key={k} className="rounded-lg border border-border px-2.5 py-1.5">
            <div className="section-label">{k}</div>
            <div className="mt-0.5 font-mono text-[12px] text-text">{val}</div>
          </div>
        ))}
      </div>

      <Label>Trong dữ liệu mock</Label>
      <p className="mb-2 text-[12.5px] leading-relaxed text-text-muted"><span className="text-text-faint">Sinh ra: </span>{v?.mock}</p>
      <div className="grid grid-cols-2 gap-1.5">
        <MiniDist p={prof?.raw} label="Thô" />
        <MiniDist p={prof?.final} label="Sau tiền xử lý" accent />
      </div>
      {journeys.length > 0 && (
        <div className="mt-2 flex flex-col gap-1">
          {journeys.map(j => (
            <div key={j.title} className="flex items-start gap-2 rounded-lg border border-blocked/25 bg-blocked/[0.05] px-2.5 py-1.5 text-[12px]">
              <span className="mt-[5px] h-1.5 w-1.5 shrink-0 rounded-full bg-blocked" />
              <span><b className="font-medium text-text">Lỗi cài: {j.title}</b> <span className="text-text-muted">— {j.n}. {j.outcome}</span></span>
            </div>
          ))}
        </div>
      )}

      <Label>Các bước xử lý cột này</Label>
      <ol className="relative flex flex-col">
        {steps.map(({ m, a }, i) => (
          <li key={m} className="relative flex gap-2.5 pb-2">
            {i < steps.length - 1 && <span className="absolute left-[15px] top-6 bottom-0 w-px bg-border" />}
            <button
              onClick={() => setLens(m)} title={`Xem DAG qua lăng kính ${m}`}
              className={clsx("z-[1] h-6 w-8 shrink-0 rounded-md border font-mono text-[10.5px] font-semibold",
                lens === m ? "border-text bg-text text-bg" : clsx(TONE_CLS[a!.tone].chip, TONE_CLS[a!.tone].text))}
            >{m}</button>
            <div className={clsx("min-w-0 pt-[3px] text-[12.5px] leading-snug", a!.rest ? "text-text-faint" : "text-text-muted")}>
              <span className={clsx("mr-1 font-medium", TONE_CLS[a!.tone].text)}>{TONE_META[a!.tone].label}.</span>
              {fillText(a!.text, run)}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

// ---- Lăng kính một module ------------------------------------------------------
function LensView({ m, run }: { m: string; run: RunReport }) {
  const mod = modulesData.modules.find(x => x.id === m)!;
  const lens = LENSES[m];
  const openStep = useOpenStep();
  const setCtxSel = useUIStore(s => s.setCtxSel);
  const allCols = CONCEPTS.flatMap(c => c.vars);
  const acts = allCols.map(col => ({ col, a: lensAction(m, col) })).filter(x => x.a && !x.a.rest);
  const rest = allCols.map(col => ({ col, a: lensAction(m, col) })).filter(x => x.a?.rest);
  // P08 là bước dựng L: đưa các cột vào L lên đầu; các bước khác: tác động mạnh lên đầu
  const order: Tone[] = m === 'P08' ? ['keep', 'block', 'check'] : ['drop', 'block', 'fix', 'flag', 'create', 'keep', 'use', 'check'];
  acts.sort((x, y) => order.indexOf(x.a!.tone) - order.indexOf(y.a!.tone));

  return (
    <div>
      <Title kicker={`Lăng kính · bước ${RUN_ORDER.indexOf(m) + 1}/9`}>
        <span className="font-mono text-accent">{m}</span> {mod.name}
      </Title>
      <p className="text-[13px] leading-relaxed text-text-muted">{lens.summary}</p>
      <button onClick={() => openStep(m)} className="mt-2 inline-flex items-center gap-1 text-[12.5px] font-medium text-accent hover:underline">
        Mở {m} trong Lượt chạy <ArrowUpRight className="h-3.5 w-3.5" />
      </button>

      <Label>Việc làm với từng cột · {acts.length}</Label>
      <div className="flex flex-col gap-1">
        {acts.map(({ col, a }) => (
          <button key={col} onClick={() => setCtxSel(`v:${col}`)} className="flex gap-2 rounded-lg border border-border px-2.5 py-1.5 text-left hover:border-line-strong/60">
            <ToneDot tone={a!.tone} />
            <span className="min-w-0 text-[12.5px] leading-snug">
              <span className="font-mono text-[12px] text-text">{col}</span>
              <span className={clsx("ml-1.5 text-[11px]", TONE_CLS[a!.tone].text)}>{TONE_META[a!.tone].label}</span>
              <span className="block text-text-muted">{fillText(a!.text, run)}</span>
            </span>
          </button>
        ))}
      </div>
      {rest.length > 0 && LENSES[m]?.rest && (
        <p className="mt-2 text-[12px] text-text-faint">{rest.length} cột còn lại: {LENSES[m].rest![1].toLowerCase()}</p>
      )}
      {lens.creates.length > 0 && (
        <>
          <Label>Sinh thêm cột</Label>
          <div className="flex flex-col gap-1">
            {lens.creates.map(([c, d]) => (
              <div key={c} className="flex items-start gap-2 text-[12.5px]">
                <ArrowRight className="mt-[3px] h-3 w-3 shrink-0 text-teal" />
                <span><span className="font-mono text-[12px] text-text">{c}</span> <span className="text-text-muted">— {fillText(d, run)}</span></span>
              </div>
            ))}
          </div>
        </>
      )}
      <Label>Chú giải</Label>
      <div className="grid grid-cols-2 gap-x-3 gap-y-1">
        {(['drop', 'block', 'fix', 'flag', 'create', 'keep', 'use', 'check'] as Tone[]).map(t => (
          <span key={t} className="flex items-center gap-1.5 text-[11.5px] text-text-muted"><span className={clsx("h-2 w-2 rounded-full", TONE_CLS[t].dot)} />{TONE_META[t].label}</span>
        ))}
      </div>
    </div>
  );
}
