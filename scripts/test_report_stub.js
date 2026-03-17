#!/usr/bin/env node
/**
 * 测试报告生成（Stub 模式，无需网络）
 * 输出：各接口的测试入参、测试返回值
 * 运行：node scripts/test_report_stub.js
 * 或：cd akshare_node; node scripts/test_report_stub.js
 */
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { createClient } from "../src/index.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");

const INTERFACE_PARAMS = {
  stock_zh_a_spot: {},
  stock_zh_a_hist: { symbol: "000001", period: "daily", start_date: "2024-01-01", end_date: "2024-01-31" },
  stock_intraday_em: { symbol: "000001" },
  stock_bid_ask_em: { symbol: "000001" },
  stock_index_zh_hist: { symbol: "000001", start_date: "2024-01-01", end_date: "2024-01-31" },
  stock_financial_abstract: { symbol: "000001" },
  stock_yjbb_em: { date: "20241231" },
  stock_yjyg_em: { date: "20241231" },
  futures_zh_spot: {},
  futures_zh_hist: { symbol: "RB0" },
  match_main_contract: {},
  futures_basis: {},
  fund_meta: {},
  fund_etf_market: {},
  fund_open_info: { symbol: "110011" },
  macro_china_all: {},
  commodity_basis: {},
  spot_sge: {},
  bond_zh_hs_market: {},
  bond_zh_hs_cov_market: {},
  bond_cb_meta: { mode: "summary" },
  stock_board_industry: {},
  stock_board_concept: {},
  option_finance_board: { symbol: "华夏上证50ETF期权", end_month: "2503" },
  option_current_em: {},
  option_sse_daily_sina: { symbol: "10005050C2503M" },
  option_commodity_hist: { symbol: "m2503-C-4000", exchange: "dce", trade_date: "2024-01-02" },
};

async function main() {
  const client = createClient({
    projectRoot: root,
    dbPath: path.join(root, "data", "test_report_stub.sqlite"),
    env: { AKSHARE_NODE_TEST_MODE: "1" },
  });

  const report = {
    title: "AKShare Node 接口测试报告（Stub 模式）",
    timestamp: new Date().toISOString(),
    description: "各接口的测试入参、测试返回值。使用 StubBackend，无需网络。",
    interfaces: {},
    summary: { total: 0, passed: 0, failed: 0 },
  };

  for (const [iface, params] of Object.entries(INTERFACE_PARAMS)) {
    const entry = {
      interface: iface,
      测试入参: params,
      success: false,
      测试返回值: null,
    };

    try {
      const result = await client.invoke(iface, params);
      if (result.ok) {
        entry.success = true;
        entry.测试返回值 = {
          ok: result.ok,
          interface: result.interface,
          params: result.params,
          cache_hit: result.cache_hit,
          returned_rows: result.returned_rows,
          rows: result.rows?.slice(0, 3) ?? [],
          message: result.message,
        };
      } else {
        entry.测试返回值 = { ok: false, error: result.error };
      }
    } catch (err) {
      entry.测试返回值 = { ok: false, error: err?.message ?? String(err) };
    }

    report.interfaces[iface] = entry;
    report.summary.total++;
    if (entry.success) report.summary.passed++;
    else report.summary.failed++;
  }

  const reportsDir = path.join(root, "reports");
  if (!fs.existsSync(reportsDir)) fs.mkdirSync(reportsDir, { recursive: true });

  const reportPath = path.join(reportsDir, "test_report_stub.json");
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf-8");
  console.log(`测试报告已写入: ${reportPath}`);
  console.log(`\n总计: ${report.summary.total}  通过: ${report.summary.passed}  失败: ${report.summary.failed}`);

  // 生成可读的 Markdown 报告
  const md = generateMdReport(report);
  const mdPath = path.join(reportsDir, "test_report_stub.md");
  fs.writeFileSync(mdPath, md, "utf-8");
  console.log(`Markdown 报告已写入: ${mdPath}`);
}

function generateMdReport(report) {
  const lines = [
    `# ${report.title}`,
    "",
    `生成时间: ${report.timestamp}`,
    `说明: ${report.description}`,
    "",
    `## 测试摘要`,
    "",
    `| 总计 | 通过 | 失败 |`,
    `|------|------|------|`,
    `| ${report.summary.total} | ${report.summary.passed} | ${report.summary.failed} |`,
    "",
    "## 各接口测试入参与返回值",
    "",
  ];

  for (const [iface, entry] of Object.entries(report.interfaces)) {
    const status = entry.success ? "✓" : "✗";
    lines.push(`### ${status} ${iface}`);
    lines.push("");
    lines.push("**测试入参**");
    lines.push("");
    lines.push("```json");
    lines.push(JSON.stringify(entry.测试入参, null, 2));
    lines.push("```");
    lines.push("");
    lines.push("**测试返回值**");
    lines.push("");
    lines.push("```json");
    lines.push(JSON.stringify(entry.测试返回值, null, 2));
    lines.push("```");
    lines.push("");
  }

  return lines.join("\n");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
