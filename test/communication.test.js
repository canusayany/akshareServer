/**
 * Node–Python communication tests.
 *
 * All tests use AKSHARE_NODE_TEST_MODE=1 so the Python side runs the
 * StubBackend and never makes real network requests.  This lets the whole
 * suite run offline while still exercising the full subprocess spawn →
 * JSON serialisation → response-parse pipeline for every supported interface.
 *
 * Coverage:
 *   - All 19 supported interfaces callable without error
 *   - Standard response shape on every interface
 *   - Params are normalised and echoed back correctly
 *   - SQLite cache returns cache_hit=true on second identical call
 *   - AKSHARE_NO_SSL_VERIFY env var is forwarded to the subprocess without
 *     breaking the call (verifies the SSL-patch code-path does not crash)
 *   - Unknown interface produces a rejected promise, not a crash
 */
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { createClient } from "../src/index.js";

const PYTHON_BIN = os.platform() === "win32" ? "py" : "python3";
const PROJECT_ROOT = process.cwd();

function tmpDb(label) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "akshare-comm-"));
  return path.join(dir, `${label}.sqlite`);
}

/** Create a client pointing at the StubBackend. */
function testClient(extraOptions = {}) {
  return createClient({
    pythonBin: PYTHON_BIN,
    projectRoot: PROJECT_ROOT,
    dbPath: tmpDb("default"),
    env: { AKSHARE_NODE_TEST_MODE: "1" },
    ...extraOptions,
  });
}

/**
 * Assert the seven required fields that every bridge response must have.
 * @param {object} result
 * @param {string} iface
 */
function assertShape(result, iface) {
  assert.equal(result.ok, true, `${iface}: ok must be true`);
  assert.equal(result.interface, iface, `${iface}: interface name mismatch`);
  assert.ok(Array.isArray(result.rows), `${iface}: rows must be an array`);
  assert.equal(typeof result.cache_hit, "boolean", `${iface}: cache_hit must be boolean`);
  assert.equal(typeof result.estimated_row_bytes, "number", `${iface}: estimated_row_bytes must be number`);
  assert.equal(typeof result.max_rows, "number", `${iface}: max_rows must be number`);
  assert.equal(typeof result.requested_rows, "number", `${iface}: requested_rows must be number`);
  assert.equal(typeof result.returned_rows, "number", `${iface}: returned_rows must be number`);
  assert.equal(typeof result.sampling_step, "number", `${iface}: sampling_step must be number`);
  assert.ok(result.returned_rows >= 0, `${iface}: returned_rows must be non-negative`);
  assert.ok(result.returned_rows <= result.requested_rows, `${iface}: returned_rows <= requested_rows`);
}

// ---------------------------------------------------------------------------
// A 股
// ---------------------------------------------------------------------------

test("stock_zh_a_spot — no params returns real-time rows", async () => {
  const c = testClient({ dbPath: tmpDb("spot") });
  const r = await c.stock_zh_a_spot();
  assertShape(r, "stock_zh_a_spot");
  assert.ok(r.rows.length > 0, "should have at least one row");
});

test("stock_zh_a_spot — symbol param is forwarded", async () => {
  const c = testClient({ dbPath: tmpDb("spot-sym") });
  const r = await c.stock_zh_a_spot({ symbol: "000001" });
  assertShape(r, "stock_zh_a_spot");
  assert.equal(r.params.symbol, "000001");
});

test("stock_zh_a_hist — daily period returns rows", async () => {
  const c = testClient({ dbPath: tmpDb("hist-daily") });
  const r = await c.stock_zh_a_hist({
    symbol: "000001",
    period: "daily",
    start_date: "2024-01-01",
    end_date: "2024-01-31",
  });
  assertShape(r, "stock_zh_a_hist");
  assert.ok(r.rows.length > 0);
  assert.equal(r.params.symbol, "000001");
  assert.equal(r.params.period, "daily");
});

test("stock_zh_a_hist — 30m intraday rows carry symbol and datetime", async () => {
  const c = testClient({ dbPath: tmpDb("hist-30m") });
  const r = await c.stock_zh_a_hist({
    symbol: "000001",
    period: "30m",
    start_date: "2024-01-02 09:30:00",
    end_date: "2024-01-02 15:00:00",
  });
  assertShape(r, "stock_zh_a_hist");
  assert.ok(r.rows.length > 0);
  assert.equal(r.rows[0].symbol, "000001");
  assert.ok(typeof r.rows[0].datetime === "string", "datetime field must be a string");
});

test("stock_zh_a_hist — adjust param is echoed in params", async () => {
  const c = testClient({ dbPath: tmpDb("hist-adjust") });
  const r = await c.stock_zh_a_hist({
    symbol: "600036",
    period: "daily",
    start_date: "2024-01-01",
    end_date: "2024-01-31",
    adjust: "qfq",
  });
  assertShape(r, "stock_zh_a_hist");
  assert.equal(r.params.adjust, "qfq");
  assert.equal(r.params.symbol, "600036");
});

test("stock_intraday_em — returns intraday rows for symbol", async () => {
  const c = testClient({ dbPath: tmpDb("intraday") });
  const r = await c.stock_intraday_em({ symbol: "000001" });
  assertShape(r, "stock_intraday_em");
});

test("stock_bid_ask_em — returns order book rows for symbol", async () => {
  const c = testClient({ dbPath: tmpDb("bidask") });
  const r = await c.stock_bid_ask_em({ symbol: "000001" });
  assertShape(r, "stock_bid_ask_em");
});

// ---------------------------------------------------------------------------
// 期货
// ---------------------------------------------------------------------------

test("futures_zh_spot — no params returns spot rows", async () => {
  const c = testClient({ dbPath: tmpDb("fspot") });
  const r = await c.futures_zh_spot();
  assertShape(r, "futures_zh_spot");
});

test("futures_zh_hist — returns historical rows for symbol", async () => {
  const c = testClient({ dbPath: tmpDb("fhist") });
  const r = await c.futures_zh_hist({ symbol: "RB0" });
  assertShape(r, "futures_zh_hist");
  assert.ok(r.rows.length > 0);
});

test("match_main_contract — returns contract rows for exchange", async () => {
  const c = testClient({ dbPath: tmpDb("main-contract") });
  const r = await c.match_main_contract({ symbol: "cffex" });
  assertShape(r, "match_main_contract");
});

test("futures_basis — no params returns basis rows", async () => {
  const c = testClient({ dbPath: tmpDb("basis") });
  const r = await c.futures_basis();
  assertShape(r, "futures_basis");
});

// ---------------------------------------------------------------------------
// 基金
// ---------------------------------------------------------------------------

test("fund_meta — no params returns fund metadata rows", async () => {
  const c = testClient({ dbPath: tmpDb("fund-meta") });
  const r = await c.fund_meta();
  assertShape(r, "fund_meta");
});

test("fund_etf_market — no params returns ETF market rows", async () => {
  const c = testClient({ dbPath: tmpDb("etf") });
  const r = await c.fund_etf_market();
  assertShape(r, "fund_etf_market");
});

test("fund_open_info — symbol param is required and forwarded", async () => {
  const c = testClient({ dbPath: tmpDb("fund-open") });
  const r = await c.fund_open_info({ symbol: "110011" });
  assertShape(r, "fund_open_info");
  assert.equal(r.params.symbol, "110011");
});

// ---------------------------------------------------------------------------
// 宏观
// ---------------------------------------------------------------------------

test("macro_china_all — returns merged dataset rows", async () => {
  const c = testClient({ dbPath: tmpDb("macro") });
  const r = await c.macro_china_all();
  assertShape(r, "macro_china_all");
  assert.ok(r.rows.length >= 4, "macro must return at least 4 dataset rows");
  assert.ok(
    r.rows.every((row) => typeof row.dataset === "string"),
    "every macro row must have a dataset field",
  );
});

test("macro_china_all — datasets filter param is forwarded", async () => {
  const c = testClient({ dbPath: tmpDb("macro-filter") });
  const r = await c.macro_china_all({ datasets: ["macro_china_cpi", "macro_china_lpr"] });
  assertShape(r, "macro_china_all");
  assert.deepEqual(r.params.datasets, ["macro_china_cpi", "macro_china_lpr"]);
});

// ---------------------------------------------------------------------------
// 商品
// ---------------------------------------------------------------------------

test("commodity_basis — no params returns basis rows", async () => {
  const c = testClient({ dbPath: tmpDb("commodity") });
  const r = await c.commodity_basis();
  assertShape(r, "commodity_basis");
});

test("spot_sge — no params returns SGE spot rows", async () => {
  const c = testClient({ dbPath: tmpDb("sge") });
  const r = await c.spot_sge();
  assertShape(r, "spot_sge");
});

// ---------------------------------------------------------------------------
// 债券
// ---------------------------------------------------------------------------

test("bond_zh_hs_market — no params returns bond market rows", async () => {
  const c = testClient({ dbPath: tmpDb("bond-mkt") });
  const r = await c.bond_zh_hs_market();
  assertShape(r, "bond_zh_hs_market");
});

test("bond_zh_hs_cov_market — no params returns convertible bond rows", async () => {
  const c = testClient({ dbPath: tmpDb("bond-cov") });
  const r = await c.bond_zh_hs_cov_market();
  assertShape(r, "bond_zh_hs_cov_market");
});

test("bond_cb_meta — summary mode returns rows", async () => {
  const c = testClient({ dbPath: tmpDb("bond-meta") });
  const r = await c.bond_cb_meta({ mode: "summary" });
  assertShape(r, "bond_cb_meta");
  assert.equal(r.params.mode, "summary");
});

// ---------------------------------------------------------------------------
// 板块
// ---------------------------------------------------------------------------

test("stock_board_industry — no params returns industry rows", async () => {
  const c = testClient({ dbPath: tmpDb("board-ind") });
  const r = await c.stock_board_industry();
  assertShape(r, "stock_board_industry");
});

test("stock_board_concept — no params returns concept rows", async () => {
  const c = testClient({ dbPath: tmpDb("board-con") });
  const r = await c.stock_board_concept();
  assertShape(r, "stock_board_concept");
});

// ---------------------------------------------------------------------------
// 期权
// ---------------------------------------------------------------------------

test("option_finance_board — returns option board rows", async () => {
  const c = testClient({ dbPath: tmpDb("opt-fin") });
  const r = await c.option_finance_board({ symbol: "华夏上证50ETF期权", end_month: "2503" });
  assertShape(r, "option_finance_board");
  assert.ok(r.rows.length > 0);
});

test("option_current_em — no params returns option spot rows", async () => {
  const c = testClient({ dbPath: tmpDb("opt-em") });
  const r = await c.option_current_em();
  assertShape(r, "option_current_em");
  assert.ok(r.rows.length > 0);
});

test("option_sse_daily_sina — symbol param returns daily rows", async () => {
  const c = testClient({ dbPath: tmpDb("opt-sse") });
  const r = await c.option_sse_daily_sina({ symbol: "10005050C2503M" });
  assertShape(r, "option_sse_daily_sina");
  assert.ok(r.rows.length > 0);
});

test("option_commodity_hist — returns commodity option rows", async () => {
  const c = testClient({ dbPath: tmpDb("opt-comm") });
  const r = await c.option_commodity_hist({ symbol: "m2503-C-4000", exchange: "dce", trade_date: "2024-01-02" });
  assertShape(r, "option_commodity_hist");
  assert.ok(r.rows.length > 0);
});

// ---------------------------------------------------------------------------
// 指数、财务、业绩
// ---------------------------------------------------------------------------

test("stock_index_zh_hist — returns index daily rows", async () => {
  const c = testClient({ dbPath: tmpDb("index-hist") });
  const r = await c.stock_index_zh_hist({
    symbol: "000001",
    start_date: "2024-01-01",
    end_date: "2024-01-31",
  });
  assertShape(r, "stock_index_zh_hist");
  assert.ok(r.rows.length > 0);
});

test("stock_financial_abstract — symbol param returns financial rows", async () => {
  const c = testClient({ dbPath: tmpDb("financial") });
  const r = await c.stock_financial_abstract({ symbol: "000001" });
  assertShape(r, "stock_financial_abstract");
  assert.ok(r.rows.length > 0);
});

test("stock_yjbb_em — date param returns performance report rows", async () => {
  const c = testClient({ dbPath: tmpDb("yjbb") });
  const r = await c.stock_yjbb_em({ date: "20241231" });
  assertShape(r, "stock_yjbb_em");
  assert.ok(r.rows.length > 0);
});

test("stock_yjyg_em — date param returns performance forecast rows", async () => {
  const c = testClient({ dbPath: tmpDb("yjyg") });
  const r = await c.stock_yjyg_em({ date: "20241231" });
  assertShape(r, "stock_yjyg_em");
  assert.ok(r.rows.length > 0);
});

// ---------------------------------------------------------------------------
// 通用行为
// ---------------------------------------------------------------------------

test("cache — second identical call returns cache_hit=true", async () => {
  const dbPath = tmpDb("cache");
  const c = testClient({ dbPath });
  const first = await c.macro_china_all();
  const second = await c.macro_china_all();
  assert.equal(first.cache_hit, false, "first call must be a cache miss");
  assert.equal(second.cache_hit, true, "second identical call must be a cache hit");
  assert.deepEqual(first.rows, second.rows, "cached rows must be identical to original");
});

test("cache — different params produce independent cache entries", async () => {
  const dbPath = tmpDb("cache-params");
  const c = testClient({ dbPath });
  const r1 = await c.stock_zh_a_hist({ symbol: "000001", period: "daily", start_date: "2024-01-01", end_date: "2024-01-31" });
  const r2 = await c.stock_zh_a_hist({ symbol: "000002", period: "daily", start_date: "2024-01-01", end_date: "2024-01-31" });
  assert.equal(r1.cache_hit, false);
  assert.equal(r2.cache_hit, false, "different symbol must be a separate cache miss");
});

test("unknown interface — invoke() rejects with descriptive error", async () => {
  const c = testClient({ dbPath: tmpDb("unknown") });
  await assert.rejects(
    () => c.invoke("not_a_real_interface", {}),
    (err) => {
      assert.ok(err instanceof Error);
      assert.ok(
        err.message.includes("not_a_real_interface") || err.message.includes("Unsupported"),
        `error message should mention the interface name or 'Unsupported', got: ${err.message}`,
      );
      return true;
    },
  );
});

test("AKSHARE_NO_SSL_VERIFY=1 — env var forwarded; patch does not crash subprocess", async () => {
  // The StubBackend never makes real HTTPS requests so this test stays
  // fully offline.  It exercises the _patch_ssl_if_needed() code path to
  // ensure it doesn't throw on import or during the patch application.
  const c = testClient({
    dbPath: tmpDb("ssl-patch"),
    env: {
      AKSHARE_NODE_TEST_MODE: "1",
      AKSHARE_NO_SSL_VERIFY: "1",
    },
  });
  const r = await c.stock_zh_a_spot();
  assertShape(r, "stock_zh_a_spot");
  assert.ok(r.rows.length > 0);
});

test("non-trading day — single-day query returns empty with message", async () => {
  const c = testClient({ dbPath: tmpDb("non-trading") });
  const r = await c.stock_zh_a_hist({
    symbol: "000001",
    period: "daily",
    start_date: "2024-01-06",
    end_date: "2024-01-06",
  });
  assert.equal(r.ok, true);
  assert.equal(r.interface, "stock_zh_a_hist");
  assert.equal(r.message, "非交易日");
  assert.ok(Array.isArray(r.rows));
  assert.equal(r.rows.length, 0);
  assert.equal(r.returned_rows, 0);
});

test("payload limit — rows are sampled evenly when byte budget is tight", async () => {
  // 540 bytes is enough for ~6–7 rows of the 10-row stub response.
  const c = testClient({ dbPath: tmpDb("limit"), maxBytes: 540 });
  const r = await c.stock_zh_a_hist({
    symbol: "000001",
    period: "30m",
    start_date: "2024-01-02 09:30:00",
    end_date: "2024-01-02 15:00:00",
  });
  assertShape(r, "stock_zh_a_hist");
  assert.equal(r.requested_rows, 10, "stub always returns 10 rows before limiting");
  assert.ok(r.returned_rows < r.requested_rows, "tight byte budget must reduce rows");
  assert.ok(r.sampling_step > 1, "sampling_step must be >1 when rows are reduced");
});
