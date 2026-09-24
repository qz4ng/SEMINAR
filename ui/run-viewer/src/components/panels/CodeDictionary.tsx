import { Command } from 'cmdk';
import { useUIStore } from '../../store/uiStore';
import errorCodes from '../../content/error_codes.json';
import { useEffect } from 'react';
import { BookOpen, X } from 'lucide-react';

export default function CodeDictionary() {
  const leftPanel = useUIStore(s => s.leftPanel);
  const setLeftPanel = useUIStore(s => s.setLeftPanel);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === '/' && !(e.target as HTMLElement)?.closest('input, textarea')) {
        e.preventDefault();
        setLeftPanel(leftPanel === 'dict' ? null : 'dict');
      }
    };
    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, [leftPanel, setLeftPanel]);

  if (leftPanel !== 'dict') return null;

  return (
    <div className="absolute left-16 top-0 bottom-0 z-20 flex w-[320px] flex-col border-r border-border bg-surface shadow-panel">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div>
          <div className="kicker">Tra cứu</div>
          <div className="mt-0.5 flex items-center gap-2 font-display text-[16px] font-semibold text-text">
            <BookOpen className="h-4 w-4 text-accent" /> Từ điển mã
          </div>
        </div>
        <button onClick={() => setLeftPanel(null)} className="rounded-full p-1.5 text-text-muted hover:bg-surface-2 hover:text-text" title="Đóng">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="flex-1 overflow-hidden">
        <Command className="h-full flex flex-col bg-transparent">
          <Command.Input 
            autoFocus
            placeholder="Tìm mã lỗi hoặc từ khóa..." 
            className="w-full border-b border-border bg-transparent px-4 py-2.5 text-[13px] placeholder:text-text-faint focus:outline-none"
          />
          <Command.List className="h-full overflow-y-auto p-2 pb-16">
            <Command.Empty className="py-6 text-center text-sm text-text-muted">Không tìm thấy.</Command.Empty>
            {errorCodes.map((item) => (
              <Command.Item
                key={item.code}
                value={`${item.code} ${item.explain}`}
                className="mb-1 cursor-pointer rounded-lg px-3 py-2 text-[13px] data-[selected=true]:bg-surface-2"
                onSelect={() => {}}
              >
                <div className="mb-0.5 font-mono text-[12px] font-semibold text-accent">{item.code}</div>
                <div className="text-text-muted leading-snug">{item.explain}</div>
              </Command.Item>
            ))}
          </Command.List>
        </Command>
      </div>
    </div>
  );
}
