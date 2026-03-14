---
name: china-market-data
description: 获取中国股票、期货、基金、宏观经济、商品、债券、行业与板块数据。适用于需要先探活本地 `127.0.0.1:8888` 服务、查看可用接口、按接口名调用数据、或把较大 JSON 结果自动写入文件的场景。用户提到中国市场数据、本地行情服务、本地 AKShare HTTP 接口、127.0.0.1:8888、本地股票/期货/基金/宏观/债券/板块接口时应使用此 skill。
---

# 本地行情数据 API

## 概述

这个 skill 用来调用本机 `http://127.0.0.1:8888` 上运行的HTTP 服务。
它不直接操作 Python 包内部函数，而是通过统一的 HTTP API 获取数据，因此更适合做工具调用、脚本化查询、以及把较大的结果写入文件。

## 这个 skill 能做什么

### 1. 检查本地服务是否在线

- 调用 `GET /health`
- 判断 server 是否真的启动
- 确认监听是否仍是 `127.0.0.1:8888`

### 2. 查看有哪些可用接口

- 调用 `GET /tools`
- 拿到当前服务端支持的接口名
- 避免手写错接口名

### 3. 调用具体数据接口

- 调用 `POST /invoke`
- 传入接口名和参数
- 返回统一 JSON 结构

### 4. 自动处理大结果

- 使用 `scripts/call_local_api.py`
- 当返回 JSON 超过 5KB 时自动落盘
- 返回绝对文件路径，而不是把大段 JSON 直接塞进上下文

## 接口能做什么

### A 股

- `stock_zh_a_spot`
  用途：查询 A 股实时行情，适合看单只股票或当前市场快照。
- `stock_zh_a_hist`
  用途：查询 A 股历史行情，支持日线和分钟级数据。
- `stock_intraday_em`
  用途：查询单只股票分时成交明细。
- `stock_bid_ask_em`
  用途：查询单只股票盘口和买卖档位数据。

### 期货

- `futures_zh_spot`
  用途：查询期货实时行情。
- `futures_zh_hist`
  用途：查询期货历史行情。
- `match_main_contract`
  用途：根据交易所代码拿主力合约映射。
- `futures_basis`
  用途：查询期货基差、现期结构、现货联动信息。

### 基金

- `fund_meta`
  用途：查询基金基础资料和申购状态。
- `fund_etf_market`
  用途：查询 ETF 实时或历史行情。
- `fund_open_info`
  用途：查询开放式基金净值、走势和相关指标。

### 宏观经济

- `macro_china_all`
  用途：一次返回聚合后的中国宏观数据，适合做宏观快照或多指标联查。

### 商品与大宗商品

- `commodity_basis`
  用途：查询商品现货、期货、基差相关数据。
- `spot_sge`
  用途：查询上海金交所相关数据。

### 债券

- `bond_zh_hs_market`
  用途：查询沪深债券行情。
- `bond_zh_hs_cov_market`
  用途：查询沪深可转债行情。
- `bond_cb_meta`
  用途：查询可转债资料和概况。

### 行业与板块

- `stock_board_industry`
  用途：查询行业板块列表或历史行情。
- `stock_board_concept`
  用途：查询概念板块列表或历史行情。

## 工作流

1. 先检查服务是否在线。
2. 再查询 `/tools`，确认接口名。
3. 再调用具体接口。
4. 结果可能较大时，优先使用脚本而不是手写 HTTP。
5. 如果脚本返回 `stored_in_file=true`，直接使用返回的绝对文件路径。

## 常用例子

### 例 1：检查服务是否启动

Windows：

```powershell
py scripts/call_local_api.py --health-check
```

Linux：

```bash
python3 scripts/call_local_api.py --health-check
```

### 例 2：查看当前有哪些接口

Windows：

```powershell
py scripts/call_local_api.py --list-tools
```

Linux：

```bash
python3 scripts/call_local_api.py --list-tools
```

### 例 3：查平安银行实时行情

Windows：

```powershell
py scripts/call_local_api.py --interface stock_zh_a_spot --params '{"symbol":"000001"}'
```

Linux：

```bash
python3 scripts/call_local_api.py --interface stock_zh_a_spot --params '{"symbol":"000001"}'
```

### 例 4：查某只股票历史行情

```bash
python3 scripts/call_local_api.py \
  --interface stock_zh_a_hist \
  --params '{"symbol":"000001","period":"daily","start_date":"20240101","end_date":"20240131"}'
```

### 例 5：查宏观经济聚合数据

```bash
python3 scripts/call_local_api.py \
  --interface macro_china_all \
  --params '{"datasets":["macro_china_cpi","macro_china_lpr"]}'
```

### 例 6：查债券或可转债

```bash
python3 scripts/call_local_api.py \
  --interface bond_cb_meta \
  --params '{"mode":"summary"}'
```

### 例 7：结果很大时写入文件

```bash
python3 scripts/call_local_api.py \
  --interface macro_china_all \
  --params '{}' \
  --output-dir ./outputs
```

如果结果超过 5KB，脚本会返回：

- `stored_in_file: true`
- `file_path: /绝对/路径/xxx.json`

## 使用约束

- 默认假设服务只监听 `127.0.0.1:8888`。
- 不要先猜接口名，优先查 `/tools`。
- 大结果优先走 `scripts/call_local_api.py`。
- 当用户只是想看“某类数据能做什么”，优先解释接口用途，不要先堆原始 JSON。
- 如果本地服务不可用，要先明确报错，再考虑建议启动服务或排查。

## Win/Linux 兼容性

- 脚本只依赖 Python 标准库。
- 路径处理使用 `pathlib`，不写死 Windows 或 Linux 分隔符。
- Windows 示例使用 `py`，Linux 示例使用 `python3`。
- 结果文件路径返回绝对路径，便于两端环境直接定位。
- 当前 skill 目录名可以使用中文路径，但如果后续要接入更多自动化工具、CI 或跨机器脚本，建议把目录名改成 ASCII，例如 `china-market-data`，这样兼容性更稳。

## 资源

- 使用 [scripts/call_local_api.py](scripts/call_local_api.py) 做跨平台调用。
- 使用 [references/api.md](references/api.md) 查看 HTTP 接口结构、字段说明和更多例子。
