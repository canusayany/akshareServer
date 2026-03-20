# 多资产投资 Agent 金融工具接口 - 项目需求文档

**文档版本**: v1.0  
**更新日期**: 2026-03-20  
**状态**: 需求确认

---

## 目录

1. 需求概述
2. 核心需求详解
3. 接口设计概览
4. 实现路线图

---

## 1. 需求概述

### 1.1 背景

当前系统存在的问题：

- API 返回数据受限制，进行了不必要的切片处理
- 接口按数据品类拆分，LLM 需要面向"原始数据源"调用工具，而非"决策问题"调用
- 工具返回信息密度低，需要 LLM 做大量后处理解释

### 1.2 新需求目标

| 需求 | 描述 |
|------|------|
| **需求 1** | 数据返回不再限制大小，也不做切片，有多少数据返回多少数据 |
| **需求 2** | 用 5 个高层接口替换现有 27+ 个按品类拆分的接口 |
| **需求 3** | LLM 面向决策问题调用工具，获得高信息密度的结构化结果 |
| **需求 4** | 支持多轮自由调用，不绑死 workflow |

---

## 2. 核心需求详解

### 2.1 需求 1：数据返回不限制大小

#### 当前状态

```json
{
  "ok": true,
  "interface": "stock_zh_a_hist",
  "max_rows": 15,
  "requested_rows": 20,
  "returned_rows": 10,
  "sampling_step": 2,
  "rows": [...]
}
```

**问题**：对返回数据进行切片（sampling）

#### 目标状态

```json
{
  "ok": true,
  "interface": "stock_zh_a_hist",
  "total_rows": 500,
  "returned_rows": 500,
  "rows": [...]
}
```

**改进**：

- ✅ 移除 `max_rows`、`sampling_step`
- ✅ 返回完整数据，有多少返回多少
- ✅ 不改变数据结构，仅改变返回策略
- ✅ 保留数据质量字段用于监控

**实施范围**：

- 所有现有 27 个接口
- 所有新增 5 个接口（见下文）

---

### 2.2 需求 2 ＆ 3：新接口设计原则

#### 设计哲学

**旧模式**（不推荐）：
```
查股价 → query_stock_data → 100行K线 → LLM自己分析趋势
查期权 → query_option_data → 完整期权链 → LLM自己过滤 ATM
查宏观 → query_macro_data → 一堆原始指标 → LLM自己做决策
```

**新模式**（推荐）：
```
我要调仓 → get_portfolio_profile → 组合集中度、到期簇、调仓压力 ✓ 可直接决策
商品走势怎样 → get_market_context → 风险模式、趋势、关键驱动 ✓ 可直接决策
宁德时代有什么风险 → get_asset_snapshots → 趋势、波动、风险标签 ✓ 可直接决策
```

#### 核心 5 个接口

| 接口 | 作用 | 替代原接口 |
|------|------|----------|
| `resolve_portfolio_positions` | 解析用户持仓，消除歧义 | - |
| `get_market_context` | 市场环境结构化结论 | `query_macro_data`, 日报/周报, websearch |
| `get_asset_snapshots` | 资产统一画像 | `query_stock_data`, `query_option_data`, 等所有行情接口 |
| `get_portfolio_profile` | 组合风险画像 | - |
| `get_targeted_event_context` | 与持仓相关的事件摘要 | `report_lookup`, webseach |

---

## 3. 接口设计概览

### 3.1 接口 1：`resolve_portfolio_positions`

**作用**：把用户给的原始持仓解析成标准资产对象。

**问题解决**：
- 中文简称不规范
- 同名资产歧义
- 期权简称格式混乱
- 主力合约/连续合约识别

**示例**：

**输入**：
```json
{
  "positions": [
    {"raw_name": "宁德时代", "quantity": 500, "cost_basis": 182.3, "side": "long"},
    {"raw_name": "510300购4月3500", "quantity": 20, "cost_basis": 0.126, "side": "long"}
  ],
  "as_of": "2026-03-20T14:30:00+08:00"
}
```

**输出**：
```json
{
  "positions": [
    {
      "position_id": "pos_1",
      "asset_id": "300750.SZ",
      "asset_type": "stock",
      "normalized_name": "宁德时代",
      "exchange": "SZSE",
      "quantity": 500,
      "cost_basis": 182.3,
      "resolution_confidence": 0.99
    },
    {
      "position_id": "pos_2",
      "asset_id": "510300-C-202604-3500",
      "asset_type": "option",
      "normalized_name": "510300 ETF Call 2026-04 3.5",
      "exchange": "SSE",
      "quantity": 20,
      "cost_basis": 0.126,
      "contract_multiplier": 10000,
      "underlying_asset_id": "510300.SH",
      "resolution_confidence": 0.95
    }
  ]
}
```

---

### 3.2 接口 2：`get_market_context`

**作用**：返回当前市场环境的**结构化结论**（不是原始数据）。

**示例输出**：
```json
{
  "market": "CN",
  "as_of": "2026-03-20T14:30:00+08:00",
  "market_regime": {
    "risk_mode": "neutral",
    "equity_trend": "sideways_to_bullish",
    "style_bias": "large_cap",
    "volatility_regime": "medium",
    "liquidity_regime": "neutral"
  },
  "macro_signals": {
    "growth_signal": "stable",
    "rate_pressure": "mild",
    "policy_bias": "slightly_supportive"
  },
  "core_indices": {
    "CSI300": {"last": 3628.5, "return_pct_20d": 2.3, "trend": "up"},
    "CSI500": {"last": 5480.1, "return_pct_20d": -0.8, "trend": "flat"},
    "ChiNext": {"last": 2118.4, "return_pct_20d": -1.6, "trend": "weak"}
  },
  "key_drivers": ["northbound_inflow", "large_cap_outperforming_small_cap"],
  "event_summary": [
    {
      "topic": "政策",
      "impact_level": "medium",
      "summary": "近期政策语气对风险资产边际偏正面"
    }
  ]
}
```

**关键指标计算**：

见本文档后半部分"8. 统一字段计算规则速查"

---

### 3.3 接口 3：`get_asset_snapshots`

**作用**：批量返回持仓资产的统一画像（最核心接口）。

**替代原接口**：
- `query_stock_data`（股票行情）
- `query_option_data`（期权链）
- `query_futures_data`（期货行情）
- `query_fund_data`（基金净值）
- `query_cbond_data`（可转债行情）

**示例输出**（股票）：
```json
{
  "snapshots": [
    {
      "asset_id": "300750.SZ",
      "asset_type": "stock",
      "as_of": "2026-03-20T14:30:00+08:00",
      "summary": {
        "trend": "up",
        "momentum": "moderately_strong",
        "volatility": "medium",
        "liquidity": "good",
        "overall_state": "tradable_but_near_resistance"
      },
      "price": {
        "last": 188.4,
        "change_pct_1d": 1.8,
        "return_pct_5d": 4.2,
        "return_pct_20d": -1.5
      },
      "position": {
        "quantity": 500,
        "cost_basis": 182.3,
        "market_value": 94200.0,
        "unrealized_pnl": 3050.0,
        "unrealized_pnl_pct": 3.33
      },
      "trend": {
        "ma5": 186.9,
        "ma20": 181.2,
        "ma60": 184.1,
        "ma_alignment": "bullish"
      },
      "momentum": {
        "rsi_14": 61.8,
        "macd_state": "bullish"
      },
      "volatility_metrics": {
        "hv_20": 0.24,
        "atr_14": 5.2,
        "atr_pct": 2.76
      },
      "risk_flags": ["near_resistance"],
      "asset_specific": {
        "sector": "新能源",
        "valuation_label": "neutral_to_high",
        "fundamental_label": "good",
        "event_risk": {"earnings_within_days": 9}
      }
    }
  ]
}
```

**资产特定字段**：

| 资产类型 | 特定字段 |
|---------|---------|
| 股票 | `sector`, `beta_60d`, `valuation`, `fundamental`, `event_risk` |
| 期权 | `underlying_asset_id`, `dte`, `moneyness`, `greeks`, `iv`, `position_risk` |
| 期货 | `basis`, `term_structure`, `roll_risk`, `trend_confirmation` |
| 基金 | `fund_type`, `tracking_error_20d`, `flow`, `style_exposure` |
| 可转债 | `conversion_value`, `pure_bond_value`, `double_low_score`, `ytm` |

---

### 3.4 接口 4：`get_portfolio_profile`

**作用**：返回组合级风险画像，用于调仓决策。

**示例输出**：
```json
{
  "portfolio": {
    "nav": 1280000.0,
    "cash_balance": 180000.0,
    "cash_pct": 0.141,
    "gross_exposure": 1560000.0,
    "leverage": 1.219
  },
  "allocation": {
    "stock": 0.48,
    "option": 0.10,
    "futures": 0.12,
    "fund": 0.18,
    "convertible_bond": 0.12
  },
  "exposure": {
    "equity_delta_equivalent": 0.81,
    "growth_style_exposure": 0.66,
    "large_cap_exposure": 0.29
  },
  "concentration": {
    "top1_pct": 0.19,
    "top3_pct": 0.49,
    "same_theme_cluster_pct": 0.37
  },
  "risk_metrics": {
    "portfolio_volatility_est_20d": 0.22,
    "portfolio_var_95_1d": -0.024,
    "max_drawdown_60d": -0.11
  },
  "risk_alerts": [
    "growth_style_overweight",
    "option_expiry_cluster_within_14d"
  ],
  "rebalance_pressure": "medium"
}
```

---

### 3.5 接口 5：`get_targeted_event_context`

**作用**：返回与持仓**高度相关**的近期事件摘要。

**示例输出**：
```json
{
  "events": [
    {
      "asset_id": "300750.SZ",
      "event_time": "2026-03-18T08:00:00+08:00",
      "event_type": "policy",
      "impact_level": "medium",
      "direction": "positive",
      "relevance_score": 0.82,
      "summary": "行业政策边际改善"
    },
    {
      "asset_id": "300750.SZ",
      "event_time": "2026-03-26T00:00:00+08:00",
      "event_type": "earnings",
      "impact_level": "high",
      "direction": "unknown",
      "relevance_score": 0.95,
      "summary": "财报窗口临近"
    },
    {
      "asset_id": "510300-C-202604-3500",
      "event_time": "2026-04-22T15:00:00+08:00",
      "event_type": "expiry",
      "impact_level": "high",
      "direction": "neutral",
      "relevance_score": 0.99,
      "summary": "期权临近到期，时间价值损耗加快"
    }
  ]
}
```

---

## 4. 通用约定

### 4.1 时间格式

所有时间统一使用 **RFC3339**：

```
2026-03-20T14:30:00+08:00
```

统一字段名：
- `as_of`：数据截面时间
- `event_time`：事件时间
- `expiry_date`：合约到期日

### 4.2 资产类型枚举

```
stock, option, futures, fund, convertible_bond, cash, index, macro
```

### 4.3 市场枚举

```
CN, US, HK, GLOBAL
```

### 4.4 通用数据质量对象

所有接口必须返回：

```json
{
  "data_quality": {
    "freshness_sec": 15,
    "confidence": 0.94,
    "missing_fields": [],
    "source_count": 3
  }
}
```

**字段说明**：

| 字段 | 说明 |
|------|------|
| `freshness_sec` | 当前结果距离最新底层数据更新时间的秒数 |
| `confidence` | 结果可信度，范围 0~1 |
| `missing_fields` | 缺失字段列表 |
| `source_count` | 底层使用的数据源数量 |

**置信度计算**：

```
confidence = 1.0
           - 0.05 * len(missing_critical_fields)
           - freshness_penalty
           - estimation_penalty
           (最终裁剪到 [0, 1])
```

---

## 5. 关键计算规则

### 5.1 市场情绪 risk_mode

**枚举**: `risk_on`, `neutral`, `risk_off`

**计算方法**：
```
regime_score =
  0.35 * trend_score
+ 0.20 * flow_score
+ 0.20 * vol_score
+ 0.15 * liquidity_score
+ 0.10 * event_score

映射：
>= 0.35  → risk_on
<= -0.35 → risk_off
中间     → neutral
```

### 5.2 权益趋势 equity_trend

**枚举**: `bullish`, `sideways_to_bullish`, `sideways`, `sideways_to_bearish`, `bearish`

**规则**：
- 多数核心指数 > MA20/MA60 且 MA20 斜率正 → `bullish`
- 沪深300 强、中小盘弱 → `sideways_to_bullish`
- 多数在均线附近 → `sideways`
- 多数在 MA20 下方 → `sideways_to_bearish`
- 多数在 MA20/MA60 下方且斜率负 → `bearish`

### 5.3 波动率等级 volatility_regime

**枚举**: `low`, `medium`, `high`, `extreme`

**计算**：
```
vol_percentile = percentile(current_vol, trailing_252d_vol_series)

映射：
< 30%    → low
30-70%   → medium
70-90%   → high
> 90%    → extreme
```

---

## 6. 底层依赖关系

### 6.1 原接口保留为内部服务

**不对 LLM 暴露，仅作内部依赖**：

```
query_stock_data
query_option_data
query_futures_data
query_fund_data
query_cbond_data
query_macro_data
web_search_finance
report_lookup
```

### 6.2 新接口与旧接口映射

| 新接口 | 内部依赖 |
|--------|---------|
| `resolve_portfolio_positions` | 证券主数据表、合约元数据、别名映射表 |
| `get_market_context` | 宏观数据、指数行情、资金流、日报/周报/月报、金融 websearch |
| `get_asset_snapshots` | 股票/期权/期货/基金/可转债/财务/条款 接口 |
| `get_portfolio_profile` | `get_asset_snapshots`、历史收益率、风格标签、合约元数据 |
| `get_targeted_event_context` | 日报/周报/月报、金融 websearch、日历数据 |

---

## 7. 实现路线图

### Phase 1：基础接口（优先级最高）

```
1. resolve_portfolio_positions     ← 无其他依赖，最快上线
2. get_asset_snapshots            ← 数据聚合，支持核心决策
3. get_portfolio_profile          ← 依赖 get_asset_snapshots
```

**预期输出**：能支持基础组合分析

### Phase 2：扩展接口

```
4. get_market_context             ← 依赖宏观数据、指数、资金流
5. get_targeted_event_context     ← 依赖日报/websearch/日历
```

**预期输出**：支持完整决策辅助

### Phase 3：优化迭代

- 性能优化（缓存、预计算）
- 字段丰富度提升
- 数据源稳定性加强

---

## 8. 统一字段计算规则速查

### 8.1 价格与收益

```
change_pct_1d = last / prev_close - 1
return_pct_N  = last / close_N_days_ago - 1
```

### 8.2 技术指标

```
MA_N         = mean(close[-N:])
MA_slope_5d  = MA_today / MA_5d_ago - 1

RSI(14)      = 100 - 100 / (1 + RS)  其中 RS = avg_gain_14 / avg_loss_14

DIF          = EMA12(close) - EMA26(close)
DEA          = EMA9(DIF)
MACD_hist    = DIF - DEA
```

### 8.3 波动率与流动性

```
log_ret_t    = ln(close_t / close_t-1)
hv_20        = std(log_ret[-20:]) * sqrt(252)

TR_t         = max(high-low, abs(high-prev_close), abs(low-prev_close))
ATR_14       = MA(TR, 14)
atr_pct      = ATR_14 / last

volume_vs_20d = volume_today / avg(volume[-20:])
```

### 8.4 衍生品特定

```
beta_60d               = cov(asset_ret_60d, bench_ret_60d) / var(bench_ret_60d)
iv_rank                = (current_iv - min_iv_252d) / (max_iv_252d - min_iv_252d) * 100
basis_value            = spot_price - futures_price
basis_pct              = (spot_price - futures_price) / spot_price
conversion_value       = (100 / conversion_price) * underlying_stock_price
conversion_premium_pct = bond_price / conversion_value - 1
double_low_score       = bond_price + conversion_premium_pct
```

### 8.5 组合级指标

```
leverage                    = gross_exposure / nav
equity_delta_equivalent     = Σ(delta_adjusted_equity_exposure_i) / nav
portfolio_vol               = std(Σ(w_i * ret_i_t)) * sqrt(252)
```

---

## 9. 开发检查清单

- [ ] Phase 1 接口完成
  - [ ] `resolve_portfolio_positions` 核心逻辑
  - [ ] `get_asset_snapshots` 数据聚合
  - [ ] `get_portfolio_profile` 风险计算
- [ ] 数据质量字段集成
- [ ] 数据不做切片，完整返回
- [ ] 所有时间字段统一为 RFC3339
- [ ] 旧接口保留为内部调用
- [ ] 测试覆盖率 > 80%
- [ ] API 文档更新
- [ ] LLM 提示词更新（只暴露新 5 个接口）

---

## 10. 附录：完整示例

### LLM 决策场景

**场景 1：我想调仓**
```
LLM 调用 1: get_portfolio_profile
    ↓ 获得：集中度、到期簇、调仓压力 = "medium"
    
LLM 调用 2: get_asset_snapshots [重点持仓] 
    ↓ 获得：各资产趋势、风险标签
    
LLM 调用 3: get_market_context
    ↓ 获得：市场风险模式、关键驱动，决定是否调仓
    
LLM 输出：建议行动
```

**场景 2：宁德时代怎样**
```
LLM 调用 1: resolve_portfolio_positions ["宁德时代"]
    ↓ 获得：asset_id = 300750.SZ
    
LLM 调用 2: get_asset_snapshots [300750.SZ]
    ↓ 获得：trend, momentum, volatility, risk_flags, fundamental, event_risk
    
LLM 调用 3: get_targeted_event_context [300750.SZ]
    ↓ 获得：相关事件摘要
    
LLM 输出：综合分析
```

---

**文档完** ✓
