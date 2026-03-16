#!/usr/bin/env node
/**
 * 自动启动 HTTP 服务器（真实数据模式）并运行 API 接口测试报告。
 * 运行：npm run test:report:auto
 * 可选：在 .env 中设置 TUSHARE_TOKEN 以启用 Tushare 备选数据源。
 */
import "dotenv/config";
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const pythonPath = path.join(root, "python");
const venvPython = path.join(root, ".venv", os.platform() === "win32" ? "Scripts/python.exe" : "bin/python");
const PYTHON_BIN = (fs.existsSync && fs.existsSync(venvPython)) ? venvPython : (os.platform() === "win32" ? "py" : "python3");

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
  console.log("启动 AKShare 服务器（真实数据模式）...");
  const child = spawn(PYTHON_BIN, ["-m", "akshare_node_bridge.server"], {
    cwd: root,
    env: {
      ...process.env,
      PYTHONPATH: process.env.PYTHONPATH ? `${pythonPath}${path.delimiter}${process.env.PYTHONPATH}` : pythonPath,
      PYTHONIOENCODING: "utf-8",
      PYTHONUTF8: "1",
      AKSHARE_NODE_DB_PATH: path.join(root, "data", "api_report.sqlite"),
    },
    stdio: ["ignore", "pipe", "pipe"],
  });

  let stderr = "";
  child.stderr?.on("data", (c) => { stderr += c; });

  try {
    if (!(await waitForHealth())) {
      console.error("服务器启动失败。stderr:", stderr);
      process.exit(1);
    }
    console.log("服务器已就绪，开始测试...\n");
    const runner = spawn(process.execPath, ["scripts/api_report.js"], {
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
