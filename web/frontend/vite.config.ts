import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const BASE = '/constellation-simulator'

export default defineConfig({
  plugins: [react()],
  // Assets and routes are served under the subpath in both dev and prod.
  base: `${BASE}/`,
  server: {
    port: 3000,
    proxy: {
      // Proxy API calls through the subpath during local development.
      [`${BASE}/api`]: {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(BASE, ''),
      },
    },
  },
  preview: {
    port: 3000,
  },
})
