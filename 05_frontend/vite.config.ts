import { defineConfig } from "vite";
import uni from "@dcloudio/vite-plugin-uni";

// https://vitejs.dev/config/
export default defineConfig({
  base: process.env.UNI_PLATFORM === "h5" ? "/h5/" : "/",
  plugins: [uni()],
  server: {
    port: 3000,
    open: true
  }
});
