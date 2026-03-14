import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { createClient } from "../src/index.js";

function createTempDbPath(name) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "akshare-node-"));
  return path.join(dir, `${name}.sqlite`);
}

function createTestClient(options = {}) {
  return createClient({
    pythonBin: "py",
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
  assert.equal(typeof client.bond_zh_hs_market, "function");
  assert.equal(typeof client.stock_board_concept, "function");
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
