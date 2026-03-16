import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { INTERFACE_GROUPS, createClient, createTypedClient } from "../src/index.js";

const PYTHON_BIN = os.platform() === "win32" ? "py" : "python3";

function createTempDbPath(name) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "akshare-node-"));
  return path.join(dir, `${name}.sqlite`);
}

function createTestClient(options = {}) {
  return createClient({
    pythonBin: PYTHON_BIN,
    projectRoot: process.cwd(),
    env: {
      AKSHARE_NODE_TEST_MODE: "1",
    },
    ...options,
  });
}

test("public client exposes documented functions", async () => {
  const client = createTestClient({ dbPath: createTempDbPath("methods") });
  assert.equal(typeof client.stock_zh_a_spot, "function");
  assert.equal(typeof client.stock_zh_a_hist, "function");
  assert.equal(typeof client.futures_zh_hist, "function");
  assert.equal(typeof client.fund_etf_market, "function");
  assert.equal(typeof client.macro_china_all, "function");
  assert.equal(typeof client.bond_zh_hs_market, "function");
  assert.equal(typeof client.stock_board_concept, "function");
});

test("typed client exposes grouped methods for injection", async () => {
  const typedClient = createTypedClient({
    pythonBin: PYTHON_BIN,
    projectRoot: process.cwd(),
    dbPath: createTempDbPath("typed"),
    env: {
      AKSHARE_NODE_TEST_MODE: "1",
    },
  });

  assert.deepEqual(INTERFACE_GROUPS.macro, ["macro_china_all"]);
  assert.equal(typeof typedClient.stock.stock_zh_a_spot, "function");
  assert.equal(typeof typedClient.futures.futures_zh_hist, "function");
  assert.equal(typeof typedClient.macro.macro_china_all, "function");
  assert.equal(typeof typedClient.bond.bond_cb_meta, "function");
});

test("bridge returns standardized response shape", async () => {
  const client = createTestClient({ dbPath: createTempDbPath("shape") });
  const result = await client.stock_zh_a_spot();
  assert.equal(result.ok, true);
  assert.equal(result.interface, "stock_zh_a_spot");
  assert.equal(Array.isArray(result.rows), true);
  assert.equal(typeof result.cache_hit, "boolean");
  assert.equal(typeof result.estimated_row_bytes, "number");
  assert.equal(typeof result.max_rows, "number");
  assert.equal(typeof result.requested_rows, "number");
  assert.equal(typeof result.returned_rows, "number");
  assert.equal(typeof result.sampling_step, "number");
});

test("second identical request hits sqlite cache", async () => {
  const dbPath = createTempDbPath("cache");
  const client = createTestClient({ dbPath });
  const first = await client.stock_zh_a_hist({
    symbol: "000001",
    period: "30m",
    start_date: "2024-01-02 09:30:00",
    end_date: "2024-01-02 15:00:00",
  });
  const second = await client.stock_zh_a_hist({
    symbol: "000001",
    period: "30m",
    start_date: "2024-01-02 09:30:00",
    end_date: "2024-01-02 15:00:00",
  });
  assert.equal(first.cache_hit, false);
  assert.equal(second.cache_hit, true);
});

test("payload limit reduces rows evenly without truncating only tail", async () => {
  const client = createTestClient({
    dbPath: createTempDbPath("limit"),
    maxBytes: 540,
  });
  const result = await client.stock_zh_a_hist({
    symbol: "000001",
    period: "30m",
    start_date: "2024-01-02 09:30:00",
    end_date: "2024-01-02 15:00:00",
  });
  assert.equal(result.ok, true);
  assert.equal(result.requested_rows, 10);
  assert.ok(result.returned_rows < result.requested_rows);
  assert.ok(result.sampling_step > 1);
  assert.deepEqual(
    result.rows.map((row) => row.datetime),
    [
      "2024-01-02 09:30:00",
      "2024-01-02 10:30:00",
      "2024-01-02 11:30:00",
      "2024-01-02 13:30:00",
      "2024-01-02 14:30:00",
      "2024-01-02 15:00:00",
    ],
  );
});

test("macro endpoint returns merged dataset rows", async () => {
  const client = createTestClient({ dbPath: createTempDbPath("macro"), maxBytes: 2000 });
  const result = await client.macro_china_all();

  assert.equal(result.ok, true);
  assert.equal(result.interface, "macro_china_all");
  assert.ok(result.rows.length >= 4);
  assert.equal(result.rows.every((row) => typeof row.dataset === "string"), true);
});

test("incremental cache: 先请求单月写入缓存，再请求跨月时命中已有月份、仅补齐缺失部分", async () => {
  const dbPath = createTempDbPath("incremental");
  const client = createTestClient({ dbPath, maxBytes: 2000 });
  // 1. 请求 1 月，写入缓存
  const jan = await client.stock_zh_a_hist({
    symbol: "000001",
    period: "daily",
    start_date: "2024-01-01",
    end_date: "2024-01-31",
  });
  assert.equal(jan.ok, true);
  assert.equal(jan.cache_hit, false);
  assert.ok(jan.rows.length >= 1);
  // 2. 请求 2 月，写入缓存
  const feb = await client.stock_zh_a_hist({
    symbol: "000001",
    period: "daily",
    start_date: "2024-02-01",
    end_date: "2024-02-29",
  });
  assert.equal(feb.ok, true);
  assert.equal(feb.cache_hit, false);
  assert.ok(feb.rows.length >= 1);
  // 3. 请求 1-2 月，应全部命中分片缓存
  const janFeb = await client.stock_zh_a_hist({
    symbol: "000001",
    period: "daily",
    start_date: "2024-01-01",
    end_date: "2024-02-29",
  });
  assert.equal(janFeb.ok, true);
  assert.equal(janFeb.cache_hit, true, "1 月和 2 月均已在缓存，应全命中");
  assert.ok(janFeb.rows.length >= jan.rows.length + feb.rows.length);
});
