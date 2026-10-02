import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: `npm run dev` on :5173 proxies to the env on :8000 (same paths nginx proxies in Docker).
export default defineConfig({
  base: "./",                       // relative asset paths: works behind any proxy prefix
  plugins: [react()],
  server: {
    proxy: {
      "/api": { target: "http://localhost:8000", rewrite: (p) => p.replace(/^\/api/, "") },
      "/ws": { target: "ws://localhost:8000", ws: true },
      "/ui/state": "http://localhost:8000",
      "/live": "http://localhost:8000",
      "/docs": "http://localhost:8000",
      "/openapi.json": "http://localhost:8000",
    },
  },
});
