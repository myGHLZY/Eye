import vue from '@vitejs/plugin-vue2'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],

  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,

    // 允许通过这个 Cloudflare 域名访问
    allowedHosts: [
      'saves-intent-program-enhancement.trycloudflare.com',
    ],

    proxy: {
      '/api': 'http://127.0.0.1:5111',
    },
  },
})