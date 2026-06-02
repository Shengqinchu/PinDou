import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'https://pindou-backend-263102-4-1437642655.sh.run.tcloudbase.com',
        changeOrigin: true
      }
    }
  }
});

