import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { createAkshareTool } from "../src/tool.js";

function createTempDbPath(name) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "akshare-tool-"));
  return path.join(dir, `${name}.sqlite`);
}

function createTestTool(options = {}) {
  return createAkshareTool({
    pythonBin: "py",
    projectRoot: process.cwd(),
    dbPath: createTempDbPath("tool"),
    env: {
      AKSHARE_NODE_TEST_MODE: "1",
    },
    ...options,
  });
}

test("tool layer lists supported tools", async () => {
  const tool = createTestTool();
  const definitions = tool.listTools();
  assert.ok(definitions.length >= 10);
  assert.equal(definitions.some((item) => item.name === "stock_zh_a_hist"), true);
  assert.equal(definitions.some((item) => item.name === "macro_china_all"), true);
  assert.equal(definitions.some((item) => item.name === "bond_cb_meta"), true);
});

test("tool layer delegates calls to client methods", async () => {
  const tool = createTestTool();
  const result = await tool.call("stock_zh_a_spot", { symbol: "000001" });
  assert.equal(result.ok, true);
  assert.equal(result.interface, "stock_zh_a_spot");
});

test("tool layer rejects unsupported tools", async () => {
  const tool = createTestTool();
  await assert.rejects(() => tool.call("not_exists", {}), /Unsupported tool/);
});
