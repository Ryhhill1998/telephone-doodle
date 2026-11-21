import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// The API runs separately (Cloud Run in production, uvicorn locally). In dev
// VITE_API_URL is empty, so the app makes same-origin requests to /api and /ws
// and this proxy forwards them to the local backend. See BUILD_PLAN.md §3.
const BACKEND = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: BACKEND, changeOrigin: true },
      '/ws': { target: BACKEND, changeOrigin: true, ws: true },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.test.{ts,tsx}', 'src/test/**', 'src/main.tsx'],
    },
  },
})
