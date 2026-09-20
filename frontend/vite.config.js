import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8081',
        changeOrigin: true,
        timeout: 600000,
        proxyTimeout: 600000
      },
      '/uploads': {
        target: 'http://127.0.0.1:8081',
        changeOrigin: true,
        timeout: 600000,
        proxyTimeout: 600000
      }
    }
  }
})