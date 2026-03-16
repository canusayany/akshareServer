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
- **返回字段示例**：代码, 名称, 最新价, 涨跌额, 涨跌幅, 买入, 卖出, 昨收, 今开, 最高

**实际调用返回数据示例**：
```json
[
  {
    "代码": "bj920000",
    "名称": "安徽凤凰",
    "最新价": 17.41,
    "涨跌额": -0.36,
    "涨跌幅": -2.026,
    "买入": 17.41,
    "卖出": 17.43,
    "昨收": 17.77,
    "今开": 17.77,
    "最高": 17.77,
    "最低": 17.31,
    "成交量": 509011,
    "成交额": 8892290,
    "时间戳": "15:30:02"
  },
  {
    "代码": "sh600805",
    "名称": "悦达投资",
    "最新价": 5.79,
    "涨跌额": 0.15,
    "涨跌幅": 2.66,
    "买入": 5.78,
    "卖出": 5.79,
    "昨收": 5.64,
    "今开": 5.63,
    "最高": 5.85,
    "最低": 5.6,
    "成交量": 34413149,
    "成交额": 197359472,
    "时间戳": "15:00:03"
  },
  {
    "代码": "sh603899",
    "名称": "晨光股份",
    "最新价": 26.2,
    "涨跌额": 0.19,
    "涨跌幅": 0.73,
    "买入": 26.2,
    "卖出": 26.21,
    "昨收": 26.01,
    "今开": 26.02,
    "最高": 26.24,
    "最低": 25.91,
    "成交量": 2698100,
    "成交额": 70491133,
    "时间戳": "15:00:01"
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
- **测试状态**：✓ 测试通过

**实际调用返回数据示例**：
```json
[]
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

**实际调用返回数据示例**：
```json
[
  {
    "时间": "09:15:00",
    "成交价": 10.92,
    "手数": 110,
    "买卖盘性质": "中性盘"
  },
  {
    "时间": "09:35:57",
    "成交价": 10.93,
    "手数": 10,
    "买卖盘性质": "卖盘"
  },
  {
    "时间": "09:45:00",
    "成交价": 10.91,
    "手数": 132,
    "买卖盘性质": "卖盘"
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

**实际调用返回数据示例**：
```json
[
  {
    "item": "sell_5",
    "value": 10.97
  },
  {
    "item": "sell_5_vol",
    "value": 990800
  },
  {
    "item": "sell_4",
    "value": 10.96
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
- **返回字段示例**：symbol, exchange, name, trade, settlement, presettlement, open, high, low, close

**实际调用返回数据示例**：
```json
[
  {
    "symbol": "TA0",
    "exchange": "czce",
    "name": "PTA连续",
    "trade": 6982,
    "settlement": 7006,
    "presettlement": 6960,
    "open": 6820,
    "high": 7256,
    "low": 6720,
    "close": 6982,
    "bidprice1": 6980,
    "askprice1": 6984,
    "bidvol1": 28,
    "askvol1": 7,
    "volume": 2345417,
    "position": 1164940,
    "ticktime": "15:00:00",
    "tradedate": "2026-03-16",
    "preclose": 6934,
    "changepercent": 0.0031609,
    "bid": 0,
    "ask": 0,
    "prevsettlement": 6960
  },
  {
    "symbol": "TA2607",
    "exchange": "czce",
    "name": "PTA2607",
    "trade": 6840,
    "settlement": 6876,
    "presettlement": 6786,
    "open": 6710,
    "high": 7100,
    "low": 6590,
    "close": 6840,
    "bidprice1": 6840,
    "askprice1": 6844,
    "bidvol1": 45,
    "askvol1": 7,
    "volume": 71726,
    "position": 92496,
    "ticktime": "15:00:00",
    "tradedate": "2026-03-16",
    "preclose": 6790,
    "changepercent": 0.0079576,
    "bid": 0,
    "ask": 0,
    "prevsettlement": 6786
  },
  {
    "symbol": "TA2608",
    "exchange": "czce",
    "name": "PTA2608",
    "trade": 6762,
    "settlement": 6794,
    "presettlement": 6704,
    "open": 6596,
    "high": 7010,
    "low": 6564,
    "close": 6762,
    "bidprice1": 6760,
    "askprice1": 6772,
    "bidvol1": 12,
    "askvol1": 1,
    "volume": 33289,
    "position": 28814,
    "ticktime": "15:00:00",
    "tradedate": "2026-03-16",
    "preclose": 6700,
    "changepercent": 0.0086516,
    "bid": 0,
    "ask": 0,
    "prevsettlement": 6704
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

**实际调用返回数据示例**：
```json
[
  {
    "symbol": "cffex",
    "contracts": "IF2606,TF2606,IH2603,IC2606,TS2606,IM2606"
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
- **测试状态**：✓ 测试通过
- **返回字段示例**：date, symbol, spot_price, near_contract, near_contract_price, dominant_contract, dominant_contract_price, near_month, dominant_month, near_basis

**实际调用返回数据示例**：
```json
[
  {
    "date": "20240115",
    "symbol": "C",
    "spot_price": 2437.14,
    "near_contract": "c2401",
    "near_contract_price": 2403,
    "dominant_contract": "c2405",
    "dominant_contract_price": 2384,
    "near_month": "2401",
    "dominant_month": "2405",
    "near_basis": -34.13999999999987,
    "dom_basis": -53.13999999999987,
    "near_basis_rate": -0.014008222752898813,
    "dom_basis_rate": -0.02180424596042896
  },
  {
    "date": "20240115",
    "symbol": "EB",
    "spot_price": 8550,
    "near_contract": "eb2401",
    "near_contract_price": 8373,
    "dominant_contract": "eb2403",
    "dominant_contract_price": 8530,
    "near_month": "2401",
    "dominant_month": "2403",
    "near_basis": -177,
    "dom_basis": -20,
    "near_basis_rate": -0.020701754385964888,
    "dom_basis_rate": -0.002339181286549752
  },
  {
    "date": "20240115",
    "symbol": "SM",
    "spot_price": 6121.67,
    "near_contract": "SM401",
    "near_contract_price": 6340,
    "dominant_contract": "SM403",
    "dominant_contract_price": 6356,
    "near_month": "2401",
    "dominant_month": "2403",
    "near_basis": 218.32999999999993,
    "dom_basis": 234.32999999999993,
    "near_basis_rate": 0.035665104456790386,
    "dom_basis_rate": 0.03827877033554561
  }
]
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
    "基金代码": "003861",
    "拼音缩写": "ZSXFHHA",
    "基金简称": "招商兴福混合A",
    "基金类型": "混合型-灵活",
    "拼音全称": "ZHAOSHANGXINGFUHUNHEA"
  },
  {
    "基金代码": "007461",
    "拼音缩写": "DBRHZQA",
    "基金简称": "德邦锐泓债券A",
    "基金类型": "债券型-长债",
    "拼音全称": "DEBANGRUIHONGZHAIQUANA"
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

**实际调用返回数据示例**：
```json
[
  {
    "序号": 1,
    "基金代码": "159297",
    "基金名称": "南方国证港股通创新药ETF",
    "当前-单位净值": 0.7682,
    "当前-累计净值": 0.7682,
    "前一日-单位净值": 0.7447,
    "前一日-累计净值": 0.7447,
    "增长值": 0.0235,
    "增长率": 3.16,
    "赎回状态": "开放",
    "申购状态": "开放",
    "最新-交易日": "2026-03-16",
    "最新-单位净值": 0.7682,
    "最新-累计净值": 0.7682,
    "基金类型": "股票型",
    "查询日期": "2026-03-16"
  },
  {
    "序号": 497,
    "基金代码": "159883",
    "基金名称": "医疗器械ETF永赢",
    "当前-单位净值": 0.5018,
    "当前-累计净值": 0.5018,
    "前一日-单位净值": 0.5018,
    "前一日-累计净值": 0.5018,
    "增长值": 0,
    "增长率": 0,
    "赎回状态": "开放",
    "申购状态": "开放",
    "最新-交易日": "2026-03-16",
    "最新-单位净值": 0.5018,
    "最新-累计净值": 0.5018,
    "基金类型": "股票型",
    "查询日期": "2026-03-16"
  },
  {
    "序号": 993,
    "基金代码": "520990",
    "基金名称": "景顺长城中证国新港股通央企红利ETF",
    "当前-单位净值": null,
    "当前-累计净值": null,
    "前一日-单位净值": 1.115,
    "前一日-累计净值": 1.1725,
    "增长值": null,
    "增长率": null,
    "赎回状态": "开放",
    "申购状态": "开放",
    "最新-交易日": "2026-03-13",
    "最新-单位净值": 1.115,
    "最新-累计净值": 1.1725,
    "基金类型": "股票型",
    "查询日期": "2026-03-16"
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
- **测试状态**：✓ 测试通过
- **返回字段示例**：净值日期, 单位净值, 日增长率

**实际调用返回数据示例**：
```json
[
  {
    "净值日期": "2008-06-19",
    "单位净值": 1,
    "日增长率": 0
  },
  {
    "净值日期": "2009-05-05",
    "单位净值": 1.279,
    "日增长率": 0.7483
  },
  {
    "净值日期": "2010-01-04",
    "单位净值": 1.6802,
    "日增长率": -0.3144
  }
]
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

**实际调用返回数据示例**：
```json
[
  {
    "品种": "Au99.99",
    "时间": "00:00:00",
    "现价": 1112.61,
    "更新时间": "2026年03月17日 20:36:55"
  },
  {
    "品种": "Au99.99",
    "时间": "00:33:00",
    "现价": 1112.61,
    "更新时间": "2026年03月17日 20:36:55"
  },
  {
    "品种": "Au99.99",
    "时间": "01:06:00",
    "现价": 1112.61,
    "更新时间": "2026年03月17日 20:36:55"
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

**实际调用返回数据示例**：
```json
[
  {
    "报价机构": "重庆农村商行",
    "债券简称": "24交行债03BC",
    "买入净价": 100.71,
    "卖出净价": 101.01,
    "买入收益率": 1.6921,
    "卖出收益率": 1.5021
  },
  {
    "报价机构": "中信证券",
    "债券简称": "24交行债03BC",
    "买入净价": 100.53,
    "卖出净价": 101.18,
    "买入收益率": 1.8,
    "卖出收益率": 1.4
  },
  {
    "报价机构": "中信银行",
    "债券简称": "16铁道07",
    "买入净价": 100.82,
    "卖出净价": 100.93,
    "买入收益率": 1.6361,
    "卖出收益率": 1.4561
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
    "ticktime": "15:30:02"
  },
  {
    "symbol": "sh113056",
    "name": "重银转债",
    "trade": "129.931",
    "pricechange": "-0.100",
    "changepercent": "-0.077",
    "buy": "129.909",
    "sell": "129.930",
    "settlement": "130.031",
    "open": "130.016",
    "high": "130.650",
    "low": "129.753",
    "volume": 2778520,
    "amount": 361975029,
    "code": "113056",
    "ticktime": "15:00:01"
  },
  {
    "symbol": "sh113688",
    "name": "国检转债",
    "trade": "138.384",
    "pricechange": "-0.337",
    "changepercent": "-0.243",
    "buy": "138.361",
    "sell": "138.429",
    "settlement": "138.721",
    "open": "138.500",
    "high": "138.725",
    "low": "136.500",
    "volume": 331870,
    "amount": 45674371,
    "code": "113688",
    "ticktime": "15:00:01"
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
- **测试状态**：✓ 测试通过
- **返回字段示例**：name, code

**实际调用返回数据示例**：
```json
[
  {
    "name": "阿尔茨海默概念",
    "code": "308614"
  },
  {
    "name": "百度概念",
    "code": "301259"
  },
  {
    "name": "参股银行",
    "code": "301270"
  }
]
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

生成时间：2026-03-16T13:05:05.406Z
通过：19 / 19
