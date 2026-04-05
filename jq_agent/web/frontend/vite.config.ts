import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

/** 构建产物供 FastAPI 托管：jq_agent/web/static */
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir: "../static",
    emptyOutDir: true,
    sourcemap: false,
    minify: "esbuild",
    target: "es2022",
    rollupOptions: {
      output: {
        manualChunks: undefined,
      },
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": { target: "http://127.0.0.1:8765", changeOrigin: true },
      "/health": { target: "http://127.0.0.1:8765", changeOrigin: true },
    },
  },
});
