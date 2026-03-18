/**
 * 对外 HTTP 接口全面测试
 *
 * 覆盖所有对外暴露的 HTTP 端点：
 *   GET /health     - 健康检查
 *   GET /tools      - 可用接口列表
 *   POST /invoke    - 所有 20 个数据接口
 *
 * 服务器未运行时将跳过全部测试（不失败）。
 * 启动服务器方式（二选一）：
 *   真实数据：.\start_nossl.ps1
 *   离线测试：$env:AKSHARE_NODE_TEST_MODE="1"; .\start_python_server.ps1
 * 或使用 npm run test:http 自动启动服务器并运行本测试。
 *
 * 运行：node --test test/http_api.test.js
 */

import test from "node:test";
import assert from "node:assert/strict";

const BASE = "http://127.0.0.1:8888";
const TIMEOUT_MS = 60_000;
const LONG_RANGE_INDEX_PARAMS = { symbol: "000001", start_date: "2024-01-10", end_date: "2024-02-18" };

async function isServerUp() {
  try {
    const res = await fetch(`${BASE}/health`, { signal: AbortSignal.timeout(2000) });
    const body = await res.json();
    return body?.ok === true;
  } catch {
    return false;
  }
}

/** 每个接口的最小可用参数（覆盖必选参数） */
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

async function invoke(interfaceName, params = {}) {
  const res = await fetch(`${BASE}/invoke`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      interface: interfaceName,
      params,
      verify_ssl: false,
    }),
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  return res.json();
}

function assertSuccessShape(result, iface) {
  assert.equal(result.ok, true, `${iface}: ok 应为 true`);
  assert.equal(result.interface, iface);
  assert.ok(Array.isArray(result.rows), `${iface}: rows 应为数组`);
  assert.equal(typeof result.cache_hit, "boolean");
  assert.equal(typeof result.estimated_row_bytes, "number");
  assert.equal(typeof result.max_rows, "number");
  assert.equal(typeof result.requested_rows, "number");
  assert.equal(typeof result.returned_rows, "number");
  assert.equal(typeof result.sampling_step, "number");
}

const SERVER_UP = await isServerUp();
const SKIP_MSG = "HTTP 服务器未启动，请先运行 .\\start_nossl.ps1 或 $env:AKSHARE_NODE_TEST_MODE='1'; .\\start_python_server.ps1";

// ────────────────────────────────────────────────────────────
// 全部测试：服务器未运行时跳过
// ────────────────────────────────────────────────────────────
test("前置：服务器健康检查", { skip: !SERVER_UP ? SKIP_MSG : false }, async () => {
  const res = await fetch(`${BASE}/health`, { signal: AbortSignal.timeout(3000) });
  const body = await res.json();
  assert.equal(body.ok, true);
  assert.equal(body.host, "127.0.0.1");
  assert.equal(body.port, 8888);
});

test("前置：/tools 返回完整接口列表", { skip: !SERVER_UP }, async () => {
  const body = await fetch(`${BASE}/tools`).then((r) => r.json());
  assert.equal(body.ok, true);
  const expected = Object.keys(INTERFACE_PARAMS);
  for (const name of expected) {
    assert.ok(body.tools.includes(name), `接口 ${name} 应注册`);
  }
  assert.equal(body.tools.length, expected.length);
});

for (const [iface, params] of Object.entries(INTERFACE_PARAMS)) {
  test(`invoke: ${iface}`, { skip: !SERVER_UP }, async (t) => {
    const result = await invoke(iface, params);
    if (!result.ok) {
      const msg = result.error?.message ?? "";
      if (msg.includes("Unsupported interface") || (msg.includes("KeyError") && msg.includes("'"))) {
        assert.fail(`${iface} 不应报接口或参数解析错误: ${msg}`);
      }
      t.diagnostic(`数据源不可达（允许）: ${msg}`);
      return;
    }
    assertSuccessShape(result, iface);
  });
}

test("invoke: 未知接口返回 400 及错误信息", { skip: !SERVER_UP }, async () => {
  const result = await invoke("unknown_interface_xyz", {});
  assert.equal(result.ok, false);
  assert.ok(result.error?.message?.includes("unknown_interface_xyz") || result.error?.message?.includes("Unsupported"));
});

test("invoke: 缺少 interface 字段应返回错误", { skip: !SERVER_UP }, async () => {
  const res = await fetch(`${BASE}/invoke`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ params: {} }),
    signal: AbortSignal.timeout(5000),
  });
  const body = await res.json();
  assert.equal(body.ok, false);
  assert.ok(body.error && (typeof body.error === "string" || body.error?.message));
});

test("invoke: GET 请求 /invoke 返回 404", { skip: !SERVER_UP }, async () => {
  const res = await fetch(`${BASE}/invoke`, { method: "GET" });
  assert.equal(res.status, 404);
});

test("invoke: GET 随机路径返回 404", { skip: !SERVER_UP }, async () => {
  const res = await fetch(`${BASE}/random-path`, { method: "GET" });
  assert.equal(res.status, 404);
});

test("invoke: verify_ssl=false 不导致服务端报错", { skip: !SERVER_UP }, async () => {
  const result = await invoke("macro_china_all", {});
  assert.ok(result !== null && typeof result === "object");
  assert.ok("ok" in result);
});

test("invoke: stock_index_zh_hist 支持 40 天 000001 指数区间", { skip: !SERVER_UP }, async (t) => {
  const result = await invoke("stock_index_zh_hist", LONG_RANGE_INDEX_PARAMS);
  if (!result.ok) {
    const msg = result.error?.message ?? "";
    if (msg.includes("Unsupported interface") || (msg.includes("KeyError") && msg.includes("'"))) {
      assert.fail(`stock_index_zh_hist 40 天用例不应报接口或参数解析错误: ${msg}`);
    }
    t.diagnostic(`40 天指数用例外部数据源失败（允许）: ${msg}`);
    return;
  }

  assertSuccessShape(result, "stock_index_zh_hist");
  assert.ok(result.returned_rows >= 1, "40 天区间至少应返回 1 行数据");
  assert.equal(result.params.symbol, LONG_RANGE_INDEX_PARAMS.symbol);
  assert.equal(result.params.start_date, LONG_RANGE_INDEX_PARAMS.start_date);
  assert.equal(result.params.end_date, LONG_RANGE_INDEX_PARAMS.end_date);
  assert.ok("date" in result.rows[0], "指数行数据应包含 date 字段");
});

// ────────────────────────────────────────────────────────────
// 参数防御与 LLM 兼容
// ────────────────────────────────────────────────────────────
test("invoke: 缺少必填参数 symbol 应返回 400 及 hint", { skip: !SERVER_UP }, async () => {
  const result = await invoke("stock_zh_a_hist", { period: "daily", start_date: "2024-01-01", end_date: "2024-01-31" });
  assert.equal(result.ok, false);
  assert.ok(result.error?.message?.includes("symbol") || result.error?.message?.includes("需要参数"));
  assert.ok(result.error?.hint != null || result.error?.message?.length > 0);
});

test("invoke: symbol 为数字应自动转为字符串", { skip: !SERVER_UP }, async () => {
  const result = await invoke("stock_zh_a_hist", {
    symbol: 600519,
    period: "daily",
    start_date: "2024-01-01",
    end_date: "2024-01-31",
  });
  assert.equal(result.ok, true, "symbol 数字应被规范化");
  assert.ok(Array.isArray(result.rows));
});

test("invoke: params 为 null 时服务端应使用空对象", { skip: !SERVER_UP }, async () => {
  const res = await fetch(`${BASE}/invoke`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ interface: "stock_zh_a_spot", params: null, verify_ssl: false }),
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  const body = await res.json();
  assert.equal(body.ok, true, "params=null 应被转为 {}");
});

test("invoke: code 映射为 symbol 应兼容", { skip: !SERVER_UP }, async () => {
  const result = await invoke("stock_zh_a_hist", {
    code: "000001",
    period: "daily",
    start_date: "2024-01-01",
    end_date: "2024-01-31",
  });
  assert.equal(result.ok, true, "code 应映射为 symbol");
  assert.ok(Array.isArray(result.rows));
});
