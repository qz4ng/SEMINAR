import { useState } from 'react';
import { useUIStore } from '../store/uiStore';
import { RunReport } from '../data/types';
import { StatusBadge } from './common/StatusBadge';
import { Copy, Check, Sun, Moon } from 'lucide-react';
import { finalRowCount, stepsInRunOrder, visibleFindings } from '../data/derive';
import modulesData from '../content/modules.json';
import { PROFILE } from '../data/contextDerive';
import { ROLE_META, Role } from '../content/dataContext';
import { ROLE_CLS } from './context/styles';
import clsx from 'clsx';

/** Chip mono viền mảnh, bấm để chép (run_id, digest). */
function CopyChip({ label, value, title }: { label?: string; value: string; title?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      title={title ?? 'Bấm để chép'}
      className="chip group hover:border-line-strong/60 hover:text-text transition-colors"
      onClick={() => {
        navigator.clipboard?.writeText(value);
        setCopied(true);
        setTimeout(() => setCopied(false), 1200);
      }}
    >
      {label && <span className="text-text-faint">{label}</span>}
      <span>{value}</span>
      {copied ? <Check className="w-3 h-3 text-accent" /> : <Copy className="w-3 h-3 opacity-40 group-hover:opacity-90" />}
    </button>
  );
}

function Stat({ label, children, className }: { label: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={clsx("flex flex-col gap-0.5 px-5 first:pl-0", className)}>
      <span className="section-label">{label}</span>
      <span className="font-display text-[17px] font-semibold leading-tight text-text tabular-nums">{children}</span>
    </div>
  );
}

export default function RunHeader({ run }: { run: RunReport }) {
  const theme = useUIStore(s => s.theme);
  const setTheme = useUIStore(s => s.setTheme);
  const setSelectedNodeId = useUIStore(s => s.setSelectedNodeId);
  const view = useUIStore(s => s.view);
  const setView = useUIStore(s => s.setView);

  const steps = stepsInRunOrder(run, modulesData.modules as any);
  const finalRows = finalRowCount(run, modulesData.modules as any);
  const nWarn = steps.filter(s => s.status === 'warning').length;
  const nRan = steps.filter(s => s.status !== 'not_run').length;
  const nFindings = steps.reduce((acc, s) => acc + visibleFindings(s).length, 0);
  const inputName = run.input.path.split('/').pop();
  const started = new Date(run.started_at);
  const ds = PROFILE.dataset;

  return (
    <header className="shrink-0 border-b border-border bg-bg px-6 pt-4 z-20">
      <div className="flex items-end justify-between gap-6">
        <div className="min-w-0">
          <div className="kicker">ra_causal · tiền xử lý · P01 → P09</div>
          <div className="mt-1 flex items-center gap-3">
            <h1 className="font-display text-[26px] font-bold leading-none tracking-[-0.01em] text-text">
              {view === 'run' ? 'Lượt chạy tiền xử lý' : 'Bối cảnh dữ liệu'}
            </h1>
            {view === 'run' && <StatusBadge status={run.status} />}
            {view === 'run' && run.failed_step && (
              <button className="chip hover:text-text" onClick={() => setSelectedNodeId(run.failed_step)}>
                dừng tại {run.failed_step}
              </button>
            )}
          </div>
        </div>

        <div className="flex items-end">
          {view === 'run' ? (
            <div className="flex items-end divide-x divide-border">
              <Stat label="Số dòng">
                {run.input.n_rows}
                <span className="mx-1.5 text-text-faint">→</span>
                {finalRows ?? '—'}
                {finalRows !== null && finalRows < run.input.n_rows && (
                  <span className="ml-1.5 font-mono text-[12px] font-medium text-blocked">−{run.input.n_rows - finalRows}</span>
                )}
              </Stat>
              <Stat label="Bước">
                {nRan}/{steps.length}
                {nWarn > 0 && <span className="ml-1.5 font-sans text-[12px] font-medium text-warn">{nWarn} cảnh báo</span>}
              </Stat>
              <Stat label="Phát hiện">{nFindings}</Stat>
              <Stat label="Thời gian">{run.duration_s.toFixed(2)}<span className="ml-0.5 text-[13px] text-text-muted">s</span></Stat>
            </div>
          ) : (
            <div className="flex items-end divide-x divide-border">
              <Stat label="Dòng × cột thô">{ds.raw.rows} × {ds.raw.cols}</Stat>
              <Stat label="Nông hộ">{ds.raw.growers}</Stat>
              <Stat label="Quốc gia · năm">4 · {ds.raw.years[0]}–{String(ds.raw.years[1]).slice(2)}</Stat>
              <Stat label="Tập L">{run.context_final.adjustment_set.length}<span className="ml-1 text-[13px] text-text-muted">cột</span></Stat>
            </div>
          )}
          <button
            className="ml-6 mb-0.5 flex h-8 w-8 items-center justify-center rounded-full border border-border bg-surface text-text-muted hover:text-text hover:border-line-strong/60 transition-colors"
            title={theme === 'dark' ? 'Chuyển sang nền sáng' : 'Chuyển sang nền tối'}
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>
      </div>

      <div className="mt-3 flex items-end justify-between gap-4">
        <nav className="-mb-px flex shrink-0 gap-6">
          {([['run', '01', 'Lượt chạy'], ['context', '02', 'Bối cảnh dữ liệu']] as const).map(([v, n, label]) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={clsx(
                "flex items-baseline gap-1.5 border-b-2 pb-2.5 text-[14px] font-semibold transition-colors",
                view === v ? "border-accent text-text" : "border-transparent text-text-muted hover:text-text",
              )}
            >
              <span className="font-mono text-[11px] font-normal text-text-faint">{n}</span>{label}
            </button>
          ))}
        </nav>
        <div className="flex min-w-0 items-center gap-4 pb-2.5">
          {view === 'run' ? (
            <>
              <div className="flex min-w-0 items-center gap-1.5">
                <CopyChip label="run" value={run.run_id} />
                <CopyChip label="digest" value={run.config_digest} title="Mã băm cấu hình — hai lần chạy cùng mã dùng cùng tham số. Bấm để chép." />
                <span className="chip" title={`${run.input.path}\nschema v${run.schema_version} · ${started.toLocaleString('vi-VN')}`}>
                  <span className="text-text-faint">vào</span>{inputName} · {run.input.n_cols} cột
                </span>
              </div>
              <Legend />
            </>
          ) : (
            <RoleLegend />
          )}
        </div>
      </div>
    </header>
  );
}

function RoleLegend() {
  return (
    <div className="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[11px] text-text-muted">
      {(Object.keys(ROLE_META) as Role[]).map(r => (
        <span key={r} className="inline-flex items-center gap-1.5">
          <span className={clsx("h-2.5 w-2.5 rounded-[3px] border", ROLE_CLS[r].box)} />{ROLE_META[r].label.toLowerCase()}
        </span>
      ))}
    </div>
  );
}

/** Chú giải màu, đặt như hàng chip chú giải của Atlas. */
function Legend() {
  const item = (cls: string, label: string, dashed = false) => (
    <span className="inline-flex items-center gap-1.5">
      <span className={clsx("h-2.5 w-2.5 rounded-[3px] border", cls, dashed && "border-dashed")} />
      {label}
    </span>
  );
  return (
    <div className="flex shrink-0 items-center gap-3.5 font-mono text-[11px] text-text-muted">
      {item("bg-ok/25 border-ok", "ổn")}
      {item("bg-warn/25 border-warn", "cảnh báo")}
      {item("bg-blocked/25 border-blocked", "bị chặn")}
      {item("bg-failed/25 border-failed", "lỗi")}
      {item("bg-transparent border-line-strong", "chưa chạy", true)}
      <span className="h-3 w-px bg-border" />
      <span className="inline-flex items-center gap-1.5"><svg width="22" height="6"><line x1="0" y1="3" x2="22" y2="3" stroke="rgb(var(--line-strong))" strokeWidth="1.6" /></svg>dữ liệu</span>
      <span className="inline-flex items-center gap-1.5"><svg width="22" height="6"><line x1="0" y1="3" x2="22" y2="3" stroke="rgb(var(--context))" strokeWidth="1.6" strokeDasharray="4 3" /></svg>context</span>
    </div>
  );
}
