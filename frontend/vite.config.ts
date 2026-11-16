/// <reference types="vitest/config" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv, type ProxyOptions } from "vite";

// The dev server proxies /api to a running backend so the browser stays same-origin
// (matching production, where FastAPI serves this build). Defaults to the E2E test
// server (tests/e2e/server.py, port 8765); set API_PROXY_TARGET=http://127.0.0.1:8000
// to develop against `research-team-web`.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const proxy: Record<string, ProxyOptions> = {
    "/api": { target: env.API_PROXY_TARGET || "http://127.0.0.1:8765", changeOrigin: true },
  };

  return {
    plugins: [react(), tailwindcss()],
    server: { proxy },
    preview: { proxy },
    build: {
      outDir: "dist",
      target: "es2022",
      sourcemap: false,
    },
    test: {
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
      include: ["src/**/*.test.{ts,tsx}"],
      css: false,
      restoreMocks: true,
      unstubGlobals: true,
    },
  };
});
