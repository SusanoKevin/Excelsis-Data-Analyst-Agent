import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiBase = env.VITE_API_BASE_URL || 'http://localhost:8000'

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/auth':        apiBase,
        '/chat/stream': apiBase,
        '/data':        apiBase,
        '/health':      apiBase,
      },
    },
  }
})
