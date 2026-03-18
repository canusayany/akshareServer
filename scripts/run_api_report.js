#!/usr/bin/env node
/**
 * 自动启动 HTTP 服务器（真实数据模式）并运行 API 接口测试报告。
 * 运行：npm run test:report:auto
 * 可选：在 .env 中设置 TUSHARE_TOKEN 以启用 Tushare 备选数据源。
 */
import "dotenv/config";
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { startLocalServer } from "./local_server.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");

async function main() {
  const server = await startLocalServer({
    root,
    dbFileName: "api_report.sqlite",
  });
  console.log("启动 AKShare 服务器（真实数据模式）...");
  if (server.installed) {
    console.log("检测到项目虚拟环境缺少依赖，已自动执行 pip install -r requirements.txt");
  }

  try {
    console.log("服务器已就绪，开始测试...\n");
    const runner = spawn(process.execPath, ["scripts/api_report.js"], {
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
