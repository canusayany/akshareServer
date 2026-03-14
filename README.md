# akshare-node

基于 Python `akshare` 的 Node.js 数据库，内置 SQLite 缓存，适合在 Node 工程或 agent tool 中直接调用。

## 目标

- 使用 Python + `akshare` 获取市场数据。
- 对 Node 暴露稳定的、接近 `akshare` 风格的调用接口。
- 使用 SQLite 缓存请求结果，优先复用本地缓存。
- 保证单次返回的数据行 JSON 负载不超过 `2000` UTF-8 字节。
- 当调用方请求的数据条数超过上限时，按“每天均匀降频”的方式减少数据，而不是只截掉头部或尾部。
- 对单日单标的分时数据，只保留有效交易时段，不采集闭市无效数据。

## 当前覆盖范围

- A 股
- 期货
- 基金
- 商品与大宗商品
- 债券
- 行业与概念板块

## 项目结构

- `src/index.js`：Node 客户端，对外导出完整函数。
- `src/tool.js`：适配 agent tool 的统一调用层。
- `python/akshare_node_bridge`：Python 桥接、AKShare 适配、SQLite 缓存、数据量限制逻辑。
- `test/index.test.js`：Node 客户端测试。
- `test/tool.test.js`：agent tool 调用层测试。
- `docs/design.md`：设计说明。

## 运行方式

Node 通过 `child_process.spawn()` 调用 Python 模块。
Python 进程从标准输入读取 JSON 请求，再从标准输出返回 JSON 响应。
SQLite 负责保存归一化后的请求键和结果数据。

这种方式不依赖常驻 HTTP 服务，Windows 调试简单，Linux 部署也稳定。

## 数据量限制规则

系统会先根据实际返回行估算单行大小：

- `estimated_row_size = ceil(total_payload_bytes / row_count)`
- `max_rows = max(1, floor(max_bytes / estimated_row_size))`

默认 `max_bytes = 2000`。

当请求条数超过上限时：

1. 先按交易日分组。
2. 再对每天的数据按固定步长均匀采样。
3. 如果仍超限，则继续增大步长。
4. 直到结果小于等于上限。

不会只砍掉最前面或最后面的数据。

## A 股日内有效时段

对“单只股票 + 单日 + 分钟级”请求，当前只保留以下有效半小时节点：

- `09:30`
- `10:00`
- `10:30`
- `11:00`
- `11:30`
- `13:00`
- `13:30`
- `14:00`
- `14:30`
- `15:00`

午休和收盘后的无效时段不会进入返回结果。

## 已实现接口

- `stock_zh_a_spot`
- `stock_zh_a_hist`
- `stock_intraday_em`
- `stock_bid_ask_em`
- `futures_zh_spot`
- `futures_zh_hist`
- `match_main_contract`
- `futures_basis`
- `fund_meta`
- `fund_etf_market`
- `fund_open_info`
- `macro_china_all`
- `commodity_basis`
- `spot_sge`
- `bond_zh_hs_market`
- `bond_zh_hs_cov_market`
- `bond_cb_meta`
- `stock_board_industry`
- `stock_board_concept`

## 安装

### Node

```bash
npm install
```

### Python

Windows：

```bash
py -m pip install -r requirements.txt
```

Linux：

```bash
python3 -m pip install -r requirements.txt
```

建议 Python 版本为 `3.11+`。

## 使用示例

```js
import { createClient } from "./src/index.js";

const client = createClient();
const result = await client.stock_zh_a_hist({
  symbol: "000001",
  period: "30m",
  start_date: "2024-01-02 09:30:00",
  end_date: "2024-01-02 15:00:00",
});

console.log(result.rows);
```

## 作为 agent tool 使用

```js
import { createAkshareTool } from "./src/tool.js";

const tool = createAkshareTool();
const result = await tool.call("stock_zh_a_spot", { symbol: "000001" });
console.log(result.rows);
```

## 按类型注入方法

```js
import { createTypedClient } from "./src/index.js";

const typed = createTypedClient();

const stockMethods = typed.stock;
const macroMethods = typed.macro;
const bondMethods = typed.bond;

const macroResult = await macroMethods.macro_china_all();
console.log(macroResult.rows);
```

当前分组：

- `stock`
- `futures`
- `fund`
- `macro`
- `commodity`
- `bond`
- `board`

## Agent 工具注册表

```js
import { createAgentToolRegistry } from "./src/agent-tools.js";

const registry = createAgentToolRegistry();

const macroTools = registry.getGroup("macro");
const bondTool = registry.getTool("bond_cb_meta");
const result = await registry.invoke("macro_china_all");
```

## 环境变量

- `AKSHARE_NODE_PYTHON_BIN`：Python 可执行文件路径。Windows 默认 `py`，Linux 默认 `python3`。
- `AKSHARE_NODE_DB_PATH`：SQLite 数据库路径，默认 `./data/akshare_cache.sqlite`。
- `AKSHARE_NODE_MAX_BYTES`：单次响应最大字节数，默认 `2000`。
- `AKSHARE_NODE_TEST_MODE`：测试模式。开启后使用内置 stub 后端，不访问真实 `akshare`。

## Windows 开发、Linux 运行注意事项

- 当前项目先在 Windows 验证，再面向 Linux 运行。
- Node 侧路径使用 `path.join()` 构建。
- Python 侧路径使用 `pathlib.Path` 构建。
- SQLite 使用标准库 `sqlite3`，无额外平台依赖。
- Node 客户端运行时会自动选择 Windows 下的 `py` 或 Linux 下的 `python3`。
- 测试也会按平台自动选择 Python 启动命令，不依赖 Windows 专用别名。
- Linux 部署时只需要确保 `python3`、`pip` 和网络访问 `akshare` 所需数据源即可。
