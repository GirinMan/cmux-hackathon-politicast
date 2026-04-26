import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// dev: 8234 frontend, proxy /api -> 8235 (FastAPI backend)
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 8234,
    host: '127.0.0.1',
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8235',
        changeOrigin: true,
      },
    },
  },
})
