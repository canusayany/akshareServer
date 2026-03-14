# 本地 AKShare HTTP API 参考

## 基础地址

- `http://127.0.0.1:8888`

## HTTP 接口

### `GET /health`

作用：

- 检查服务是否在线
- 确认监听地址和端口

示例返回：

```json
{
  "ok": true,
  "host": "127.0.0.1",
  "port": 8888
}
```

### `GET /tools`

作用：

- 返回当前 server 支持的接口名列表
- 适合先探测能力，再决定调哪个接口

示例返回：

```json
{
  "ok": true,
  "tools": [
    "stock_zh_a_spot",
    "stock_zh_a_hist",
    "macro_china_all"
  ]
}
```

### `POST /invoke`

作用：

- 按接口名调用具体数据接口
- 所有业务数据都从这里走

请求体：

```json
{
  "interface": "stock_zh_a_spot",
  "params": {
    "symbol": "000001"
  },
  "max_bytes": 2000,
  "db_path": "可选，自定义 sqlite 路径"
}
```

标准返回：

```json
{
  "ok": true,
  "interface": "stock_zh_a_spot",
  "params": {
    "symbol": "000001"
  },
  "cache_hit": false,
  "estimated_row_bytes": 120,
  "max_rows": 16,
  "requested_rows": 2,
  "returned_rows": 2,
  "sampling_step": 1,
  "rows": []
}
```

## 常见接口与用途

### 股票类

- `stock_zh_a_spot`：A 股实时行情
- `stock_zh_a_hist`：A 股历史行情
- `stock_intraday_em`：A 股分时成交
- `stock_bid_ask_em`：A 股盘口

### 期货类

- `futures_zh_spot`：期货实时行情
- `futures_zh_hist`：期货历史行情
- `match_main_contract`：主力合约映射
- `futures_basis`：基差和现期结构

### 基金类

- `fund_meta`：基金基础信息
- `fund_etf_market`：ETF 行情
- `fund_open_info`：开放式基金净值与指标

### 宏观类

- `macro_china_all`：聚合后的中国宏观经济数据

### 商品类

- `commodity_basis`：商品/大宗商品现货与基差
- `spot_sge`：上海金交所数据

### 债券类

- `bond_zh_hs_market`：沪深债券行情
- `bond_zh_hs_cov_market`：沪深可转债行情
- `bond_cb_meta`：可转债资料

### 板块类

- `stock_board_industry`：行业板块
- `stock_board_concept`：概念板块

## 脚本调用

### 跨平台脚本

- `scripts/call_local_api.py`

用途：

- 调 `--health-check`
- 调 `--list-tools`
- 调任意 `--interface`
- 当结果超过 5KB 时自动写文件

### 例子：健康检查

```bash
python3 scripts/call_local_api.py --health-check
```

### 例子：列接口

```bash
python3 scripts/call_local_api.py --list-tools
```

### 例子：查实时股票

```bash
python3 scripts/call_local_api.py \
  --interface stock_zh_a_spot \
  --params '{"symbol":"000001"}'
```

### 例子：查宏观数据并写文件

```bash
python3 scripts/call_local_api.py \
  --interface macro_china_all \
  --params '{}' \
  --output-dir ./outputs
```

如果结果过大，脚本返回类似：

```json
{
  "ok": true,
  "stored_in_file": true,
  "file_path": "/abs/path/result.json",
  "bytes": 8241,
  "interface": "macro_china_all"
}
```
