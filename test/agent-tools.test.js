import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { createAgentToolRegistry } from "../src/agent-tools.js";

function createTempDbPath(name) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "akshare-agent-tools-"));
  return path.join(dir, `${name}.sqlite`);
}

function createRegistry(options = {}) {
  return createAgentToolRegistry({
    pythonBin: "py",
    projectRoot: process.cwd(),
    dbPath: createTempDbPath("registry"),
    env: {
      AKSHARE_NODE_TEST_MODE: "1",
    },
    ...options,
  });
}

test("agent registry exposes grouped tool metadata", async () => {
  const registry = createRegistry();
  assert.ok(Array.isArray(registry.groups.stock));
  assert.equal(registry.getGroup("macro")[0].name, "macro_china_all");
  assert.equal(registry.getTool("bond_cb_meta")?.group, "bond");
});

test("agent registry invokes grouped handlers", async () => {
  const registry = createRegistry();
  const result = await registry.invoke("macro_china_all", {});
  assert.equal(result.ok, true);
  assert.equal(result.interface, "macro_china_all");
});

test("agent registry rejects unsupported tools", async () => {
  const registry = createRegistry();
  await assert.rejects(() => registry.invoke("missing_tool", {}), /Unsupported tool/);
});

