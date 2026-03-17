#!/usr/bin/env node
/**
 * API 接口测试报告
 * 测试 server 各接口是否能获取到数据，输出测试报告和 API 文档
 *
 * 前置：先启动真实服务器（非 TEST_MODE）：
 *   .\start_nossl.ps1  或  .\start_nossl.cmd
 *
 * 运行：node scripts/api_report.js
 * 或：npm run test:report
 *
 * 输出：
 *   - 控制台：测试结果摘要
 *   - reports/api_test_report.json：详细测试报告
 *   - docs/API.md：接口入参、返回值文档
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const BASE = "http://127.0.0.1:8888";
const TIMEOUT_MS = 120_000; // 期货历史接口可能较慢

/**
 * 每个接口的测试参数及 API 元信息（入参、返回值说明）
 */
const INTERFACE_SPEC = {
  stock_zh_a_spot: {
    params: {},
    paramDesc: { symbol: "可选，股票代码，如 000001" },
    returnDesc: "A 股实时行情列表",
  },
  stock_zh_a_hist: {
    params: { symbol: "000001", period: "daily", start_date: "2024-01-01", end_date: "2024-01-31" },
    paramDesc: {
      symbol: "必填，股票代码",
      period: "daily|weekly|monthly|1m|5m|15m|30m|60m",
      start_date: "开始日期",
      end_date: "结束日期",
      adjust: "可选，复权方式",
    },
    returnDesc: "A 股历史 K 线",
  },
  stock_intraday_em: {
    params: { symbol: "000001" },
    paramDesc: { symbol: "必填，股票代码" },
    returnDesc: "分时行情",
  },
  stock_bid_ask_em: {
    params: { symbol: "000001" },
    paramDesc: { symbol: "必填，股票代码" },
    returnDesc: "买卖盘口",
  },
  futures_zh_spot: {
    params: { symbol: "PTA" },
    paramDesc: {
      symbol: "可选，期货合约代码",
      market: "可选，FF|SF 等",
      adjust: "可选",
    },
    returnDesc: "期货实时行情",
  },
  futures_zh_hist: {
    params: { symbol: "RB2505", start_date: "2025-03-05", end_date: "2025-03-05" },  // 单日减轻请求
    paramDesc: {
      symbol: "必填，期货合约",
      period: "daily|1m|5m|15m|30m|60m",
      start_date: "可选，开始日期",
      end_date: "可选，结束日期",
      source: "可选，em 用东方财富",
    },
    returnDesc: "期货历史 K 线",
  },
  match_main_contract: {
    params: {},
    paramDesc: {
      symbol: "可选，交易所如 cffex|shfe|dce|czce",
      exchange: "同上",
    },
    returnDesc: "主力合约列表",
  },
  futures_basis: {
    params: { date: "2024-01-15" },
    paramDesc: {
      mode: "可选，sys 用 futures_spot_sys，否则用 futures_spot_price",
      symbol: "mode=sys 时必填，如 RU",
      date: "可选，交易日 YYYY-MM-DD，空则当天",
    },
    returnDesc: "期货基差/现货价格",
  },
  fund_meta: {
    params: {},
    paramDesc: {
      mode: "可选，purchase 返回申购信息",
    },
    returnDesc: "基金列表/申购信息",
  },
  fund_etf_market: {
    params: {},
    paramDesc: {
      mode: "可选，hist 返回历史需 symbol/start_date/end_date",
      symbol: "mode=hist 时必填",
      period: "daily/weekly/monthly",
      start_date: "mode=hist 时",
      end_date: "mode=hist 时",
      adjust: "可选",
    },
    returnDesc: "ETF 行情/历史",
  },
  fund_open_info: {
    params: { symbol: "110011" },
    paramDesc: {
      symbol: "必填，基金代码",
      indicator: "可选，如 单位净值走势",
    },
    returnDesc: "开放式基金信息",
  },
  macro_china_all: {
    params: {},
    paramDesc: {
      datasets: "可选，gdp,cpi,ppi,pmi,lpr,money_supply,credit,fx_gold 或 macro_china_*",
    },
    returnDesc: "宏观数据汇总",
  },
  commodity_basis: {
    params: { date: "2024-03-15" },
    paramDesc: {
      mode: "可选，futures_spot_price|futures_spot_sys",
      symbol: "可选，品种如 铜/CU/RU",
      date: "可选，交易日",
    },
    returnDesc: "商品基差/现货价",
  },
  spot_sge: {
    params: {},
    paramDesc: {
      mode: "可选，hist 返回历史",
      symbol: "可选，Au99.99/白银等",
    },
    returnDesc: "上海黄金交易所现货行情",
  },
  bond_zh_hs_market: {
    params: {},
    paramDesc: {
      mode: "可选，hist 需 symbol",
      symbol: "mode=hist 时必填",
    },
    returnDesc: "沪深债券行情",
  },
  bond_zh_hs_cov_market: {
    params: {},
    paramDesc: {
      mode: "可选，hist 需 symbol",
      symbol: "mode=hist 时必填",
    },
    returnDesc: "可转债行情",
  },
  bond_cb_meta: {
    params: { mode: "summary" },
    paramDesc: {
      mode: "summary 汇总|非 summary 需 symbol",
      symbol: "mode 非 summary 时必填",
    },
    returnDesc: "可转债概要/详情",
  },
  stock_board_industry: {
    params: {},
    paramDesc: {
      mode: "可选，hist 需 symbol/start_date/end_date",
      symbol: "mode=hist 时板块名称",
      period: "daily/weekly/monthly",
      start_date: "mode=hist 时",
      end_date: "mode=hist 时",
      adjust: "可选",
    },
    returnDesc: "行业板块列表/历史",
  },
  stock_board_concept: {
    params: {},
    paramDesc: {
      mode: "可选，hist 需 symbol/start_date/end_date",
      symbol: "mode=hist 时概念名称",
      period: "daily/weekly/monthly",
      start_date: "mode=hist 时",
      end_date: "mode=hist 时",
      adjust: "可选",
    },
    returnDesc: "概念板块列表/历史",
  },
  stock_index_zh_hist: {
    params: { symbol: "000001", start_date: "2024-01-01", end_date: "2024-01-31" },
    paramDesc: {
      symbol: "必填，指数代码如 000001(上证)、399001(深证)、399006(创业板)",
      start_date: "开始日期",
      end_date: "结束日期",
    },
    returnDesc: "股票指数历史日线",
  },
  stock_financial_abstract: {
    params: { symbol: "000001" },
    paramDesc: { symbol: "必填，股票代码" },
    returnDesc: "财务摘要指标",
  },
  stock_yjbb_em: {
    params: { date: "20241231" },
    paramDesc: { date: "必填，报告期 YYYYMMDD，如 20241231/20240930" },
    returnDesc: "业绩快报",
  },
  stock_yjyg_em: {
    params: { date: "20241231" },
    paramDesc: { date: "必填，报告期 YYYYMMDD" },
    returnDesc: "业绩预告",
  },
  option_finance_board: {
    params: { symbol: "华夏上证50ETF期权", end_month: "2503" },
    paramDesc: {
      symbol: "可选，如华夏上证50ETF期权、华泰柏瑞沪深300ETF期权",
      end_month: "可选，到期月 YYMM，如 2503",
    },
    returnDesc: "金融期权行情板",
  },
  option_current_em: {
    params: {},
    paramDesc: {},
    returnDesc: "期权当日行情（东方财富全市场）",
  },
  option_sse_daily_sina: {
    params: { symbol: "10005050C2503M" },
    paramDesc: { symbol: "必填，上交所期权合约代码" },
    returnDesc: "上交所期权日线",
  },
  option_commodity_hist: {
    params: { symbol: "m2503-C-4000", exchange: "dce", trade_date: "2024-01-02" },
    paramDesc: {
      symbol: "必填，商品期权合约",
      exchange: "dce|shfe|czce",
      trade_date: "可选，YYYYMMDD",
    },
    returnDesc: "商品期权历史",
  },
};

async function isServerUp() {
  try {
    const res = await fetch(`${BASE}/health`, { signal: AbortSignal.timeout(2000) });
    const body = await res.json();
    return body?.ok === true;
  } catch {
    return false;
  }
}

async function invoke(interfaceName, params = {}, verifySsl = true) {
  const res = await fetch(`${BASE}/invoke`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      interface: interfaceName,
      params,
      verify_ssl: verifySsl,
    }),
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  return res.json();
}

async function main() {
  if (!(await isServerUp())) {
    console.error("错误：HTTP 服务器未启动。请先运行 .\\start_nossl.ps1 或 .\\start_nossl.cmd");
    process.exit(1);
  }

  const report = {
    timestamp: new Date().toISOString(),
    baseUrl: BASE,
    interfaces: {},
    summary: { total: 0, passed: 0, failed: 0, errors: [] },
  };

  const ifaceList = Object.entries(INTERFACE_SPEC);
  for (let i = 0; i < ifaceList.length; i++) {
    const [iface, spec] = ifaceList[i];
    process.stdout.write(`[${i + 1}/${ifaceList.length}] 测试 ${iface}...`);
    const entry = {
      interface: iface,
      params: spec.params,
      success: false,
      rowCount: 0,
      error: null,
      sampleRowKeys: [],
    };

    const useNoSsl = process.env.AKSHARE_NO_SSL_VERIFY === "1";
    try {
      let result = await invoke(iface, spec.params, !useNoSsl);
      if (!result.ok && !useNoSsl) {
        const msg = result.error?.message ?? "";
        if (/certificate|ssl|connection aborted|remote.*disconnect/i.test(msg)) {
          result = await invoke(iface, spec.params, false);
        }
      }
      if (result.ok) {
        entry.success = true;
        entry.rowCount = result.returned_rows ?? (result.rows?.length ?? 0);
        const first = result.rows?.[0];
        if (first && typeof first === "object") {
          entry.sampleRowKeys = Object.keys(first).slice(0, 10);
        }
        entry.actualResponseSample = (result.rows ?? []).slice(0, 3);
      } else {
        entry.error = result.error?.message ?? JSON.stringify(result.error);
        entry.actualResponseSample = { error: result.error };
      }
    } catch (err) {
      entry.error = err?.message ?? String(err);
      entry.actualResponseSample = { error: err?.message ?? String(err) };
    }

    console.log(entry.success ? ` OK (${entry.rowCount})` : ` FAIL: ${entry.error}`);
    report.interfaces[iface] = entry;
    report.summary.total++;
    if (entry.success) {
      report.summary.passed++;
    } else {
      report.summary.failed++;
      report.summary.errors.push({ interface: iface, error: entry.error });
    }
  }

  // 输出报告目录
  const reportsDir = path.join(root, "reports");
  const docsDir = path.join(root, "docs");
  if (!fs.existsSync(reportsDir)) fs.mkdirSync(reportsDir, { recursive: true });
  if (!fs.existsSync(docsDir)) fs.mkdirSync(docsDir, { recursive: true });

  const reportPath = path.join(reportsDir, "api_test_report.json");
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf-8");
  console.log(`\n测试报告已写入: ${reportPath}`);

  // 生成 API 文档
  const apiDoc = generateApiDoc(report);
  const apiDocPath = path.join(docsDir, "API.md");
  fs.writeFileSync(apiDocPath, apiDoc, "utf-8");
  console.log(`API 文档已写入: ${apiDocPath}`);

  // 控制台摘要
  console.log("\n========== 接口测试结果 ==========");
  console.log(`总计: ${report.summary.total}  通过: ${report.summary.passed}  失败: ${report.summary.failed}\n`);

  for (const [iface, entry] of Object.entries(report.interfaces)) {
    const status = entry.success ? "✓" : "✗";
    const detail = entry.success ? `(${entry.rowCount} 行)` : `: ${entry.error}`;
    console.log(`  ${status} ${iface} ${detail}`);
  }

  if (report.summary.failed > 0) {
    console.log("\n失败原因分析:");
    for (const e of report.summary.errors) {
      console.log(`  - ${e.interface}: ${e.error}`);
    }
  }

  console.log("\n==================================\n");
}

function generateApiDoc(report) {
  const lines = [
    "# AKShare Node HTTP API 接口文档",
    "",
    "## 概述",
    "",
    "服务器地址：`http://127.0.0.1:8888`",
    "",
    "- `GET /health`：健康检查",
    "- `GET /tools`：可用接口列表",
    "- `POST /invoke`：调用数据接口",
    "",
    "## POST /invoke 请求体",
    "",
    "```json",
    '{ "interface": "接口名", "params": { ... }, "verify_ssl": false }',
    "```",
    "",
    "## 返回值通用结构（成功时）",
    "",
    "```json",
    JSON.stringify(
      {
        ok: true,
        interface: "接口名",
        params: {},
        cache_hit: false,
        estimated_row_bytes: 100,
        max_rows: 20,
        requested_rows: 100,
        returned_rows: 20,
        sampling_step: 5,
        rows: [{ /* 数据行 */ }],
      },
      null,
      2
    ),
    "```",
    "",
    "## 各接口说明",
    "",
  ];

  for (const [iface, spec] of Object.entries(INTERFACE_SPEC)) {
    const entry = report.interfaces[iface];
    const status = entry?.success ? "✓ 测试通过" : `✗ 测试失败: ${entry?.error ?? "未知"}`;

    lines.push(`### ${iface}`);
    lines.push("");
    lines.push(`- **说明**：${spec.returnDesc}`);
    lines.push(`- **测试状态**：${status}`);
    if (entry?.success && entry.sampleRowKeys?.length) {
      lines.push(`- **返回字段示例**：${entry.sampleRowKeys.join(", ")}`);
    }
    if (entry?.actualResponseSample) {
      lines.push("");
      lines.push("**实际调用返回数据示例**：");
      lines.push("```json");
      const sample = entry.actualResponseSample;
      lines.push(JSON.stringify(Array.isArray(sample) ? sample : sample, null, 2));
      lines.push("```");
    }
    lines.push("");
    lines.push("**入参 (params)**：");
    lines.push("");
    lines.push("| 参数 | 说明 |");
    lines.push("|------|------|");
    for (const [k, v] of Object.entries(spec.paramDesc)) {
      lines.push(`| ${k} | ${v} |`);
    }
    lines.push("");
    lines.push("**测试用最小参数**：");
    lines.push("");
    lines.push("```json");
    lines.push(JSON.stringify(spec.params, null, 2));
    lines.push("```");
    lines.push("");
  }

  lines.push("## SSL 与数据源说明");
  lines.push("");
  lines.push("### SSL 验证");
  lines.push("- **默认启用 SSL 验证**。在正常网络环境下，启用 SSL 通常更稳定，数据源连接成功率更高。");
  lines.push("- 若在企业代理/防火墙环境下出现 `certificate verify failed` 等错误，可设置环境变量 `AKSHARE_NO_SSL_VERIFY=1` 或请求时传 `verify_ssl: false`。");
  lines.push("- 测试报告会先尝试 SSL，若检测到证书/连接类错误会自动重试禁用 SSL。");
  lines.push("");
  lines.push("### 数据源回退");
  lines.push("部分接口已实现多数据源回退，主源失败时自动尝试备选：");
  lines.push("| 接口 | 主源 | 备选 |");
  lines.push("|------|------|------|");
  lines.push("| stock_zh_a_spot | 东方财富 | 新浪 |");
  lines.push("| stock_board_industry | 东方财富 | 同花顺 |");
  lines.push("| stock_board_concept | 东方财富 | 同花顺 |");
  lines.push("| fund_etf_market | 东方财富 | 同花顺 |");
  lines.push("| futures_zh_hist | 新浪/东方财富 | 互相回退 |");
  lines.push("| bond_zh_hs_market | 新浪 | 少页数重试 |");
  lines.push("");
  lines.push("### 雅虎数据源");
  lines.push("AKShare 主要使用东方财富、新浪、同花顺等国内数据源。A 股、期货、基金等境内品种**无雅虎数据源**，雅虎财经不覆盖 A 股市场。");
  lines.push("");
  lines.push("## 测试报告");
  lines.push("");
  lines.push(`生成时间：${report.timestamp}`);
  lines.push(`通过：${report.summary.passed} / ${report.summary.total}`);
  lines.push("");
  return lines.join("\n");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
