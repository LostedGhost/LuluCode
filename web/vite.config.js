import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// En dev : proxy vers le serveur FastAPI (lulucode web --port 8341).
// En prod : `npm run build` produit dist/ que FastAPI sert en statique.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/tache': 'http://127.0.0.1:8341',
      '/permission': 'http://127.0.0.1:8341',
      '/evenements': { target: 'http://127.0.0.1:8341', ws: false },
      '/historique': 'http://127.0.0.1:8341',
    },
  },
  build: { outDir: 'dist' },
})
