import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  base: "/studio/",
  plugins: [vue()],
  server: {
    port: 5184,
    strictPort: true,
    proxy: {
      "/studio-api": { target: "http://127.0.0.1:8011", changeOrigin: false },
    },
  },
  preview: { port: 4184, strictPort: true },
  build: { assetsDir: "studio-assets" },
});
