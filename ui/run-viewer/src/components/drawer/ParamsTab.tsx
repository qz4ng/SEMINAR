import { StepReport } from '../../data/types';
import paramsData from '../../mock/params.json';
import paramGuide from '../../content/param_guide.json';
import { changedParams } from '../../data/derive';
import { useUIStore } from '../../store/uiStore';
import { useState, useEffect, useMemo } from 'react';
import { Copy, ChevronDown, ArrowUp, ArrowDown, Info, CircleSlash, Check } from 'lucide-react';
import * as Accordion from '@radix-ui/react-accordion';
import { ImpactTag, Impact } from '../common/ImpactTag';
import clsx from 'clsx';

// ---- Kiểu dữ liệu của content/param_guide.json -------------------------------
interface Option { value: any; label: string; effect: string; tags: Impact[]; implemented: boolean }
interface When { param?: string; in?: any[]; valuesOf?: string; contains?: any; any?: When[] }
interface Guide {
  kind: 'enum' | 'enum_map' | 'multi' | 'number' | 'list' | 'string' | 'map' | 'fields';
  ask: string;
  options?: Option[];
  fields?: Record<string, string>;
  explain?: string;
  map_explain?: string;
  up?: string;
  down?: string;
  note?: string;
  tags?: Impact[];
  when?: When;
  when_text?: string;
}

const same = (a: any, b: any) => JSON.stringify(a) === JSON.stringify(b);
const show = (v: any) => (typeof v === 'string' ? v : JSON.stringify(v));

/** Tham số có tác dụng với cấu hình hiện tại không (vd iqr_k chỉ dùng khi có cột chạy iqr). */
function isActive(when: When | undefined, params: Record<string, any>): boolean {
  if (!when) return true;
  if (when.any) return when.any.some(w => isActive(w, params));
  if (when.valuesOf) return Object.values(params[when.valuesOf] ?? {}).some(v => when.in!.some(x => same(x, v)));
  if (when.contains !== undefined) return Array.isArray(params[when.param!]) && params[when.param!].includes(when.contains);
  return (when.in ?? []).some(x => same(x, params[when.param!]));
}

const SECTIONS: { id: string; title: string; hint: string; kinds: Guide['kind'][] }[] = [
  { id: 'decide', title: 'Quyết định xử lý', hint: 'mỗi giá trị là một cách xử lý khác nhau', kinds: ['enum', 'enum_map', 'multi'] },
  { id: 'number', title: 'Ngưỡng & con số', hint: 'tăng hay giảm thì kết quả đổi thế nào', kinds: ['number'] },
  { id: 'config', title: 'Cột & cấu hình', hint: 'áp lên những cột nào', kinds: ['list', 'string', 'map', 'fields'] },
];

export default function ParamsTab({ step }: { step: StepReport }) {
  const [viewMode, setViewMode] = useState<'guide' | 'yaml'>('guide');
  const id = step.module_id;
  const defaults: Record<string, any> = (paramsData as any)[id]?.defaults || {};
  const guides: Record<string, Guide> = (paramGuide as any)[id] || {};
  const isNotRun = step.status === 'not_run';
  const current: Record<string, any> = isNotRun ? defaults : (step.params_effective || defaults);
  const changed = isNotRun ? [] : changedParams(step, defaults);
  const keys = Object.keys(defaults);
  const inactive = keys.filter(k => !isActive(guides[k]?.when, current));

  const grouped = useMemo(() => SECTIONS.map(sec => {
    const ks = keys.filter(k => sec.kinds.includes(guides[k]?.kind ?? 'string'));
    // Tham số đã đổi lên đầu, tham số không có tác dụng xuống cuối
    const rank = (k: string) => (changed.includes(k) ? 0 : inactive.includes(k) ? 2 : 1);
    return { ...sec, keys: [...ks].sort((a, b) => rank(a) - rank(b)) };
  }).filter(s => s.keys.length > 0), [id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Mở sẵn tham số đã đổi; không có thì mở tham số quyết định đầu tiên để thấy ngay lớp "giá trị → cách xử lý".
  const initialOpen = changed.length ? changed : grouped[0]?.keys.slice(0, 1) ?? [];
  const [open, setOpen] = useState<string[]>(initialOpen);
  useEffect(() => setOpen(initialOpen), [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const tagsHere = useMemo(() => {
    const s = new Set<Impact>();
    keys.forEach(k => {
      guides[k]?.options?.forEach(o => { o.tags.forEach(t => s.add(t)); if (!o.implemented) s.add('noop'); });
      guides[k]?.tags?.forEach(t => s.add(t));
    });
    return (['stop', 'drop', 'modify', 'flag', 'cols', 'select', 'report', 'noop'] as Impact[]).filter(t => s.has(t));
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex flex-col gap-5 px-6 py-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="font-display text-[15px] font-semibold text-text">
            {keys.length} tham số
            <span className="ml-2 font-sans text-[13px] font-normal text-text-muted">
              {isNotRun ? '· giá trị mặc định (bước chưa chạy)' : changed.length ? `· ${changed.length} khác mặc định` : '· đều đang ở mặc định'}
              {inactive.length > 0 && ` · ${inactive.length} không có tác dụng với cấu hình này`}
            </span>
          </div>
          <p className="mt-1 text-[12.5px] leading-relaxed text-text-muted">
            Mở một tham số để xem nó nhận những giá trị nào và mỗi giá trị xử lý dữ liệu ra sao.
          </p>
        </div>
        <Segmented value={viewMode} onChange={setViewMode} options={[['guide', 'Giải thích'], ['yaml', 'YAML']]} />
      </div>

      {viewMode === 'guide' ? (
        <>
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="section-label mr-1">Tác động</span>
            {tagsHere.map(t => <ImpactTag key={t} tag={t} />)}
          </div>

          <div className="flex items-center justify-end gap-3 -mb-2 text-[12px]">
            <button className="text-text-muted hover:text-accent" onClick={() => setOpen(keys)}>Mở tất cả</button>
            <span className="h-3 w-px bg-border" />
            <button className="text-text-muted hover:text-accent" onClick={() => setOpen([])}>Thu gọn</button>
          </div>

          <Accordion.Root type="multiple" value={open} onValueChange={setOpen} className="flex flex-col gap-6">
            {grouped.map(sec => (
              <section key={sec.id}>
                <div className="mb-2 flex items-baseline gap-2">
                  <span className="section-label">{sec.title}</span>
                  <span className="text-[11.5px] text-text-faint">— {sec.hint}</span>
                </div>
                <div className="flex flex-col gap-2">
                  {sec.keys.map(k => (
                    <ParamItem
                      key={k} name={k} guide={guides[k]} value={current[k]} defaultValue={defaults[k]}
                      changed={changed.includes(k)} active={!inactive.includes(k)}
                    />
                  ))}
                </div>
              </section>
            ))}
          </Accordion.Root>
        </>
      ) : (
        <YamlView value={current} />
      )}
    </div>
  );
}

// ---- Một tham số -------------------------------------------------------------
function ParamItem({ name, guide, value, defaultValue, changed, active }: {
  name: string; guide?: Guide; value: any; defaultValue: any; changed: boolean; active: boolean;
}) {
  if (!guide) return null;
  const currentOpt = guide.options?.find(o => same(o.value, value));

  return (
    <Accordion.Item
      value={name}
      className={clsx(
        "overflow-hidden rounded-xl border bg-surface transition-colors",
        changed ? "border-accent/50" : "border-border",
        "data-[state=open]:shadow-lift",
      )}
    >
      <Accordion.Header>
        <Accordion.Trigger className="group flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-surface-2/50">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className={clsx("font-mono text-[13px] font-semibold", active ? "text-text" : "text-text-faint")}>{name}</span>
              {changed && <span className="rounded-full bg-accent px-1.5 py-[1px] text-[10.5px] font-medium text-accent-ink">đã đổi</span>}
              {!active && (
                <span className="inline-flex items-center gap-1 rounded-full border border-dashed border-border px-1.5 py-[1px] text-[10.5px] text-text-faint" title={guide.when_text && `Chỉ dùng khi ${guide.when_text}`}>
                  <CircleSlash className="h-3 w-3" /> không có tác dụng
                </span>
              )}
            </div>
            <div className={clsx("mt-0.5 text-[12.5px] leading-snug", active ? "text-text-muted" : "text-text-faint")}>{guide.ask}</div>
          </div>
          <div className="flex max-w-[45%] shrink-0 items-center gap-2 pt-0.5">
            <CurrentValue guide={guide} value={value} option={currentOpt} />
            <ChevronDown className="h-4 w-4 shrink-0 text-text-faint transition-transform group-data-[state=open]:rotate-180" />
          </div>
        </Accordion.Trigger>
      </Accordion.Header>

      <Accordion.Content className="border-t border-border/80 bg-bg/40 px-4 py-3.5">
        <div className="flex flex-col gap-3">
          {guide.when_text && (
            <div className={clsx("text-[12px]", active ? "text-text-faint" : "text-warn")}>
              Chỉ có tác dụng khi <span className="font-mono">{guide.when_text}</span>
              {!active && ' — cấu hình hiện tại không thỏa, nên giá trị này đang bị bỏ qua.'}
            </div>
          )}
          <ParamBody guide={guide} value={value} defaultValue={defaultValue} />
          {guide.tags && guide.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">{guide.tags.map(t => <ImpactTag key={t} tag={t} />)}</div>
          )}
          {guide.note && (
            <div className="flex gap-2 rounded-lg border border-info/25 bg-info/[0.06] px-3 py-2 text-[12.5px] leading-relaxed text-text-muted">
              <Info className="mt-[3px] h-3.5 w-3.5 shrink-0 text-info" />
              <span>{guide.note}</span>
            </div>
          )}
        </div>
      </Accordion.Content>
    </Accordion.Item>
  );
}

/** Giá trị đang dùng, hiện gọn ở đầu dòng tham số. */
function CurrentValue({ guide, value, option }: { guide: Guide; value: any; option?: Option }) {
  if (option) {
    return (
      <span className="flex min-w-0 items-center gap-1.5 rounded-md border border-border bg-bg px-2 py-[3px]">
        <span className="truncate text-[12px] font-medium text-text">{option.label}</span>
      </span>
    );
  }
  let text: string;
  if (Array.isArray(value)) text = value.length ? value.map(show).join(', ') : '[ ]';
  else if (value && typeof value === 'object') text = guide.kind === 'enum_map' ? `${value.default} +${Object.keys(value.overrides ?? {}).length}` : `${Object.keys(value).length} mục`;
  else text = value === null || value === undefined ? '—' : show(value);
  return (
    <span className="truncate rounded-md border border-border bg-bg px-2 py-[3px] font-mono text-[11.5px] text-text-muted" title={show(value)}>
      {text}
    </span>
  );
}

function ParamBody({ guide, value, defaultValue }: { guide: Guide; value: any; defaultValue: any }) {
  switch (guide.kind) {
    case 'enum':
      return <OptionList options={guide.options!} isCurrent={o => same(o.value, value)} isDefault={o => same(o.value, defaultValue)} />;

    case 'multi': {
      const arr: any[] = Array.isArray(value) ? value : [];
      const def: any[] = Array.isArray(defaultValue) ? defaultValue : [];
      return (
        <>
          <div className="text-[12px] text-text-faint">Chọn được nhiều giá trị cùng lúc.</div>
          <OptionList multi options={guide.options!} isCurrent={o => arr.some(v => same(v, o.value))} isDefault={o => def.some(v => same(v, o.value))} />
        </>
      );
    }

    case 'enum_map': {
      // unmapped_action: { default, overrides: { cột: giá trị } }
      const overrides: Record<string, any> = value?.overrides ?? {};
      const usedBy = (o: Option) => {
        const cols = Object.entries(overrides).filter(([, v]) => same(v, o.value)).map(([c]) => c);
        if (same(value?.default, o.value)) cols.unshift('mọi cột khác');
        return cols;
      };
      return (
        <>
          {guide.map_explain && <div className="text-[12px] text-text-faint">{guide.map_explain}</div>}
          <OptionList
            options={guide.options!}
            isCurrent={o => usedBy(o).length > 0}
            isDefault={o => same(defaultValue?.default, o.value)}
            currentLabel={o => `dùng cho: ${usedBy(o).join(', ')}`}
          />
        </>
      );
    }

    case 'number':
      return (
        <>
          <div className="grid grid-cols-2 gap-2">
            <ValueBox label="Đang dùng" value={value} strong />
            <ValueBox label="Mặc định" value={defaultValue} />
          </div>
          {(guide.up || guide.down) && (
            <div className="overflow-hidden rounded-lg border border-border bg-surface">
              {guide.up && <Direction icon={ArrowUp} label="Tăng lên" text={guide.up} />}
              {guide.down && <Direction icon={ArrowDown} label="Giảm xuống" text={guide.down} border />}
            </div>
          )}
          {guide.explain && <p className="text-[12.5px] leading-relaxed text-text-muted">{guide.explain}</p>}
        </>
      );

    case 'fields': {
      const obj = value ?? {};
      return (
        <div className="overflow-hidden rounded-lg border border-border bg-surface">
          {Object.entries(guide.fields!).map(([f, desc], i) => (
            <div key={f} className={clsx("grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 px-3 py-2.5", i > 0 && "border-t border-border/80")}>
              <span className="font-mono text-[12px] font-semibold text-text">{f}</span>
              <span className="justify-self-end"><Chip value={obj[f]} /></span>
              <span className="col-span-2 text-[12.5px] leading-relaxed text-text-muted">{desc}</span>
            </div>
          ))}
        </div>
      );
    }

    case 'map': {
      const obj: Record<string, any> = value ?? {};
      return (
        <>
          <div className="overflow-hidden rounded-lg border border-border bg-surface">
            {Object.entries(obj).map(([k, v], i) => (
              <div key={k} className={clsx("flex items-center justify-between px-3 py-2", i > 0 && "border-t border-border/80")}>
                <span className="font-mono text-[12px] text-text">{k}</span>
                <Chip value={v} />
              </div>
            ))}
            {Object.keys(obj).length === 0 && <div className="px-3 py-2 text-[12px] text-text-faint">trống</div>}
          </div>
          {guide.explain && <p className="text-[12.5px] leading-relaxed text-text-muted">{guide.explain}</p>}
        </>
      );
    }

    default: // list, string
      return (
        <>
          <div className="flex flex-wrap gap-1.5">
            {Array.isArray(value)
              ? (value.length ? value.map((v, i) => <Chip key={i} value={v} />) : <span className="text-[12px] text-text-faint">danh sách trống</span>)
              : <Chip value={value} />}
          </div>
          {!same(value, defaultValue) && (
            <div className="text-[12px] text-text-faint">Mặc định: <span className="font-mono">{show(defaultValue)}</span></div>
          )}
          {guide.explain && <p className="text-[12.5px] leading-relaxed text-text-muted">{guide.explain}</p>}
        </>
      );
  }
}

/** Danh sách lựa chọn dạng thẻ radio: giá trị · tên cách xử lý · tác dụng · loại tác động. */
function OptionList({ options, isCurrent, isDefault, multi, currentLabel }: {
  options: Option[];
  isCurrent: (o: Option) => boolean;
  isDefault: (o: Option) => boolean;
  multi?: boolean;
  currentLabel?: (o: Option) => string;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      {options.map(o => {
        const cur = isCurrent(o);
        return (
          <div
            key={show(o.value)}
            className={clsx(
              "flex gap-3 rounded-lg border px-3 py-2.5 transition-colors",
              cur ? "border-accent/55 bg-accent/[0.06]" : "border-border bg-surface",
              !o.implemented && !cur && "border-dashed",
            )}
          >
            <span className={clsx(
              "mt-[3px] flex h-4 w-4 shrink-0 items-center justify-center border-[1.5px]",
              multi ? "rounded-[4px]" : "rounded-full",
              cur ? "border-accent bg-accent" : "border-line-strong/50",
            )}>
              {cur && (multi ? <Check className="h-3 w-3 text-accent-ink" strokeWidth={3} /> : <span className="h-1.5 w-1.5 rounded-full bg-accent-ink" />)}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <code className={clsx("font-mono text-[12.5px] font-semibold", o.implemented ? "text-text" : "text-text-faint")}>{show(o.value)}</code>
                <span className={clsx("text-[13px] font-medium", o.implemented ? "text-text" : "text-text-faint")}>{o.label}</span>
                {cur && (
                  <span className="rounded-full bg-accent px-1.5 py-[1px] text-[10.5px] font-medium text-accent-ink">
                    {currentLabel ? currentLabel(o) : 'đang dùng'}
                  </span>
                )}
                {isDefault(o) && <span className="rounded-full border border-border px-1.5 py-[0px] text-[10.5px] text-text-muted">mặc định</span>}
              </div>
              <p className={clsx("mt-1 text-[12.5px] leading-relaxed", o.implemented ? "text-text-muted" : "text-text-faint")}>{o.effect}</p>
              {(o.tags.length > 0 || !o.implemented) && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {o.tags.map(t => <ImpactTag key={t} tag={t} />)}
                  {!o.implemented && <ImpactTag tag="noop" />}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ValueBox({ label, value, strong }: { label: string; value: any; strong?: boolean }) {
  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2">
      <div className="section-label">{label}</div>
      <div className={clsx("mt-0.5 font-mono text-[15px] tabular-nums", strong ? "font-semibold text-text" : "text-text-muted")}>{show(value)}</div>
    </div>
  );
}

function Direction({ icon: Icon, label, text, border }: { icon: any; label: string; text: string; border?: boolean }) {
  return (
    <div className={clsx("flex gap-2.5 px-3 py-2.5", border && "border-t border-border/80")}>
      <Icon className="mt-[2px] h-3.5 w-3.5 shrink-0 text-accent" strokeWidth={2.4} />
      <div className="text-[12.5px] leading-relaxed">
        <span className="font-medium text-text">{label}: </span>
        <span className="text-text-muted">{text}</span>
      </div>
    </div>
  );
}

function Chip({ value }: { value: any }) {
  const text = value === null || value === undefined ? 'null' : show(value);
  return <span className="rounded-md border border-border bg-bg px-1.5 py-[2px] font-mono text-[11.5px] text-text-muted">{text}</span>;
}

function Segmented<T extends string>({ value, onChange, options }: { value: T; onChange: (v: T) => void; options: [T, string][] }) {
  return (
    <div className="flex shrink-0 rounded-full border border-border bg-surface p-0.5 text-[12px]">
      {options.map(([v, label]) => (
        <button
          key={v}
          className={clsx("rounded-full px-3 py-1 transition-colors", value === v ? "bg-text text-bg" : "text-text-muted hover:text-text")}
          onClick={() => onChange(v)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

function YamlView({ value }: { value: any }) {
  const theme = useUIStore(s => s.theme);
  const [html, setHtml] = useState('');
  const [text, setText] = useState('');

  useEffect(() => {
    let alive = true;
    Promise.all([import('yaml'), import('shiki')]).then(async ([YAML, shiki]) => {
      const yml = YAML.stringify(value);
      const hl = await shiki.createHighlighter({ themes: ['github-light', 'github-dark-default'], langs: ['yaml'] });
      if (!alive) return;
      setText(yml);
      setHtml(hl.codeToHtml(yml, { lang: 'yaml', theme: theme === 'dark' ? 'github-dark-default' : 'github-light' }));
    });
    return () => { alive = false; };
  }, [value, theme]);

  return (
    <div className="group relative rounded-xl border border-border bg-surface">
      <button
        className="absolute right-2 top-2 rounded-md border border-border bg-surface p-1.5 text-text-muted opacity-0 transition-opacity hover:text-text group-hover:opacity-100"
        title="Chép YAML"
        onClick={() => navigator.clipboard?.writeText(text)}
      >
        <Copy className="h-3.5 w-3.5" />
      </button>
      <div className="overflow-x-auto px-4 py-3" dangerouslySetInnerHTML={{ __html: html || '<span style="opacity:.5">Đang tải…</span>' }} />
    </div>
  );
}
