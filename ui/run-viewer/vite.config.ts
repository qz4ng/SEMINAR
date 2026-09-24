import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  // GitHub Pages phục vụ trang ở https://<user>.github.io/<repo>/ nên đường dẫn tài nguyên
  // phải có tiền tố /<repo>/. Workflow deploy đặt VITE_BASE; chạy trên máy thì để '/'.
  base: process.env.VITE_BASE ?? '/',
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
