import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { TanStackRouterVite } from '@tanstack/router-vite-plugin'

const API_PORT = process.env.API_PORT || '8000'
const WEB_PORT = process.env.WEB_PORT || '5173'

export default defineConfig({
  plugins: [react(), TanStackRouterVite()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
  server: {
    port: parseInt(WEB_PORT, 10),
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${API_PORT}`,
        changeOrigin: true,
      },
      '/outputs': {
        target: `http://127.0.0.1:${API_PORT}`,
        changeOrigin: true,
      },
    },
  },
})
