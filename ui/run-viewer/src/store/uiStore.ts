import { create } from 'zustand';

export type DrawerTab = "problem" | "params" | "result";
export type LeftPanel = "L" | "artifacts" | "dict" | null;
export type Theme = "light" | "dark";
export type View = "run" | "context";

interface UIState {
  selectedNodeId: string | null;
  hoveredNodeId: string | null;
  drawerTab: DrawerTab;
  leftPanel: LeftPanel;
  theme: Theme;
  view: View;
  /** Trang bối cảnh: lăng kính đang xem ('roles' hoặc mã module) và mục đang chọn ('c:ID' | 'v:cột') */
  lens: string;
  ctxSel: string | null;

  setView: (v: View) => void;
  setLens: (l: string) => void;
  setCtxSel: (s: string | null) => void;
  setSelectedNodeId: (id: string | null) => void;
  setHoveredNodeId: (id: string | null) => void;
  setDrawerTab: (tab: DrawerTab) => void;
  setLeftPanel: (panel: LeftPanel) => void;
  setTheme: (t: Theme) => void;
}

/** Ghi trạng thái vào URL (?node=&tab=) để gửi link là mở đúng chỗ. */
function syncUrl(key: string, value: string | null) {
  if (typeof window === 'undefined') return;
  const url = new URL(window.location.href);
  if (value) url.searchParams.set(key, value);
  else url.searchParams.delete(key);
  window.history.replaceState({}, '', url);
}

const TABS: DrawerTab[] = ["problem", "params", "result"];

export const useUIStore = create<UIState>((set) => {
  const params = new URLSearchParams(typeof window !== 'undefined' ? window.location.search : '');
  const tab = params.get("tab") as DrawerTab;
  const theme = (typeof document !== 'undefined' && document.documentElement.dataset.theme === 'dark') ? 'dark' : 'light';

  return {
    selectedNodeId: params.get("node") || null,
    hoveredNodeId: null,
    drawerTab: TABS.includes(tab) ? tab : "problem",
    leftPanel: null,
    theme,
    view: params.get("view") === "context" ? "context" : "run",
    lens: params.get("lens") || "roles",
    ctxSel: null,

    setView: (v) => { set({ view: v }); syncUrl("view", v === "context" ? v : null); },
    setLens: (l) => { set({ lens: l }); syncUrl("lens", l === "roles" ? null : l); },
    setCtxSel: (s) => set({ ctxSel: s }),
    setSelectedNodeId: (id) => { set({ selectedNodeId: id }); syncUrl("node", id); },
    setHoveredNodeId: (id) => set({ hoveredNodeId: id }),
    setDrawerTab: (t) => { set({ drawerTab: t }); syncUrl("tab", t); },
    setLeftPanel: (panel) => set({ leftPanel: panel }),
    setTheme: (t) => {
      document.documentElement.dataset.theme = t;
      try { localStorage.setItem('rv-theme', t); } catch { /* chế độ riêng tư: bỏ qua */ }
      set({ theme: t });
    },
  };
});
