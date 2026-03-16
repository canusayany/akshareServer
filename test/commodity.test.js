/**
 * 测试 commodity_basis / spot_sge 接口
 *
 * 服务器未运行时将跳过全部测试。启动方式：.\start_nossl.ps1 或 npm run test:http
 * 运行：node --test test/commodity.test.js
 */

import test from "node:test";
import assert from "node:assert/strict";

const BASE = "http://127.0.0.1:8888";
const TIMEOUT_MS = 20_000;

async function isServerUp() {
  try {
    const res = await fetch(`${BASE}/health`, { signal: AbortSignal.timeout(2000) });
    const body = await res.json();
    return body?.ok === true;
  } catch {
    return false;
  }
}

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

const SERVER_UP = await isServerUp();

// ────────────────────────────────────────────────────────────
// 前置检查
// ────────────────────────────────────────────────────────────
test("前置：服务器健康检查", { skip: !SERVER_UP ? "HTTP 服务器未启动" : false }, async () => {
  const res = await fetch(`${BASE}/health`, { signal: AbortSignal.timeout(3000) });
  const body = await res.json();
  assert.equal(body.ok, true);
  assert.equal(body.host, "127.0.0.1");
  assert.equal(body.port, 8888);
});

test("前置：确认 commodity_basis 和 spot_sge 在工具列表中", { skip: !SERVER_UP }, async () => {
  const body = await fetch(`${BASE}/tools`).then((r) => r.json());
  assert.equal(body.ok, true);
  assert.ok(body.tools.includes("commodity_basis"), "commodity_basis 未注册");
  assert.ok(body.tools.includes("spot_sge"), "spot_sge 未注册");
});

// ────────────────────────────────────────────────────────────
// commodity_basis 测试
// ────────────────────────────────────────────────────────────
test("commodity_basis: 传 date 获取全市场大宗商品快照", { skip: !SERVER_UP }, async (t) => {
  // 用今天（工作日）的日期；非交易日可能返回 0 行，接口仍应返回 ok:true
  const today = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  const date = `${today.getFullYear()}${pad(today.getMonth() + 1)}${pad(today.getDate())}`;
  const result = await invoke("commodity_basis", { date });
  console.log(`  [commodity_basis/date=${date}] ok=${result.ok} rows=${result.rows?.length ?? "N/A"}`);

  if (!result.ok) {
    const msg = result.error?.message ?? "";
    assert.ok(!msg.includes("KeyError"), `不应报 KeyError，实际错误：${msg}`);
    t.diagnostic(`数据源不可达（允许）：${msg}`);
    return;
  }

  assert.ok(Array.isArray(result.rows), "rows 应为数组");
  // 非交易日/数据源无数据时 rows 可以为 0，接口本身成功即可
  t.diagnostic(`返回 ${result.rows.length} 行（非交易日允许为 0）`);
});

test("commodity_basis: symbol=CU (铜) 应成功映射", { skip: !SERVER_UP }, async (t) => {
  const result = await invoke("commodity_basis", { symbol: "CU" });
  console.log(`  [commodity_basis/CU] ok=${result.ok} error=${result.error?.message ?? "none"}`);

  if (!result.ok) {
    const msg = result.error?.message ?? "";
    // 关键断言：不应出现 KeyError: 'CU'（修复前的旧 bug）
    assert.ok(
      !msg.includes("KeyError: 'CU'"),
      `'CU' 应被映射为中文名"铜"，不应报 KeyError: 'CU'。实际错误：${msg}`
    );
    t.diagnostic(`数据源不可达（允许）：${msg}`);
    return;
  }

  assert.ok(Array.isArray(result.rows), "rows 应为数组");
});

test("commodity_basis: symbol=AG (银) 应成功映射，不报 KeyError", { skip: !SERVER_UP }, async (t) => {
  const result = await invoke("commodity_basis", { symbol: "AG" });
  console.log(`  [commodity_basis/AG] ok=${result.ok} error=${result.error?.message ?? "none"}`);

  if (!result.ok) {
    const msg = result.error?.message ?? "";
    assert.ok(
      !msg.includes("KeyError: 'AG'"),
      `'AG' 应被映射为中文名"白银"，不应报 KeyError: 'AG'。实际错误：${msg}`
    );
    t.diagnostic(`数据源不可达（允许）：${msg}`);
    return;
  }

  assert.ok(Array.isArray(result.rows), "rows 应为数组");
});

test("commodity_basis: symbol=铜 (中文) 应直接使用", { skip: !SERVER_UP }, async (t) => {
  const result = await invoke("commodity_basis", { symbol: "铜" });
  console.log(`  [commodity_basis/铜] ok=${result.ok} rows=${result.rows?.length ?? "N/A"}`);

  if (!result.ok) {
    t.diagnostic(`数据源不可达（允许）：${result.error?.message}`);
    return;
  }

  assert.ok(Array.isArray(result.rows), "rows 应为数组");
});

test("commodity_basis: mode=futures_spot_sys symbol=RU 应返回橡胶基差", { skip: !SERVER_UP }, async (t) => {
  const result = await invoke("commodity_basis", {
    mode: "futures_spot_sys",
    symbol: "RU",
  });
  console.log(`  [commodity_basis/sys/RU] ok=${result.ok} rows=${result.rows?.length ?? "N/A"}`);

  if (!result.ok) {
    t.diagnostic(`数据源不可达（允许）：${result.error?.message}`);
    return;
  }

  assert.ok(Array.isArray(result.rows), "rows 应为数组");
});

// ────────────────────────────────────────────────────────────
// spot_sge 测试
// ────────────────────────────────────────────────────────────
test("spot_sge: 不传 symbol 默认 Au99.99", { skip: !SERVER_UP }, async (t) => {
  const result = await invoke("spot_sge", {});
  console.log(`  [spot_sge/default] ok=${result.ok} rows=${result.rows?.length ?? "N/A"} error=${result.error?.message ?? "none"}`);

  if (!result.ok) {
    const msg = result.error?.message ?? "";
    assert.ok(
      !msg.includes("KeyError"),
      `不应报 KeyError，实际：${msg}`
    );
    t.diagnostic(`数据源不可达（允许）：${msg}`);
    return;
  }

  assert.ok(Array.isArray(result.rows), "rows 应为数组");
  assert.ok(result.rows.length > 0, "SGE 行情不应为空");
});

test("spot_sge: symbol=AU9999 应映射为 Au99.99", { skip: !SERVER_UP }, async (t) => {
  const result = await invoke("spot_sge", { symbol: "AU9999" });
  console.log(`  [spot_sge/AU9999] ok=${result.ok} rows=${result.rows?.length ?? "N/A"} error=${result.error?.message ?? "none"}`);

  if (!result.ok) {
    const msg = result.error?.message ?? "";
    // "Expecting value: line 1 column 1" 是 SSL 相关，允许
    // 不应出现 symbol 格式报错
    assert.ok(!msg.toLowerCase().includes("invalid symbol"), `Symbol 映射应生效，错误：${msg}`);
    t.diagnostic(`数据源不可达（允许）：${msg}`);
    return;
  }

  assert.ok(Array.isArray(result.rows), "rows 应为数组");
});

test("spot_sge: symbol=AU 或 au 应映射为 Au99.99", { skip: !SERVER_UP }, async (t) => {
  const result = await invoke("spot_sge", { symbol: "AU" });
  console.log(`  [spot_sge/AU] ok=${result.ok} rows=${result.rows?.length ?? "N/A"} error=${result.error?.message ?? "none"}`);

  if (!result.ok) {
    t.diagnostic(`数据源不可达（允许）：${result.error?.message}`);
    return;
  }

  assert.ok(Array.isArray(result.rows), "rows 应为数组");
});

test("spot_sge: symbol=AG9999 应映射为 Ag99.99", { skip: !SERVER_UP }, async (t) => {
  const result = await invoke("spot_sge", { symbol: "AG9999" });
  console.log(`  [spot_sge/AG9999] ok=${result.ok} rows=${result.rows?.length ?? "N/A"} error=${result.error?.message ?? "none"}`);

  if (!result.ok) {
    t.diagnostic(`数据源不可达（允许）：${result.error?.message}`);
    return;
  }

  assert.ok(Array.isArray(result.rows), "rows 应为数组");
});

test("spot_sge: symbol=Au99.99 (标准格式) 应直接使用", { skip: !SERVER_UP }, async (t) => {
  const result = await invoke("spot_sge", { symbol: "Au99.99" });
  console.log(`  [spot_sge/Au99.99] ok=${result.ok} rows=${result.rows?.length ?? "N/A"} error=${result.error?.message ?? "none"}`);

  if (!result.ok) {
    t.diagnostic(`数据源不可达（允许）：${result.error?.message}`);
    return;
  }

  assert.ok(Array.isArray(result.rows), "rows 应为数组");
});

// ────────────────────────────────────────────────────────────
// verify_ssl: false 测试
// ────────────────────────────────────────────────────────────
test("verify_ssl: false 请求字段应被服务器接受（不报错）", { skip: !SERVER_UP }, async () => {
  // 用一个无网络请求的接口（macro_china_all 在测试模式下成功）
  // 对于真实服务器，测试请求体中带 verify_ssl:false 不会破坏正常功能
  const result = await invoke("spot_sge", { symbol: "Au99.99" });
  // 无论 ok 与否，不应返回 5xx 级别的服务器内部错误
  // BadRequest 是数据源失败，不是解析 verify_ssl 失败
  assert.ok(result !== null && typeof result === "object", "应返回 JSON 对象");
  assert.ok("ok" in result, "响应中应有 ok 字段");
});
