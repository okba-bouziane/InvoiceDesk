/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The FastAPI service (port 7860) serves /api and /samples. In dev and preview Vite proxies
// them, so the browser sees one origin; in production FastAPI serves the built app itself.
const proxy = {
  '/api': 'http://localhost:7860',
  '/samples': 'http://localhost:7860',
}

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy },
  preview: { proxy },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
})
