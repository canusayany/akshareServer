import test from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import os from "node:os";
import path from "node:path";

const PYTHON_BIN = os.platform() === "win32" ? "py" : "python3";

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForHealth(url, timeoutMs = 10000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return;
      }
    } catch {}
    await delay(200);
  }
  throw new Error(`Server did not become healthy in ${timeoutMs}ms`);
}

test("http server listens on 127.0.0.1:8888 and serves tool APIs", async () => {
  const pythonPath = path.join(process.cwd(), "python");
  const child = spawn(PYTHON_BIN, ["-m", "akshare_node_bridge.server"], {
    cwd: process.cwd(),
    env: {
      ...process.env,
      PYTHONPATH: process.env.PYTHONPATH ? `${pythonPath}${path.delimiter}${process.env.PYTHONPATH}` : pythonPath,
      PYTHONIOENCODING: "utf-8",
      PYTHONUTF8: "1",
      AKSHARE_NODE_TEST_MODE: "1",
      AKSHARE_NODE_DB_PATH: path.join(process.cwd(), "data", "server-test.sqlite"),
    },
    stdio: ["ignore", "pipe", "pipe"],
  });

  try {
    await waitForHealth("http://127.0.0.1:8888/health");

    const health = await fetch("http://127.0.0.1:8888/health").then((response) => response.json());
    assert.equal(health.host, "127.0.0.1");
    assert.equal(health.port, 8888);

    const tools = await fetch("http://127.0.0.1:8888/tools").then((response) => response.json());
    assert.equal(tools.ok, true);
    assert.equal(tools.tools.includes("macro_china_all"), true);

    const invokeResponse = await fetch("http://127.0.0.1:8888/invoke", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        interface: "macro_china_all",
        params: {},
      }),
    });
    const invokeResult = await invokeResponse.json();
    assert.equal(invokeResult.ok, true);
    assert.equal(invokeResult.interface, "macro_china_all");
  } finally {
    child.kill();
  }
});
