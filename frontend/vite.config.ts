import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // In development the FastAPI backend runs on :8000; Vite forwards /api calls to it.
    proxy: { '/api': 'http://localhost:8000' },
  },
})
