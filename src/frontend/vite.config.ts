import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

/**
 * The routes the backend owns. In development Vite proxies them, so the app
 * uses the same relative URLs it does when the backend serves it.
 */
const API_ROUTES = [
  '/tree',
  '/notes',
  '/folders',
  '/entries',
  '/images',
  '/imports',
  '/hollow',
  '/settings',
  '/tutor',
]

const target = process.env.DRAGONGLASS_API_URL ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5173,
    proxy: Object.fromEntries(
      API_ROUTES.map((route) => [route, { target, changeOrigin: true }]),
    ),
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
