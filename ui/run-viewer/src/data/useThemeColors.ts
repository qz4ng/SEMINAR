import { useMemo } from 'react';
import { useUIStore } from '../store/uiStore';

const KEYS = ['accent', 'line', 'line-strong', 'blocked', 'failed', 'context', 'faint', 'ink', 'muted', 'surface'] as const;
type Key = typeof KEYS[number];

/**
 * Màu theme dạng hex cho những chỗ không nhận được biến CSS: React Flow tạo id của mũi tên
 * từ chuỗi màu và tham chiếu bằng url(#id), nên "rgb(var(--x))" sẽ làm hỏng tham chiếu.
 * Đọc lại mỗi khi đổi theme.
 */
export function useThemeColors(): Record<Key, string> {
  const theme = useUIStore(s => s.theme);
  return useMemo(() => {
    const cs = getComputedStyle(document.documentElement);
    const out = {} as Record<Key, string>;
    for (const k of KEYS) {
      const [r, g, b] = cs.getPropertyValue(`--${k}`).trim().split(/\s+/).map(Number);
      out[k] = '#' + [r, g, b].map(n => (n || 0).toString(16).padStart(2, '0')).join('');
    }
    return out;
    // theme là phụ thuộc thật: data-theme đổi thì giá trị biến CSS đổi
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [theme]);
}
