import clsx from 'clsx';
import { ArrowRight, CircleCheck, Flag, CircleAlert, Target, Rows3, Clock3, Database } from 'lucide-react';
import { RunReport } from '../../data/types';
import { CONCEPTS, JOURNEYS, ROLE_META, VARS, Verdict } from '../../content/dataContext';
import { PROFILE, ROLES, conceptOf } from '../../data/contextDerive';
import { useUIStore } from '../../store/uiStore';
import { ROLE_CLS, TONE_CLS } from './styles';
import DagBoard from './DagBoard';

/** Trang "Bối cảnh dữ liệu": bài toán → DAG gán xuống từng cột → lỗi cài trong mock → từ điển biến. */
export default function ContextPage({ run }: { run: RunReport }) {
  return (
    <div id="ctx-scroll" className="min-w-0 flex-1 overflow-y-auto">
      <div className="mx-auto flex max-w-[1560px] flex-col gap-10 px-8 py-7">
        <Problem />
        <div id="ctx-dag"><DagBoard run={run} /></div>
        <Journeys />
        <Dictionary />
      </div>
    </div>
  );
}

// ---- 01 · Bài toán ------------------------------------------------------------
function Problem() {
  const ds = PROFILE.dataset;
  const cards: { icon: any; title: string; body: React.ReactNode }[] = [
    { icon: Target, title: 'Câu hỏi', body: <>Trồng <b className="font-medium text-text">cây che phủ</b> (A) trong mùa nghỉ trước vụ có làm tăng <b className="font-medium text-text">năng suất khoai tây</b> (Y) không? Dữ liệu quan sát, không có phân nhóm ngẫu nhiên.</> },
    { icon: Rows3, title: 'Một dòng là gì', body: <>Một <b className="font-medium text-text">ruộng trong một mùa vụ</b>. Khóa nghiệp vụ grower_id + field_id + year; một nông hộ có nhiều dòng → cụm.</> },
    { icon: Clock3, title: 'Time zero', body: <>Lúc <b className="font-medium text-text">quyết định trồng cây che phủ</b>. Biến đo trước được điều chỉnh; biến đo sau (đất sau áp dụng, cỏ dại, tham gia chương trình) bị chặn.</> },
    { icon: Database, title: 'Dữ liệu mẫu', body: <><b className="font-medium text-text">{ds.raw.rows} dòng × {ds.raw.cols} cột</b> thô → {ds.final.rows} × {ds.final.cols} sau tiền xử lý. {ds.raw.growers} nông hộ, 4 nước, {ds.raw.years[0]}–{ds.raw.years[1]}. A = 1: {ds.raw.cover_crop_true} dòng (khai báo) → {ds.final.treated} (định nghĩa ≥ 2 tháng).</> },
  ];
  return (
    <section>
      <div className="kicker">01 · Bài toán</div>
      <h2 className="mt-1 font-display text-[20px] font-bold text-text">Dữ liệu này đo cái gì</h2>
      <div className="mt-3 grid grid-cols-4 gap-3">
        {cards.map(c => (
          <div key={c.title} className="rounded-xl border border-border bg-surface px-4 py-3.5">
            <div className="flex items-center gap-2 text-[13px] font-semibold text-text"><c.icon className="h-4 w-4 text-accent" />{c.title}</div>
            <p className="mt-1.5 text-[13px] leading-relaxed text-text-muted">{c.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

// ---- 03 · Lỗi cài trong mock --------------------------------------------------
const VERDICT: Record<Verdict, { label: string; icon: any; cls: string }> = {
  done: { label: 'Đã xử lý', icon: CircleCheck, cls: 'text-ok border-ok/40 bg-ok/[0.08]' },
  flagged: { label: 'Còn cờ, xử lý ở giai đoạn sau', icon: Flag, cls: 'text-info border-info/40 bg-info/[0.08]' },
  open: { label: 'Còn tồn trong analysis_ready', icon: CircleAlert, cls: 'text-blocked border-blocked/40 bg-blocked/[0.08]' },
};

function Journeys() {
  const setView = useUIStore(s => s.setView);
  const setSelectedNodeId = useUIStore(s => s.setSelectedNodeId);
  const setDrawerTab = useUIStore(s => s.setDrawerTab);
  const setCtxSel = useUIStore(s => s.setCtxSel);
  const count = (v: Verdict) => JOURNEYS.filter(j => j.verdict === v).length;
  const focusVar = (c: string) => { setCtxSel(`v:${c}`); document.getElementById('ctx-dag')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); };

  return (
    <section>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="kicker">03 · Dữ liệu bẩn đi qua pipeline</div>
          <h2 className="mt-1 font-display text-[20px] font-bold text-text">Lỗi được cài vào mock, và bước nào bắt được</h2>
          <p className="mt-1 max-w-[820px] text-[13px] leading-relaxed text-text-muted">
            Mock được làm bẩn có chủ đích (tests/fixtures/make_frames.py). Mỗi thẻ đi theo một loại lỗi từ lúc vào đến khi ra khỏi P09. Nhấn tên bước để mở bước đó trong Lượt chạy, nhấn tên cột để xem trên DAG.
          </p>
        </div>
        <div className="flex gap-2">
          {(['done', 'flagged', 'open'] as Verdict[]).map(v => {
            const V = VERDICT[v];
            return <span key={v} className={clsx("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[12px]", V.cls)}><V.icon className="h-3.5 w-3.5" />{V.label} · {count(v)}</span>;
          })}
        </div>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 xl:grid-cols-3">
        {JOURNEYS.map(j => {
          const V = VERDICT[j.verdict];
          return (
            <div key={j.title} className="flex flex-col rounded-xl border border-border bg-surface px-4 py-3.5">
              <div className="flex items-start justify-between gap-2">
                <div className="font-display text-[14.5px] font-semibold text-text">{j.title}</div>
                <span className={clsx("inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-[1px] text-[11px]", V.cls)} title={V.label}><V.icon className="h-3 w-3" />{j.n}</span>
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-1">
                {j.cols.map(c => (
                  <button key={c} onClick={() => focusVar(c)} className="rounded-md border border-border px-1.5 font-mono text-[11px] text-text-muted hover:border-line-strong/60 hover:text-text">{c}</button>
                ))}
                <span className="text-[12px] text-text-faint">· {j.injected}</span>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-1">
                <span className="rounded-md bg-surface-2 px-1.5 py-[2px] font-mono text-[10.5px] text-text-faint">vào</span>
                {j.steps.map(([m, tone, text]) => (
                  <span key={m + text} className="inline-flex items-center gap-1">
                    <ArrowRight className="h-3 w-3 text-text-faint" />
                    <button
                      onClick={() => { setView('run'); setSelectedNodeId(m); setDrawerTab('result'); }}
                      className={clsx("inline-flex items-center gap-1.5 rounded-md border px-1.5 py-[2px] text-[11.5px] hover:brightness-95", TONE_CLS[tone].chip)}
                      title={`Mở ${m} trong Lượt chạy`}
                    >
                      <span className={clsx("font-mono font-semibold", TONE_CLS[tone].text)}>{m}</span>
                      <span className="text-text-muted">{text}</span>
                    </button>
                  </span>
                ))}
              </div>
              <p className="mt-3 border-t border-border/70 pt-2 text-[12.5px] leading-relaxed text-text-muted">
                <span className={clsx("mr-1 font-medium", V.cls.split(' ')[0])}>Kết quả:</span>{j.outcome}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}

// ---- 04 · Từ điển biến ---------------------------------------------------------
function Dictionary() {
  const setCtxSel = useUIStore(s => s.setCtxSel);
  const rows = CONCEPTS.flatMap(cp => cp.vars.map(col => ({ col, cp })));
  const pct = (p: any) => (p && p.n ? p.missing : null);
  return (
    <section className="pb-10">
      <div className="kicker">04 · Từ điển biến</div>
      <h2 className="mt-1 font-display text-[20px] font-bold text-text">{rows.length} cột trong dữ liệu thô</h2>
      <div className="mt-3 overflow-hidden rounded-xl border border-border bg-surface">
        <table className="w-full text-left text-[12.5px]">
          <thead>
            <tr className="border-b border-border bg-surface-2/60">
              {['Cột', 'Ý nghĩa', 'Nhóm DAG', 'Đo lúc', 'Đơn vị', 'Thiếu thô → sau', 'L', 'Cách mock sinh'].map(h => (
                <th key={h} className="px-3 py-2 section-label font-normal">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(({ col, cp }) => {
              const r = ROLES[col]; const p = PROFILE.columns[col]; const v = VARS[col];
              return (
                <tr key={col} onClick={() => { setCtxSel(`v:${col}`); document.getElementById('ctx-dag')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }}
                  className="cursor-pointer border-t border-border/60 first:border-0 hover:bg-surface-2/50">
                  <td className="px-3 py-1.5 font-mono text-[12px] text-text">{col}</td>
                  <td className="px-3 py-1.5 text-text-muted">{v?.label}</td>
                  <td className="px-3 py-1.5">
                    <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-text-muted">
                      <span className={clsx("h-2.5 w-2.5 rounded-[3px]", ROLE_CLS[cp.role].dot)} />
                      <span className={clsx("font-mono", ROLE_CLS[cp.role].text)}>{cp.code}</span> {ROLE_META[cp.role].label}
                    </span>
                  </td>
                  <td className={clsx("px-3 py-1.5 font-mono text-[11.5px]", r?.measured_at === 'post' ? 'text-blocked' : 'text-text-muted')}>{r?.measured_at ?? '—'}</td>
                  <td className="px-3 py-1.5 text-text-muted">{v?.unit ?? '—'}</td>
                  <td className="px-3 py-1.5 font-mono text-[11.5px] text-text-muted">
                    <span className={pct(p?.raw) ? 'text-warn' : ''}>{pct(p?.raw) ?? '—'}</span> → <span>{p?.final ? pct(p.final) : '—'}</span>
                  </td>
                  <td className="px-3 py-1.5">{r?.in_L && <span className="rounded-[3px] bg-ok px-1 font-mono text-[9.5px] text-accent-ink">L{r.dag_role === 'ambiguous' ? '*' : ''}</span>}</td>
                  <td className="px-3 py-1.5 text-[12px] text-text-faint">{v?.mock}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-[12px] text-text-faint">Nhấn một dòng để xem cột đó trên DAG. Vai trò theo configs/schema/canonical.yaml (giả định DAG v0, chưa được CIAT xác nhận).</p>
    </section>
  );
}

export { conceptOf };
