import { defineConfig, loadEnv } from 'vite'
import path from 'path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'


function figmaAssetResolver() {
  return {
    name: 'figma-asset-resolver',
    resolveId(id: string) {
      if (id.startsWith('figma:asset/')) {
        const filename = id.replace('figma:asset/', '')
        return path.resolve(__dirname, 'src/assets', filename)
      }
    },
  }
}

export default defineConfig(({ mode }) => {
  // Load .env files for the current mode so we can read VITE_API_URL
  const env = loadEnv(mode, process.cwd(), '')

  // In dev: proxy to local FastAPI. In production builds with a separate
  // backend domain, set VITE_API_URL=https://mindcradle01-959765770210.asia-south1.run.app in .env.local
  // (Vercel/Railway rewrites handle /api routing automatically in most setups).
  const apiTarget = env.VITE_API_URL || 'http://localhost:8000'

  return {
    plugins: [
      figmaAssetResolver(),
      // The React and Tailwind plugins are both required for Make, even if
      // Tailwind is not being actively used – do not remove them
      react(),
      tailwindcss(),
    ],
    resolve: {
      alias: {
        // Alias @ to the src directory
        '@': path.resolve(__dirname, './src'),
      },
    },

    // File types to support raw imports. Never add .css, .tsx, or .ts files to this.
    assetsInclude: ['**/*.svg', '**/*.csv'],

    server: {
      proxy: {
        // Forward all /api requests to the FastAPI backend.
        // The api.ts client always uses relative /api paths — no changes needed there.
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          // Rewrite https → http when proxying to localhost in dev
          secure: !apiTarget.includes('localhost'),
        },
      },
    },
  }
})
