import { defineConfig, type Plugin } from "vite";
import uni from "@dcloudio/vite-plugin-uni";

// The website owns these shared modules. Its tool/editor labels have no caller
// in the Studio mini program; exclude them at build time, without editing web copy.
const webOnlyCopy: Record<string, string[]> = {
  "account.json": ["pattern_tool"],
  "App.json": ["pattern_maker_7db57b"],
  "profile.json": ["shared_help"],
  "data-commerce-messages.json": ["journal_english_required"],
};
const studioCopyBoundary: Plugin = {
  name: "studio-copy-boundary",
  enforce: "pre",
  transform(code, id) {
    const file = id.replace(/\\/g, "/");
    const name = file.split("/").pop() || "";
    if (!file.includes("/05_studio/src/content/") || !webOnlyCopy[name]) return;
    const content = JSON.parse(code);
    for (const key of webOnlyCopy[name]) delete content[key];
    return { code: JSON.stringify(content), map: null };
  },
};

// https://vitejs.dev/config/
export default defineConfig({
  base: process.env.UNI_PLATFORM === "h5" ? "/h5/" : "/",
  plugins: [studioCopyBoundary, uni()],
  server: {
    port: 3000,
    open: true
  }
});
