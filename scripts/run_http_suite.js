#!/usr/bin/env node
/**
 * 自动启动 HTTP 服务器并运行 HTTP 接口全面测试。
 * 使用 TEST_MODE=1（StubBackend），无需真实网络。
 * 运行：npm run test:http
 */
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { startLocalServer } from "./local_server.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");

async function main() {
  const server = await startLocalServer({
    root,
    dbFileName: "http_test.sqlite",
    testMode: true,
    requiredModules: ["akshare", "pandas", "requests"],
  });

  try {
    const runner = spawn(process.execPath, ["--test", "test/http_api.test.js"], {
      cwd: root,
      stdio: "inherit",
    });
    const code = await new Promise((resolve) => runner.on("close", resolve));
    process.exit(code ?? 1);
  } finally {
    server.stop();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
