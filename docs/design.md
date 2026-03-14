# 设计说明

## 对外接口形态

对外保留接近 `akshare` 的命名风格，但对明显重复的接口做了一层合并：

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
- `commodity_basis`
- `spot_sge`
- `bond_zh_hs_market`
- `bond_zh_hs_cov_market`
- `bond_cb_meta`
- `stock_board_industry`
- `stock_board_concept`

## 标准返回结构

每个 Node 接口都返回统一结构：

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

字段含义：

- `ok`：调用是否成功。
- `interface`：实际调用的接口名。
- `params`：归一化后的参数。
- `cache_hit`：是否命中 SQLite 缓存。
- `estimated_row_bytes`：估算的单行 UTF-8 字节数。
- `max_rows`：在当前大小限制下允许的最大行数。
- `requested_rows`：原始结果行数。
- `returned_rows`：降频后的返回行数。
- `sampling_step`：均匀采样步长，`1` 表示没有降频。
- `rows`：最终返回的数据行。

## 缓存设计

缓存键由以下信息组成：

- 接口名
- 归一化参数
- 当前 `max_bytes`

执行流程：

1. 先查 SQLite。
2. 如果缓存存在，直接读取缓存数据，再执行大小限制。
3. 如果缓存不存在，则调用 `akshare`。
4. 将原始归一化结果写入 SQLite。
5. 对结果执行大小限制后返回。

## 数据量限制设计

### 固定上限

- 默认单次响应最大字节数为 `2000`。
- 限制对象是 `rows` 的紧凑 JSON 序列化结果。

### 单行大小估算

流程如下：

1. 将返回结果归一化为 JSON 安全对象。
2. 使用紧凑 JSON 序列化整组数据。
3. 用总字节数除以总行数，向上取整，得到单行估算大小。

公式：

- `estimated_row_size = ceil(total_payload_bytes / row_count)`
- `max_rows = max(1, floor(max_bytes / estimated_row_size))`

### 均匀降频

如果结果超出上限，不允许简单截断。

处理过程：

1. 先按日期或时间字段识别所属交易日。
2. 每天单独保留顺序。
3. 对每天按固定步长采样，比如每隔 `2` 条取 `1` 条，再每隔 `3` 条取 `1` 条。
4. 所有天同步增加步长，直到总大小低于上限。

这样能尽量保留时间覆盖范围。

## A 股日内时段规则

对“单只股票 + 单日 + 分钟级历史数据”请求，先过滤到有效交易节点：

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

该规则用于避免把午休和闭市后的无效数据送回调用方。

## Node 与 Python 的职责划分

### Node 侧

- 暴露友好的 JS API
- 为每个接口补充参数和返回值注释
- 负责启动 Python 桥接进程
- 适配 agent tool 的统一调用方式

### Python 侧

- 调用真实 `akshare` 接口
- 把 DataFrame 转成标准 JSON 行
- 管理 SQLite 缓存
- 实现大小估算、均匀降频、交易时段过滤

## 测试策略

当前测试分两层：

- Node 单元测试：默认走 Python stub 后端，保证测试稳定。
- Python/真实数据冒烟测试：安装 `akshare` 后，直接访问真实接口验证桥接链路。

重点验证项：

- Node 客户端函数是否完整可用
- SQLite 是否命中缓存
- 2KB 限制是否生效
- 是否按均匀降频处理
- agent tool 调用层是否可用
