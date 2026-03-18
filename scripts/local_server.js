#!/usr/bin/env node
import { spawn } from "node:child_process";
import path from "node:path";

import { resolvePythonRuntime } from "./python_runtime.js";

const HEALTH_URL = "http://127.0.0.1:8888/health";

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function waitForHealth(timeoutMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const response = await fetch(HEALTH_URL, {
        signal: AbortSignal.timeout(2000),
      });
      if (response.ok && (await response.json()).ok) {
        return true;
      }
    } catch {}
    await delay(300);
  }
  return false;
}

export async function startLocalServer({
  root,
  dbFileName,
  testMode = false,
  requiredModules,
} = {}) {
  const pythonPath = path.join(root, "python");
  const { pythonBin, installed } = await resolvePythonRuntime({ root, requiredModules });
  const child = spawn(pythonBin, ["-m", "akshare_node_bridge.server"], {
    cwd: root,
    env: {
      ...process.env,
      PYTHONPATH: process.env.PYTHONPATH ? `${pythonPath}${path.delimiter}${process.env.PYTHONPATH}` : pythonPath,
      PYTHONIOENCODING: "utf-8",
      PYTHONUTF8: "1",
      AKSHARE_NODE_DB_PATH: path.join(root, "data", dbFileName),
      ...(testMode ? { AKSHARE_NODE_TEST_MODE: "1" } : {}),
    },
    stdio: ["ignore", "pipe", "pipe"],
  });

  let stdout = "";
  let stderr = "";
  child.stdout?.on("data", (chunk) => { stdout += chunk.toString(); });
  child.stderr?.on("data", (chunk) => { stderr += chunk.toString(); });

  const healthy = await waitForHealth();
  if (!healthy) {
    child.kill();
    throw new Error(`Server did not become healthy. stderr: ${stderr || "<empty>"}`);
  }

  return {
    child,
    installed,
    pythonBin,
    getStdout() {
      return stdout;
    },
    getStderr() {
      return stderr;
    },
    stop() {
      if (!child.killed) {
        child.kill();
      }
    },
  };
}