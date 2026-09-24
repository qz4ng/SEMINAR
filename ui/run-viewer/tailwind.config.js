/** @type {import('tailwindcss').Config} */
// Màu lấy từ biến CSS (index.css) theo bảng màu của Atlas_Nhan_qua_RA.html, nên đổi
// sáng/tối chỉ cần đổi data-theme trên <html>. Viết dạng "rgb(var(--x) / <alpha-value>)"
// để các lớp có độ trong suốt như bg-warn/10 vẫn dùng được.
const v = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: v('bg'),
        surface: v('surface'),
        'surface-2': v('surface-2'),
        border: v('line'),
        'line-strong': v('line-strong'),
        text: v('ink'),
        'text-muted': v('muted'),
        'text-faint': v('faint'),
        accent: v('accent'),
        'accent-ink': v('accent-ink'),
        ok: v('ok'),
        warn: v('warn'),
        blocked: v('blocked'),
        failed: v('failed'),
        info: v('info'),
        teal: v('teal'),
        'data-edge': v('accent'),
        'context-edge': v('context'),
        conf: v('conf'),
        prec: v('prec'),
        instr: v('instr'),
        unm: v('unm'),
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', '"Segoe UI"', '"Noto Sans"', 'system-ui', 'sans-serif'],
        display: ['"Be Vietnam Pro"', '"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', '"Cascadia Mono"', 'Consolas', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        panel: 'var(--shadow)',
        lift: 'var(--shadow-lift)',
      },
    },
  },
  plugins: [],
}
