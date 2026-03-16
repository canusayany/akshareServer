#!/usr/bin/env node
/**
 * 自动启动 HTTP 服务器并运行 HTTP 接口全面测试。
 * 使用 TEST_MODE=1（StubBackend），无需真实网络。
 * 运行：npm run test:http
 */
import { spawn } from "node:child_process";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const pythonPath = path.join(root, "python");
const PYTHON_BIN = os.platform() === "win32" ? "py" : "python3";

function delay(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function waitForHealth(timeoutMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const r = await fetch("http://127.0.0.1:8888/health", {
        signal: AbortSignal.timeout(2000),
      });
      if (r.ok && (await r.json()).ok) return true;
    } catch {}
    await delay(300);
  }
  return false;
}

async function main() {
  const child = spawn(PYTHON_BIN, ["-m", "akshare_node_bridge.server"], {
    cwd: root,
    env: {
      ...process.env,
      PYTHONPATH: process.env.PYTHONPATH ? `${pythonPath}${path.delimiter}${process.env.PYTHONPATH}` : pythonPath,
      PYTHONIOENCODING: "utf-8",
      PYTHONUTF8: "1",
      AKSHARE_NODE_TEST_MODE: "1",
      AKSHARE_NODE_DB_PATH: path.join(root, "data", "http_test.sqlite"),
    },
    stdio: ["ignore", "pipe", "pipe"],
  });

  let stdout = "";
  let stderr = "";
  child.stdout?.on("data", (c) => { stdout += c; });
  child.stderr?.on("data", (c) => { stderr += c; });

  try {
    if (!(await waitForHealth())) {
      console.error("Server did not become healthy. stderr:", stderr);
      process.exit(1);
    }
    const runner = spawn(process.execPath, ["--test", "test/http_api.test.js"], {
      cwd: root,
      stdio: "inherit",
    });
    const code = await new Promise((resolve) => runner.on("close", resolve));
    process.exit(code ?? 1);
  } finally {
    child.kill();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
