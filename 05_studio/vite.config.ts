import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
const build = new Date().toISOString();

export default defineConfig({
  base: "/",
  define: { __STUDIO_BUILD__: JSON.stringify(build) },
  plugins: [
    vue(),
    {
      name: "studio-release-identity",
      generateBundle() {
        this.emitFile({
          type: "asset",
          fileName: "version.json",
          source: JSON.stringify({ build }),
        });
      },
      transformIndexHtml() {
        return [
          {
            tag: "meta",
            attrs: { name: "studio-build", content: build },
            injectTo: "head",
          },
        ];
      },
    },
  ],
  server: {
    port: 5184,
    strictPort: true,
    proxy: {
      "/studio-api": { target: "http://127.0.0.1:8011", changeOrigin: false },
    },
  },
  preview: { port: 4184, strictPort: true, proxy: {"/studio-api": {target:"http://127.0.0.1:8011",changeOrigin:false}} },
  build: { assetsDir: "studio-assets" },
});
