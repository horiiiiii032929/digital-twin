import path from 'node:path'

import tailwindcss from '@tailwindcss/vite'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

const repositoryRoot = path.resolve(import.meta.dirname, '../..')

export default defineConfig(({ mode }) => {
  const environment = loadEnv(mode, repositoryRoot, 'VITE_')
  return {
    envDir: repositoryRoot,
    plugins: [
      react(),
      tailwindcss(),
      {
        name: 'inspectable-auth-build-configuration',
        generateBundle() {
          this.emitFile({
            type: 'asset',
            fileName: 'build-configuration.json',
            source: JSON.stringify({
              schema_version: 1,
              auth_mode: environment.VITE_AUTH_MODE === 'session' ? 'session' : 'demo',
            }),
          })
        },
      },
    ],
    server: {
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
    resolve: {
      alias: {
        '@': path.resolve(import.meta.dirname, './src'),
      },
    },
  }
})
