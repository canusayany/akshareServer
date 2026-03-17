# 设计说明

## 1. 对外接口形态

保留接近 `akshare` 的命名风格，对明显重复的接口做了合并。共 27 个接口：

- `stock_zh_a_spot` — A 股实时行情
- `stock_zh_a_hist` — A 股历史行情
- `stock_intraday_em` — A 股分时成交
- `stock_bid_ask_em` — A 股盘口
- `stock_index_zh_hist` — 股票指数日线（沪深300、中证500 等）
- `stock_financial_abstract` — 财务摘要
- `stock_yjbb_em` — 业绩快报
- `stock_yjyg_em` — 业绩预告
- `futures_zh_spot` — 期货实时行情
- `futures_zh_hist` — 期货历史行情
- `match_main_contract` — 主力合约映射
- `futures_basis` — 期货基差结构
- `fund_meta` — 基金元信息
- `fund_etf_market` — ETF 行情
- `fund_open_info` — 开放式基金净值/指数
- `commodity_basis` — 商品/农产品基差
- `spot_sge` — 上海黄金交易所现货
- `bond_zh_hs_market` — 沪深债券行情
- `bond_zh_hs_cov_market` — 沪深可转债行情
- `bond_cb_meta` — 可转债元信息
- `stock_board_industry` — 行业板块
- `stock_board_concept` — 概念板块
- `option_finance_board` — 金融期权行情板
- `option_current_em` — 期权当日行情
- `option_sse_daily_sina` — 上交所期权日线
- `option_commodity_hist` — 商品期权历史

## 2. 标准返回结构

每个 Node 接口返回统一结构：

```json
{
  "ok": true,
  "interface": "stock_zh_a_hist",
  "params": {},
  "cache_hit": false,
  "estimated_row_bytes": 132,
  "max_rows": 15,
  "requested_rows": 20,
  "returned_rows": 10,
  "sampling_step": 2,
  "rows": []
}
```

| 字段 | 含义 |
|------|------|
| `ok` | 调用是否成功 |
| `interface` | 实际调用的接口名 |
| `params` | 归一化后的参数 |
| `cache_hit` | 是否命中 SQLite 缓存 |
| `estimated_row_bytes` | 估算的单行 UTF-8 字节数 |
| `max_rows` | 当前大小限制下允许的最大行数 |
| `requested_rows` | 原始结果行数 |
| `returned_rows` | 降频后的返回行数 |
| `sampling_step` | 均匀采样步长，1 表示未降频 |
| `rows` | 最终返回的数据行 |

## 3. 缓存设计

缓存键由「接口名 + 归一化参数 + max_bytes」组成。流程：

1. 查 SQLite 缓存
2. 命中 → 读缓存数据，执行大小限制
3. 未命中 → 调用 akshare，将归一化结果写入 SQLite，执行大小限制后返回

## 4. 数据量限制

- 默认单次响应最大字节数 `2000`，限制对象为 `rows` 的紧凑 JSON 序列化
- 单行估算：`estimated_row_size = ceil(total_payload_bytes / row_count)`，`max_rows = max(1, floor(max_bytes / estimated_row_size))`
- 超出时进行**均匀降频**（非简单截断）：按交易日分组，对每天按固定步长采样，同步增加步长直至总大小低于上限，以保留时间覆盖范围

## 5. A 股日内时段规则

单只股票 + 单日 + 分钟级历史：仅保留有效交易节点（09:30、10:00、10:30、11:00、11:30、13:00、13:30、14:00、14:30、15:00），过滤午休与闭市后无效数据。

## 5.1 非交易日

单日查询（spot 的当日、hist 的 start_date=end_date）若为非交易日，直接返回空 `rows`，`message` 为「非交易日」。使用 `exchange_calendars` 判断上交所交易日历。

## 5.2 数据源回退

| 类型 | 主源 | 备选 |
|------|------|------|
| A股行情 | 东方财富/新浪 | TuShare → Baostock |
| 指数日线 | AKShare | Baostock |
| 财务摘要 | AKShare | Baostock |
| 期货 | AKShare/新浪 | TuShare |

## 6. Node 与 Python 职责

| 侧 | 职责 |
|----|------|
| Node | 暴露 JS API、参数/返回值注释、启动 Python 桥接、适配 agent tool |
| Python | 调用 akshare、DataFrame→JSON、SQLite 缓存、大小估算/降频/时段过滤 |

## 7. 测试策略

- **Node 单元测试**：默认 StubBackend（`AKSHARE_NODE_TEST_MODE=1`），不发真实请求
- **Python 冒烟测试**：安装 akshare 后访问真实接口验证桥接链路

重点验证：接口可用性、SQLite 缓存命中、2KB 限制、均匀降频、非交易日空数据、agent tool 调用。

### 测试文件

| 文件 | 说明 |
|------|------|
| `communication.test.js` | 覆盖 27 个接口，StubBackend，subprocess 方式 |
| `server.test.js` | 自动启动 HTTP 服务（TEST_MODE=1），测 /health、/tools、/invoke |
| `http_api.test.js` | 对已运行 HTTP 服务全面测试，需先启动 `start_nossl.ps1` 或 `start_python_server.ps1` |

```powershell
node --test                          # 全部测试
node --test test/communication.test.js   # 仅通信测试
npm run test:report:stub             # 离线生成测试报告（入参/返回值）
npm run test:report:auto             # 启动真实服务并生成 api_test_report、API 文档
```

## 8. SSL 错误与修复

### 根因

akshare 向东方财富、新浪等发 HTTPS 请求。企业内网 TLS 检查代理用自签名证书替换服务器证书，导致：

```
requests.exceptions.SSLError: certificate verify failed: unable to get local issuer certificate
```

### 修复

`backend.py` 的 `_patch_ssl_if_needed()` 在 `AKSHARE_NO_SSL_VERIFY=1` 时对 `ssl`、`requests`、`httpx` 打补丁，强制 `verify=False`。补丁幂等。

```powershell
.\start_python_server.ps1 -NoSslVerify
# 或
$env:AKSHARE_NO_SSL_VERIFY = "1"
.\start_python_server.ps1
```

**注意**：关闭证书验证会降低 MITM 防御，仅在受信任企业代理环境下使用。

## 9. 常见问题

**Q: HTTP 请求是否必须使用 SSL？**

| 连接 | 协议 | 说明 |
|------|------|------|
| 客户端 → akshareServer | HTTP (127.0.0.1:8888) | 本地 HTTP，无需 SSL |
| akshare → 外部数据源 | HTTPS | 企业 TLS 代理下证书失败时，可设 `AKSHARE_NO_SSL_VERIFY=1` 或 `verify_ssl: false` |

**Q: 为什么 akshare 会“从网页抓取”？**

akshare 非官方 API，而是对东方财富、新浪等数据源的封装，内部通过 HTTP/HTTPS 请求并解析 JSON/HTML。akshareServer 只调用 akshare 函数，不直接抓网页。
