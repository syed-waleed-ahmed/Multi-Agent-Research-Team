import path from "node:path";
import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests against the real FastAPI app with a deterministic fake
 * research engine (`tests/e2e/server.py`), which also serves `frontend/dist`.
 * Run `npm run build` first. Set `E2E_PYTHON` to the interpreter that has the
 * backend installed, e.g. `E2E_PYTHON=../.venv/Scripts/python` on Windows or
 * `E2E_PYTHON=../.venv/bin/python` elsewhere (default: `python`).
 */
const port = Number(process.env.E2E_PORT ?? "8765");
const baseURL = `http://127.0.0.1:${port}`;

function pythonCommand(): string {
  const value = process.env.E2E_PYTHON?.trim() || "python";
  // Paths get native separators (cmd.exe cannot run "../x"); bare commands stay as they are.
  return /[\\/]/.test(value) ? path.normalize(value) : value;
}

const quote = (value: string) => `"${value}"`;
const serverScript = path.join("..", "tests", "e2e", "server.py");

export default defineConfig({
  testDir: "./e2e",
  outputDir: "./test-results",
  // The test server runs one research job at a time, so tests run serially.
  fullyParallel: false,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : [["list"]],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
      testIgnore: /screenshots\.spec\.ts/,
    },
    {
      name: "screenshots",
      use: { ...devices["Desktop Chrome"] },
      testMatch: /screenshots\.spec\.ts/,
    },
  ],
  webServer: {
    command: `${quote(pythonCommand())} ${quote(serverScript)}`,
    url: `${baseURL}/api/health`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: { E2E_PORT: String(port) },
    stdout: "ignore",
    stderr: "pipe",
  },
});
