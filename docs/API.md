# AKShare Node HTTP API 接口文档

## 概述

服务器地址：`http://127.0.0.1:8888`

- `GET /health`：健康检查
- `GET /tools`：可用接口列表
- `POST /invoke`：调用数据接口

## POST /invoke 请求体

```json
{ "interface": "接口名", "params": { ... }, "verify_ssl": false }
```

## 返回值通用结构（成功时）

```json
{
  "ok": true,
  "interface": "接口名",
  "params": {},
  "cache_hit": false,
  "estimated_row_bytes": 100,
  "max_rows": 20,
  "requested_rows": 100,
  "returned_rows": 20,
  "sampling_step": 5,
  "rows": [
    {}
  ]
}
```

## 各接口说明

### stock_zh_a_spot

- **说明**：A 股实时行情列表
- **测试状态**：✓ 测试通过
- **返回字段示例**：code, name, price, 涨跌额, pct_chg, 买入, 卖出, 昨收, 今开, 最高

**测试请求体示例**：
```json
{
  "interface": "stock_zh_a_spot",
  "params": {},
  "verify_ssl": false
}
```

**实际返回元信息**：
```json
{
  "ok": true,
  "cache_hit": true,
  "requested_rows": 5489,
  "returned_rows": 7,
  "sampling_step": 915
}
```

**实际调用返回数据示例**：
```json
[
  {
    "code": "bj920000",
    "name": "安徽凤凰",
    "price": 16.76,
    "涨跌额": -0.3,
    "pct_chg": -1.758,
    "买入": 16.73,
    "卖出": 16.76,
    "昨收": 17.06,
    "今开": 17.06,
    "最高": 17.35,
    "最低": 16.7,
    "volume": 385957,
    "成交额": 6507513,
    "时间戳": "11:34:57"
  },
  {
    "code": "sh600803",
    "name": "新奥股份",
    "price": 21.89,
    "涨跌额": -0.57,
    "pct_chg": -2.538,
    "买入": 21.89,
    "卖出": 21.9,
    "昨收": 22.46,
    "今开": 22.45,
    "最高": 22.46,
    "最低": 21.86,
    "volume": 7056900,
    "成交额": 156360884,
    "时间戳": "11:30:00"
  },
  {
    "code": "sh603898",
    "name": "好莱客",
    "price": 14.53,
    "涨跌额": -0.21,
    "pct_chg": -1.425,
    "买入": 14.53,
    "卖出": 14.55,
    "昨收": 14.74,
    "今开": 14.65,
    "最高": 14.8,
    "最低": 14.47,
    "volume": 1969700,
    "成交额": 28744328,
    "时间戳": "11:30:00"
  }
]
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| symbol | 可选，股票代码，如 000001 |

**测试用最小参数**：

```json
{}
```

### stock_zh_a_hist

- **说明**：A 股历史 K 线
- **测试状态**：✗ 测试失败: baostock not installed

**测试请求体示例**：
```json
{
  "interface": "stock_zh_a_hist",
  "params": {
    "symbol": "000001",
    "period": "daily",
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  },
  "verify_ssl": false
}
```

**实际调用返回数据示例**：
```json
{
  "error": {
    "type": "ValueError",
    "message": "baostock not installed",
    "hint": null
  }
}
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| symbol | 必填，股票代码 |
| period | daily|weekly|monthly|1m|5m|15m|30m|60m |
| start_date | 开始日期 |
| end_date | 结束日期 |
| adjust | 可选，复权方式 |

**测试用最小参数**：

```json
{
  "symbol": "000001",
  "period": "daily",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31"
}
```

### stock_intraday_em

- **说明**：分时行情
- **测试状态**：✓ 测试通过
- **返回字段示例**：时间, 成交价, 手数, 买卖盘性质

**测试请求体示例**：
```json
{
  "interface": "stock_intraday_em",
  "params": {
    "symbol": "000001"
  },
  "verify_ssl": false
}
```

**实际返回元信息**：
```json
{
  "ok": true,
  "cache_hit": false,
  "requested_rows": 2125,
  "returned_rows": 25,
  "sampling_step": 89
}
```

**实际调用返回数据示例**：
```json
[
  {
    "时间": "09:15:00",
    "成交价": 11.04,
    "手数": 69,
    "买卖盘性质": "中性盘"
  },
  {
    "时间": "09:31:33",
    "成交价": 11.02,
    "手数": 289,
    "买卖盘性质": "卖盘"
  },
  {
    "时间": "09:36:00",
    "成交价": 11.02,
    "手数": 122,
    "买卖盘性质": "买盘"
  }
]
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| symbol | 必填，股票代码 |

**测试用最小参数**：

```json
{
  "symbol": "000001"
}
```

### stock_bid_ask_em

- **说明**：买卖盘口
- **测试状态**：✓ 测试通过
- **返回字段示例**：item, value

**测试请求体示例**：
```json
{
  "interface": "stock_bid_ask_em",
  "params": {
    "symbol": "000001"
  },
  "verify_ssl": false
}
```

**实际返回元信息**：
```json
{
  "ok": true,
  "cache_hit": true,
  "requested_rows": 36,
  "returned_rows": 36,
  "sampling_step": 1
}
```

**实际调用返回数据示例**：
```json
[
  {
    "item": "sell_5",
    "value": 10.99
  },
  {
    "item": "sell_5_vol",
    "value": 430700
  },
  {
    "item": "sell_4",
    "value": 10.98
  }
]
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| symbol | 必填，股票代码 |

**测试用最小参数**：

```json
{
  "symbol": "000001"
}
```

### futures_zh_spot

- **说明**：期货实时行情
- **测试状态**：✓ 测试通过
- **返回字段示例**：symbol, exchange, name, price, settlement, presettlement, open, high, low, close

**测试请求体示例**：
```json
{
  "interface": "futures_zh_spot",
  "params": {
    "symbol": "PTA"
  },
  "verify_ssl": false
}
```

**实际返回元信息**：
```json
{
  "ok": true,
  "cache_hit": false,
  "requested_rows": 13,
  "returned_rows": 5,
  "sampling_step": 3
}
```

**实际调用返回数据示例**：
```json
[
  {
    "symbol": "TA0",
    "exchange": "czce",
    "name": "PTA连续",
    "price": 6782,
    "settlement": 6928,
    "presettlement": 6842,
    "open": 6868,
    "high": 7060,
    "low": 6744,
    "close": 0,
    "bidprice1": 6778,
    "askprice1": 6782,
    "bidvol1": 32,
    "askvol1": 9,
    "volume": 1422690,
    "position": 1138271,
    "ticktime": "11:30:00",
    "tradedate": "2026-03-18",
    "preclose": 6918,
    "changepercent": -0.0087694,
    "bid": 0,
    "ask": 0,
    "prevsettlement": 6842
  },
  {
    "symbol": "TA2607",
    "exchange": "czce",
    "name": "PTA2607",
    "price": 6690,
    "settlement": 6826,
    "presettlement": 6738,
    "open": 6752,
    "high": 6950,
    "low": 6654,
    "close": 0,
    "bidprice1": 6688,
    "askprice1": 6700,
    "bidvol1": 1,
    "askvol1": 1,
    "volume": 60874,
    "position": 102517,
    "ticktime": "11:30:00",
    "tradedate": "2026-03-18",
    "preclose": 6810,
    "changepercent": -0.0071238,
    "bid": 0,
    "ask": 0,
    "prevsettlement": 6738
  },
  {
    "symbol": "TA2608",
    "exchange": "czce",
    "name": "PTA2608",
    "price": 6634,
    "settlement": 6760,
    "presettlement": 6672,
    "open": 6686,
    "high": 6880,
    "low": 6594,
    "close": 0,
    "bidprice1": 6628,
    "askprice1": 6636,
    "bidvol1": 5,
    "askvol1": 5,
    "volume": 41158,
    "position": 35217,
    "ticktime": "11:29:58",
    "tradedate": "2026-03-18",
    "preclose": 6746,
    "changepercent": -0.0056954,
    "bid": 0,
    "ask": 0,
    "prevsettlement": 6672
  }
]
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| symbol | 可选，期货合约代码 |
| market | 可选，FF|SF 等 |
| adjust | 可选 |

**测试用最小参数**：

```json
{
  "symbol": "PTA"
}
```

### futures_zh_hist

- **说明**：期货历史 K 线
- **测试状态**：✓ 测试通过
- **返回字段示例**：index, symbol, date, open, high, low, close, volume, open_interest, turnover

**测试请求体示例**：
```json
{
  "interface": "futures_zh_hist",
  "params": {
    "symbol": "RB2505",
    "start_date": "2025-03-05",
    "end_date": "2025-03-05"
  },
  "verify_ssl": false
}
```

**实际返回元信息**：
```json
{
  "ok": true,
  "cache_hit": false,
  "requested_rows": 1,
  "returned_rows": 1,
  "sampling_step": 1
}
```

**实际调用返回数据示例**：
```json
[
  {
    "index": 118,
    "symbol": "RB2505",
    "date": "20250305",
    "open": 3279,
    "high": 3288,
    "low": 3252,
    "close": 3259,
    "volume": 1789010,
    "open_interest": 2047118,
    "turnover": 5847403.149,
    "settle": 3268,
    "pre_settle": 3282,
    "variety": "RB"
  }
]
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| symbol | 必填，期货合约 |
| period | daily|1m|5m|15m|30m|60m |
| start_date | 可选，开始日期 |
| end_date | 可选，结束日期 |
| source | 可选，em 用东方财富 |

**测试用最小参数**：

```json
{
  "symbol": "RB2505",
  "start_date": "2025-03-05",
  "end_date": "2025-03-05"
}
```

### match_main_contract

- **说明**：主力合约列表
- **测试状态**：✓ 测试通过
- **返回字段示例**：symbol, contracts

**测试请求体示例**：
```json
{
  "interface": "match_main_contract",
  "params": {},
  "verify_ssl": false
}
```

**实际返回元信息**：
```json
{
  "ok": true,
  "cache_hit": false,
  "requested_rows": 1,
  "returned_rows": 1,
  "sampling_step": 1
}
```

**实际调用返回数据示例**：
```json
[
  {
    "symbol": "cffex",
    "contracts": "IF2606,TF2606,IH2606,IC2606,TS2606,IM2606"
  }
]
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| symbol | 可选，交易所如 cffex|shfe|dce|czce |
| exchange | 同上 |

**测试用最小参数**：

```json
{}
```

### futures_basis

- **说明**：期货基差/现货价格
- **测试状态**：✗ 测试失败: The operation was aborted due to timeout

**测试请求体示例**：
```json
{
  "interface": "futures_basis",
  "params": {
    "date": "2024-01-15"
  },
  "verify_ssl": false
}
```

**实际调用返回数据示例**：
```json
{
  "error": "The operation was aborted due to timeout"
}
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| mode | 可选，sys 用 futures_spot_sys，否则用 futures_spot_price |
| symbol | mode=sys 时必填，如 RU |
| date | 可选，交易日 YYYY-MM-DD，空则当天 |

**测试用最小参数**：

```json
{
  "date": "2024-01-15"
}
```

### fund_meta

- **说明**：基金列表/申购信息
- **测试状态**：✓ 测试通过
- **返回字段示例**：基金代码, 拼音缩写, 基金简称, 基金类型, 拼音全称

**测试请求体示例**：
```json
{
  "interface": "fund_meta",
  "params": {},
  "verify_ssl": false
}
```

**实际返回元信息**：
```json
{
  "ok": true,
  "cache_hit": false,
  "requested_rows": 26237,
  "returned_rows": 11,
  "sampling_step": 2705
}
```

**实际调用返回数据示例**：
```json
[
  {
    "基金代码": "000001",
    "拼音缩写": "HXCZHH",
    "基金简称": "华夏成长混合",
    "基金类型": "混合型-灵活",
    "拼音全称": "HUAXIACHENGZHANGHUNHE"
  },
  {
    "基金代码": "004020",
    "拼音缩写": "GFJXCZ",
    "基金简称": "广发景祥纯债",
    "基金类型": "债券型-长债",
    "拼音全称": "GUANGFAJINGXIANGCHUNZHAI"
  },
  {
    "基金代码": "007612",
    "拼音缩写": "HAYHCZZQC",
    "基金简称": "汇安裕和纯债债券C",
    "基金类型": "债券型-长债",
    "拼音全称": "HUIANYUHECHUNZHAIZHAIQUANC"
  }
]
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| mode | 可选，purchase 返回申购信息 |

**测试用最小参数**：

```json
{}
```

### fund_etf_market

- **说明**：ETF 行情/历史
- **测试状态**：✓ 测试通过
- **返回字段示例**：序号, 基金代码, 基金名称, 当前-单位净值, 当前-累计净值, 前一日-单位净值, 前一日-累计净值, 增长值, 增长率, 赎回状态

**测试请求体示例**：
```json
{
  "interface": "fund_etf_market",
  "params": {},
  "verify_ssl": false
}
```

**实际返回元信息**：
```json
{
  "ok": true,
  "cache_hit": false,
  "requested_rows": 1490,
  "returned_rows": 4,
  "sampling_step": 497
}
```

**实际调用返回数据示例**：
```json
[
  {
    "序号": 1,
    "基金代码": "513930",
    "基金名称": "华泰柏瑞恒生生物科技ETF",
    "当前-单位净值": 1.001,
    "当前-累计净值": 1.001,
    "前一日-单位净值": null,
    "前一日-累计净值": null,
    "增长值": 0.0234,
    "增长率": 2.39,
    "赎回状态": "开放",
    "申购状态": "开放",
    "最新-交易日": "2026-03-17",
    "最新-单位净值": 1.001,
    "最新-累计净值": 1.001,
    "基金类型": "股票型",
    "查询日期": "2026-03-17"
  },
  {
    "序号": 498,
    "基金代码": "517100",
    "基金名称": "富国中证沪港深500ETF",
    "当前-单位净值": 1.0296,
    "当前-累计净值": 1.0296,
    "前一日-单位净值": 1.0353,
    "前一日-累计净值": 1.0353,
    "增长值": -0.0057,
    "增长率": -0.55,
    "赎回状态": "开放",
    "申购状态": "开放",
    "最新-交易日": "2026-03-17",
    "最新-单位净值": 1.0296,
    "最新-累计净值": 1.0296,
    "基金类型": "股票型",
    "查询日期": "2026-03-17"
  },
  {
    "序号": 995,
    "基金代码": "589850",
    "基金名称": "科创50ETF东财",
    "当前-单位净值": 1.2955,
    "当前-累计净值": 1.2955,
    "前一日-单位净值": 1.3249,
    "前一日-累计净值": 1.3249,
    "增长值": -0.0294,
    "增长率": -2.22,
    "赎回状态": "开放",
    "申购状态": "开放",
    "最新-交易日": "2026-03-17",
    "最新-单位净值": 1.2955,
    "最新-累计净值": 1.2955,
    "基金类型": "股票型",
    "查询日期": "2026-03-17"
  }
]
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| mode | 可选，hist 返回历史需 symbol/start_date/end_date |
| symbol | mode=hist 时必填 |
| period | daily/weekly/monthly |
| start_date | mode=hist 时 |
| end_date | mode=hist 时 |
| adjust | 可选 |

**测试用最小参数**：

```json
{}
```

### fund_open_info

- **说明**：开放式基金信息
- **测试状态**：✗ 测试失败: The operation was aborted due to timeout

**测试请求体示例**：
```json
{
  "interface": "fund_open_info",
  "params": {
    "symbol": "110011"
  },
  "verify_ssl": false
}
```

**实际调用返回数据示例**：
```json
{
  "error": "The operation was aborted due to timeout"
}
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| symbol | 必填，基金代码 |
| indicator | 可选，如 单位净值走势 |

**测试用最小参数**：

```json
{
  "symbol": "110011"
}
```

### macro_china_all

- **说明**：宏观数据汇总
- **测试状态**：✓ 测试通过
- **返回字段示例**：dataset, 季度, 国内生产总值-绝对值, 国内生产总值-同比增长, 第一产业-绝对值, 第一产业-同比增长, 第二产业-绝对值, 第二产业-同比增长, 第三产业-绝对值, 第三产业-同比增长

**测试请求体示例**：
```json
{
  "interface": "macro_china_all",
  "params": {},
  "verify_ssl": false
}
```

**实际返回元信息**：
```json
{
  "ok": true,
  "cache_hit": true,
  "requested_rows": 2981,
  "returned_rows": 11,
  "sampling_step": 319
}
```

**实际调用返回数据示例**：
```json
[
  {
    "dataset": "macro_china_gdp",
    "季度": "2025年第1-4季度",
    "国内生产总值-绝对值": 1401879.2,
    "国内生产总值-同比增长": 5,
    "第一产业-绝对值": 93346.8,
    "第一产业-同比增长": 3.9,
    "第二产业-绝对值": 499653,
    "第二产业-同比增长": 4.5,
    "第三产业-绝对值": 808879.3,
    "第三产业-同比增长": 5.4
  },
  {
    "dataset": "macro_china_ppi",
    "月份": "2024年05月份",
    "当月": 98.6,
    "当月同比增长": -1.4,
    "累计": 97.6
  },
  {
    "dataset": "macro_china_pmi",
    "月份": "2017年12月份",
    "制造业-指数": 51.6,
    "制造业-同比增长": 0.38910506,
    "非制造业-指数": 55,
    "非制造业-同比增长": 0.91743119
  }
]
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| datasets | 可选，gdp,cpi,ppi,pmi,lpr,money_supply,credit,fx_gold 或 macro_china_* |

**测试用最小参数**：

```json
{}
```

### commodity_basis

- **说明**：商品基差/现货价
- **测试状态**：✓ 测试通过
- **返回字段示例**：date, symbol, spot_price, near_contract, near_contract_price, dominant_contract, dominant_contract_price, near_month, dominant_month, near_basis

**测试请求体示例**：
```json
{
  "interface": "commodity_basis",
  "params": {
    "date": "2024-03-15"
  },
  "verify_ssl": false
}
```

**实际返回元信息**：
```json
{
  "ok": true,
  "cache_hit": false,
  "requested_rows": 52,
  "returned_rows": 5,
  "sampling_step": 13
}
```

**实际调用返回数据示例**：
```json
[
  {
    "date": "20240315",
    "symbol": "C",
    "spot_price": 2350,
    "near_contract": "c2405",
    "near_contract_price": 2451,
    "dominant_contract": "c2405",
    "dominant_contract_price": 2451,
    "near_month": "2405",
    "dominant_month": "2405",
    "near_basis": 101,
    "dom_basis": 101,
    "near_basis_rate": 0.04297872340425535,
    "dom_basis_rate": 0.04297872340425535
  },
  {
    "date": "20240315",
    "symbol": "EB",
    "spot_price": 9430,
    "near_contract": "eb2403",
    "near_contract_price": 9517,
    "dominant_contract": "eb2405",
    "dominant_contract_price": 9400,
    "near_month": "2403",
    "dominant_month": "2405",
    "near_basis": 87,
    "dom_basis": -30,
    "near_basis_rate": 0.009225874867444306,
    "dom_basis_rate": -0.0031813361611876534
  },
  {
    "date": "20240315",
    "symbol": "SM",
    "spot_price": 5906.67,
    "near_contract": "SM404",
    "near_contract_price": 6092,
    "dominant_contract": "SM405",
    "dominant_contract_price": 6122,
    "near_month": "2404",
    "dominant_month": "2405",
    "near_basis": 185.32999999999993,
    "dom_basis": 215.32999999999993,
    "near_basis_rate": 0.03137639312844631,
    "dom_basis_rate": 0.03645539703420031
  }
]
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| mode | 可选，futures_spot_price|futures_spot_sys |
| symbol | 可选，品种如 铜/CU/RU |
| date | 可选，交易日 |

**测试用最小参数**：

```json
{
  "date": "2024-03-15"
}
```

### spot_sge

- **说明**：上海黄金交易所现货行情
- **测试状态**：✓ 测试通过
- **返回字段示例**：品种, 时间, 现价, 更新时间

**测试请求体示例**：
```json
{
  "interface": "spot_sge",
  "params": {},
  "verify_ssl": false
}
```

**实际返回元信息**：
```json
{
  "ok": true,
  "cache_hit": false,
  "requested_rows": 358,
  "returned_rows": 19,
  "sampling_step": 20
}
```

**实际调用返回数据示例**：
```json
[
  {
    "品种": "Au99.99",
    "时间": "00:00:00",
    "现价": 1111,
    "更新时间": "2026年03月18日 12:26:55"
  },
  {
    "品种": "Au99.99",
    "时间": "00:20:00",
    "现价": 1111,
    "更新时间": "2026年03月18日 12:26:55"
  },
  {
    "品种": "Au99.99",
    "时间": "00:40:00",
    "现价": 1111,
    "更新时间": "2026年03月18日 12:26:55"
  }
]
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| mode | 可选，hist 返回历史 |
| symbol | 可选，Au99.99/白银等 |

**测试用最小参数**：

```json
{}
```

### bond_zh_hs_market

- **说明**：沪深债券行情
- **测试状态**：✓ 测试通过
- **返回字段示例**：报价机构, 债券简称, 买入净价, 卖出净价, 买入收益率, 卖出收益率

**测试请求体示例**：
```json
{
  "interface": "bond_zh_hs_market",
  "params": {},
  "verify_ssl": false
}
```

**实际返回元信息**：
```json
{
  "ok": true,
  "cache_hit": false,
  "requested_rows": 15,
  "returned_rows": 8,
  "sampling_step": 2
}
```

**实际调用返回数据示例**：
```json
[
  {
    "报价机构": "中金公司",
    "债券简称": "19附息国债15",
    "买入净价": 106.15,
    "卖出净价": 107.27,
    "买入收益率": 1.405,
    "卖出收益率": 1.105
  },
  {
    "报价机构": "上海银行",
    "债券简称": "19附息国债15",
    "买入净价": 106.66,
    "卖出净价": 106.76,
    "买入收益率": 1.2675,
    "卖出收益率": 1.2425
  },
  {
    "报价机构": "平安银行",
    "债券简称": "19附息国债15",
    "买入净价": 106.68,
    "卖出净价": 106.74,
    "买入收益率": 1.2625,
    "卖出收益率": 1.2475
  }
]
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| mode | 可选，hist 需 symbol |
| symbol | mode=hist 时必填 |

**测试用最小参数**：

```json
{}
```

### bond_zh_hs_cov_market

- **说明**：可转债行情
- **测试状态**：✓ 测试通过
- **返回字段示例**：symbol, name, trade, pricechange, changepercent, buy, sell, settlement, open, high

**测试请求体示例**：
```json
{
  "interface": "bond_zh_hs_cov_market",
  "params": {},
  "verify_ssl": false
}
```

**实际返回元信息**：
```json
{
  "ok": true,
  "cache_hit": false,
  "requested_rows": 379,
  "returned_rows": 7,
  "sampling_step": 63
}
```

**实际调用返回数据示例**：
```json
[
  {
    "symbol": "bj810011",
    "name": "优机定转",
    "trade": "0.000",
    "pricechange": "0.000",
    "changepercent": "0.000",
    "buy": "0.000",
    "sell": "0.000",
    "settlement": "100.500",
    "open": "0.000",
    "high": "0.000",
    "low": "0.000",
    "volume": 0,
    "amount": 0,
    "code": "810011",
    "ticktime": "11:34:57"
  },
  {
    "symbol": "sh113056",
    "name": "重银转债",
    "trade": "128.664",
    "pricechange": "-0.592",
    "changepercent": "-0.458",
    "buy": "128.648",
    "sell": "128.661",
    "settlement": "129.256",
    "open": "129.256",
    "high": "129.460",
    "low": "128.524",
    "volume": 1249360,
    "amount": 161015596,
    "code": "113056",
    "ticktime": "11:30:00"
  },
  {
    "symbol": "sh113688",
    "name": "国检转债",
    "trade": "136.521",
    "pricechange": "0.837",
    "changepercent": "0.617",
    "buy": "136.507",
    "sell": "136.610",
    "settlement": "135.684",
    "open": "136.078",
    "high": "137.108",
    "low": "135.256",
    "volume": 101140,
    "amount": 13781670,
    "code": "113688",
    "ticktime": "11:30:00"
  }
]
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| mode | 可选，hist 需 symbol |
| symbol | mode=hist 时必填 |

**测试用最小参数**：

```json
{}
```

### bond_cb_meta

- **说明**：可转债概要/详情
- **测试状态**：✓ 测试通过
- **返回字段示例**：item, value

**测试请求体示例**：
```json
{
  "interface": "bond_cb_meta",
  "params": {
    "mode": "summary"
  },
  "verify_ssl": false
}
```

**实际返回元信息**：
```json
{
  "ok": true,
  "cache_hit": false,
  "requested_rows": 15,
  "returned_rows": 15,
  "sampling_step": 1
}
```

**实际调用返回数据示例**：
```json
[
  {
    "item": "债券类型",
    "value": "普通企业债"
  },
  {
    "item": "计息方式",
    "value": "固定利率"
  },
  {
    "item": "付息方式",
    "value": "周期性付息"
  }
]
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| mode | summary 汇总|非 summary 需 symbol |
| symbol | mode 非 summary 时必填 |

**测试用最小参数**：

```json
{
  "mode": "summary"
}
```

### stock_board_industry

- **说明**：行业板块列表/历史
- **测试状态**：✓ 测试通过
- **返回字段示例**：name, code

**测试请求体示例**：
```json
{
  "interface": "stock_board_industry",
  "params": {},
  "verify_ssl": false
}
```

**实际返回元信息**：
```json
{
  "ok": true,
  "cache_hit": false,
  "requested_rows": 90,
  "returned_rows": 46,
  "sampling_step": 2
}
```

**实际调用返回数据示例**：
```json
[
  {
    "name": "半导体",
    "code": "881121"
  },
  {
    "name": "白色家电",
    "code": "881131"
  },
  {
    "name": "包装印刷",
    "code": "881138"
  }
]
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| mode | 可选，hist 需 symbol/start_date/end_date |
| symbol | mode=hist 时板块名称 |
| period | daily/weekly/monthly |
| start_date | mode=hist 时 |
| end_date | mode=hist 时 |
| adjust | 可选 |

**测试用最小参数**：

```json
{}
```

### stock_board_concept

- **说明**：概念板块列表/历史
- **测试状态**：✗ 测试失败: The operation was aborted due to timeout

**测试请求体示例**：
```json
{
  "interface": "stock_board_concept",
  "params": {},
  "verify_ssl": false
}
```

**实际调用返回数据示例**：
```json
{
  "error": "The operation was aborted due to timeout"
}
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| mode | 可选，hist 需 symbol/start_date/end_date |
| symbol | mode=hist 时概念名称 |
| period | daily/weekly/monthly |
| start_date | mode=hist 时 |
| end_date | mode=hist 时 |
| adjust | 可选 |

**测试用最小参数**：

```json
{}
```

### stock_index_zh_hist

- **说明**：股票指数历史日线
- **测试状态**：✗ 测试失败: The operation was aborted due to timeout
- **测试场景**：长区间样例：40 天 000001 指数日线

**测试请求体示例**：
```json
{
  "interface": "stock_index_zh_hist",
  "params": {
    "symbol": "000001",
    "start_date": "2024-01-10",
    "end_date": "2024-02-18"
  },
  "verify_ssl": false
}
```

**实际调用返回数据示例**：
```json
{
  "error": "The operation was aborted due to timeout"
}
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| symbol | 必填，指数代码如 000001(上证)、399001(深证)、399006(创业板) |
| start_date | 开始日期 |
| end_date | 结束日期 |

**测试用最小参数**：

```json
{
  "symbol": "000001",
  "start_date": "2024-01-10",
  "end_date": "2024-02-18"
}
```

### stock_financial_abstract

- **说明**：财务摘要指标
- **测试状态**：✗ 测试失败: The operation was aborted due to timeout

**测试请求体示例**：
```json
{
  "interface": "stock_financial_abstract",
  "params": {
    "symbol": "000001"
  },
  "verify_ssl": false
}
```

**实际调用返回数据示例**：
```json
{
  "error": "The operation was aborted due to timeout"
}
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| symbol | 必填，股票代码 |

**测试用最小参数**：

```json
{
  "symbol": "000001"
}
```

### stock_yjbb_em

- **说明**：业绩快报
- **测试状态**：✓ 测试通过
- **返回字段示例**：序号, 股票代码, 股票简称, 每股收益, 营业总收入-营业总收入, 营业总收入-同比增长, 营业总收入-季度环比增长, 净利润-净利润, 净利润-同比增长, 净利润-季度环比增长

**测试请求体示例**：
```json
{
  "interface": "stock_yjbb_em",
  "params": {
    "date": "20241231"
  },
  "verify_ssl": false
}
```

**实际返回元信息**：
```json
{
  "ok": true,
  "cache_hit": true,
  "requested_rows": 11673,
  "returned_rows": 3,
  "sampling_step": 5836
}
```

**实际调用返回数据示例**：
```json
[
  {
    "序号": 1,
    "股票代码": "688678",
    "股票简称": "福立旺",
    "每股收益": 0.26,
    "营业总收入-营业总收入": 1285181367.32,
    "营业总收入-同比增长": 29.6025414663,
    "营业总收入-季度环比增长": 11.3321,
    "净利润-净利润": 54526001.94,
    "净利润-同比增长": -38.38,
    "净利润-季度环比增长": -154.935,
    "每股净资产": 6.189578714321,
    "净资产收益率": 3.53,
    "每股经营现金流量": 0.222009549942,
    "销售毛利率": 24.4123108277,
    "所处行业": "消费电子",
    "最新公告日期": "2026-03-18"
  },
  {
    "序号": 5837,
    "股票代码": "002886",
    "股票简称": "沃特股份",
    "每股收益": 0.14,
    "营业总收入-营业总收入": 1896867994.9,
    "营业总收入-同比增长": 23.452425925,
    "营业总收入-季度环比增长": 26.9059,
    "净利润-净利润": 36596540.43,
    "净利润-同比增长": 520.69,
    "净利润-季度环比增长": 12.8196,
    "每股净资产": 6.751950485435,
    "净资产收益率": 2.08,
    "每股经营现金流量": 0.356305147843,
    "销售毛利率": 17.8124878741,
    "所处行业": "塑料",
    "最新公告日期": "2025-04-25"
  },
  {
    "序号": 11673,
    "股票代码": "838284",
    "股票简称": "时代华商",
    "每股收益": 0.39,
    "营业总收入-营业总收入": 58184183.19,
    "营业总收入-同比增长": -46.8218275865,
    "营业总收入-季度环比增长": null,
    "净利润-净利润": 12933228.12,
    "净利润-同比增长": 3.02,
    "净利润-季度环比增长": null,
    "每股净资产": 1.96,
    "净资产收益率": 20.53,
    "每股经营现金流量": -0.198298748666,
    "销售毛利率": 56.4682369996,
    "所处行业": null,
    "最新公告日期": "2025-01-24"
  }
]
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| date | 必填，报告期 YYYYMMDD，如 20241231/20240930 |

**测试用最小参数**：

```json
{
  "date": "20241231"
}
```

### stock_yjyg_em

- **说明**：业绩预告
- **测试状态**：✗ 测试失败: The operation was aborted due to timeout

**测试请求体示例**：
```json
{
  "interface": "stock_yjyg_em",
  "params": {
    "date": "20241231"
  },
  "verify_ssl": false
}
```

**实际调用返回数据示例**：
```json
{
  "error": "The operation was aborted due to timeout"
}
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| date | 必填，报告期 YYYYMMDD |

**测试用最小参数**：

```json
{
  "date": "20241231"
}
```

### option_finance_board

- **说明**：金融期权行情板
- **测试状态**：✓ 测试通过
- **返回字段示例**：日期, code, price, pct_chg, 前结价, strike, 数量

**测试请求体示例**：
```json
{
  "interface": "option_finance_board",
  "params": {
    "symbol": "华夏上证50ETF期权",
    "end_month": "2503"
  },
  "verify_ssl": false
}
```

**实际返回元信息**：
```json
{
  "ok": true,
  "cache_hit": false,
  "requested_rows": 48,
  "returned_rows": 13,
  "sampling_step": 4
}
```

**实际调用返回数据示例**：
```json
[
  {
    "日期": "20260318123925",
    "code": "510050C2603A02700",
    "price": 0.4,
    "pct_chg": -3.5,
    "前结价": 0.4145,
    "strike": 2.63,
    "数量": 48
  },
  {
    "日期": "20260318123925",
    "code": "510050C2603A02900",
    "price": 0.2023,
    "pct_chg": -8.21,
    "前结价": 0.2204,
    "strike": 2.825,
    "数量": 48
  },
  {
    "日期": "20260318123925",
    "code": "510050C2603A03200",
    "price": 0.0044,
    "pct_chg": -24.14,
    "前结价": 0.0058,
    "strike": 3.117,
    "数量": 48
  }
]
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| symbol | 可选，如华夏上证50ETF期权、华泰柏瑞沪深300ETF期权 |
| end_month | 可选，到期月 YYMM，如 2503 |

**测试用最小参数**：

```json
{
  "symbol": "华夏上证50ETF期权",
  "end_month": "2503"
}
```

### option_current_em

- **说明**：期权当日行情（东方财富全市场）
- **测试状态**：✗ 测试失败: HTTPSConnectionPool(host='23.push2.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/clist/get?pn=1&pz=100&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m%3A10%2Cm%3A12%2Cm%3A140%2Cm%3A141%2Cm%3A151%2Cm%3A163%2Cm%3A226&fields=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6%2Cf7%2Cf8%2Cf9%2Cf10%2Cf12%2Cf13%2Cf14%2Cf15%2Cf16%2Cf17%2Cf18%2Cf20%2Cf21%2Cf23%2Cf24%2Cf25%2Cf22%2Cf28%2Cf11%2Cf62%2Cf128%2Cf136%2Cf115%2Cf152%2Cf133%2Cf108%2Cf163%2Cf161%2Cf162 (Caused by ProxyError('Unable to connect to proxy', RemoteDisconnected('Remote end closed connection without response')))

**测试请求体示例**：
```json
{
  "interface": "option_current_em",
  "params": {},
  "verify_ssl": false
}
```

**实际调用返回数据示例**：
```json
{
  "error": {
    "type": "ProxyError",
    "message": "HTTPSConnectionPool(host='23.push2.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/clist/get?pn=1&pz=100&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m%3A10%2Cm%3A12%2Cm%3A140%2Cm%3A141%2Cm%3A151%2Cm%3A163%2Cm%3A226&fields=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6%2Cf7%2Cf8%2Cf9%2Cf10%2Cf12%2Cf13%2Cf14%2Cf15%2Cf16%2Cf17%2Cf18%2Cf20%2Cf21%2Cf23%2Cf24%2Cf25%2Cf22%2Cf28%2Cf11%2Cf62%2Cf128%2Cf136%2Cf115%2Cf152%2Cf133%2Cf108%2Cf163%2Cf161%2Cf162 (Caused by ProxyError('Unable to connect to proxy', RemoteDisconnected('Remote end closed connection without response')))",
    "hint": null
  }
}
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|

**测试用最小参数**：

```json
{}
```

### option_sse_daily_sina

- **说明**：上交所期权日线
- **测试状态**：✗ 测试失败: Length mismatch: Expected axis has 0 elements, new values have 6 elements

**测试请求体示例**：
```json
{
  "interface": "option_sse_daily_sina",
  "params": {
    "symbol": "10005050C2503M"
  },
  "verify_ssl": false
}
```

**实际调用返回数据示例**：
```json
{
  "error": {
    "type": "ValueError",
    "message": "Length mismatch: Expected axis has 0 elements, new values have 6 elements",
    "hint": null
  }
}
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| symbol | 必填，上交所期权合约代码 |

**测试用最小参数**：

```json
{
  "symbol": "10005050C2503M"
}
```

### option_commodity_hist

- **说明**：商品期权历史
- **测试状态**：✗ 测试失败: 'm2503-C-4000'

**测试请求体示例**：
```json
{
  "interface": "option_commodity_hist",
  "params": {
    "symbol": "m2503-C-4000",
    "exchange": "dce",
    "trade_date": "2024-01-02"
  },
  "verify_ssl": false
}
```

**实际调用返回数据示例**：
```json
{
  "error": {
    "type": "KeyError",
    "message": "'m2503-C-4000'",
    "hint": null
  }
}
```

**入参 (params)**：

| 参数 | 说明 |
|------|------|
| symbol | 必填，商品期权合约 |
| exchange | dce|shfe|czce |
| trade_date | 可选，YYYYMMDD |

**测试用最小参数**：

```json
{
  "symbol": "m2503-C-4000",
  "exchange": "dce",
  "trade_date": "2024-01-02"
}
```

## SSL 与数据源说明

### SSL 验证
- **默认启用 SSL 验证**。在正常网络环境下，启用 SSL 通常更稳定，数据源连接成功率更高。
- 若在企业代理/防火墙环境下出现 `certificate verify failed` 等错误，可设置环境变量 `AKSHARE_NO_SSL_VERIFY=1` 或请求时传 `verify_ssl: false`。
- 测试报告会先尝试 SSL，若检测到证书/连接类错误会自动重试禁用 SSL。

### 数据源回退
部分接口已实现多数据源回退，主源失败时自动尝试备选：
| 接口 | 主源 | 备选 |
|------|------|------|
| stock_zh_a_spot | 东方财富 | 新浪 |
| stock_board_industry | 东方财富 | 同花顺 |
| stock_board_concept | 东方财富 | 同花顺 |
| fund_etf_market | 东方财富 | 同花顺 |
| futures_zh_hist | 新浪/东方财富 | 互相回退 |
| bond_zh_hs_market | 新浪 | 少页数重试 |

### 雅虎数据源
AKShare 主要使用东方财富、新浪、同花顺等国内数据源。A 股、期货、基金等境内品种**无雅虎数据源**，雅虎财经不覆盖 A 股市场。

## 测试报告

生成时间：2026-03-18T04:20:58.291Z
通过：17 / 27
