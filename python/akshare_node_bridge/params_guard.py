# noqa: D100
"""LLM 调用防护：参数规范化、校验、友好错误。"""
from __future__ import annotations

import re
from typing import Any

# 各接口必填参数及错误提示（用于 LLM 理解）
REQUIRED_PARAMS: dict[str, dict[str, str]] = {
    "stock_zh_a_hist": {"symbol": "股票代码，6位如 000001、600519"},
    "stock_intraday_em": {"symbol": "股票代码，6位如 000001"},
    "stock_bid_ask_em": {"symbol": "股票代码，6位如 000001"},
    "stock_index_zh_hist": {"symbol": "指数代码，如 000001(上证)、399001(深证)、399006(创业板)"},
    "stock_financial_abstract": {"symbol": "股票代码，6位如 000001"},
    "stock_yjbb_em": {},  # date 有默认值
    "stock_yjyg_em": {},  # date 有默认值
    "fund_open_info": {"symbol": "基金代码，如 110011"},
    "bond_cb_meta": {},  # mode=summary 时无需 symbol，否则需要
    "option_finance_board": {},  # symbol/end_month 有默认值
    "option_sse_daily_sina": {"symbol": "期权合约代码，如 10004466"},
    "option_commodity_hist": {"symbol": "商品期权合约代码，如 m2503-C-4000"},
}


def _coerce_str(value: Any) -> str | None:
    """将值转为字符串，空值返回 None。"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return str(int(value)) if isinstance(value, float) and value == int(value) else str(value)
    s = str(value).strip()
    return s if s else None


def _coerce_date(value: Any) -> str | None:
    """规范日期为 YYYY-MM-DD，兼容 YYYYMMDD、YYYY/MM/DD。"""
    s = _coerce_str(value)
    if not s:
        return None
    s = s.replace("/", "-").replace(".", "-")
    m = re.match(r"^(\d{4})-?(\d{1,2})-?(\d{1,2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
    m = re.match(r"^(\d{4})(\d{2})(\d{2})", s.replace("-", "").replace("/", ""))
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return s


def _normalize_date_compact(value: Any) -> str | None:
    """规范为 YYYYMMDD 格式（用于 stock_yjbb_em、option 等）。"""
    s = _coerce_str(value)
    if not s:
        return None
    s = re.sub(r"[-\s/.]", "", s)
    if re.match(r"^\d{8}$", s):
        return s
    ds = _coerce_date(value)
    if ds:
        return ds.replace("-", "")
    return s


def _ensure_params_dict(params: Any) -> dict[str, Any]:
    """确保 params 为 dict。LLM 可能传 null、字符串等。"""
    if params is None:
        return {}
    if isinstance(params, dict):
        return params
    if isinstance(params, str) and params.strip():
        # 尝试解析 "symbol=000001" 或 JSON
        s = params.strip()
        if s.startswith("{"):
            try:
                import json
                return json.loads(s)
            except Exception:
                pass
        # key=value 简单解析
        out: dict[str, Any] = {}
        for part in s.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                out[k.strip()] = v.strip() if v.strip() else None
        return out
    return {}


def normalize_params(params: Any, interface_name: str) -> dict[str, Any]:
    """
    规范化参数，兼容 LLM 常见传入方式。
    - 数值 symbol 转字符串
    - 日期格式统一
    - 过滤 None 和空字符串（可选参数）
    """
    raw = _ensure_params_dict(params)
    out: dict[str, Any] = {}
    for k, v in raw.items():
        if v is None:
            continue
        key = str(k).strip()
        if not key:
            continue
        # 常见键名兼容
        if key in ("code", "stock", "ts_code") and "symbol" not in raw and interface_name in (
            "stock_zh_a_hist", "stock_zh_a_spot", "stock_financial_abstract", "stock_intraday_em", "stock_bid_ask_em"
        ):
            key = "symbol"
        if key in ("start", "begin") and "start_date" not in raw:
            key = "start_date"
        if key in ("end", "until") and "end_date" not in raw:
            key = "end_date"
        if key in ("ex", "market") and "exchange" not in raw and interface_name == "option_commodity_hist":
            key = "exchange"
        val: Any
        if key == "datasets":
            # datasets 须为列表，保持原样；LLM 可能传字符串则尝试解析
            if isinstance(v, list):
                val = [_coerce_str(x) or x for x in v if x is not None]
                val = [x for x in val if x] or None
            elif isinstance(v, str) and v.strip():
                try:
                    import json
                    parsed = json.loads(v)
                    val = parsed if isinstance(parsed, list) else [parsed]
                except Exception:
                    val = _coerce_str(v) or None
            else:
                val = None
        elif key in ("symbol", "period", "adjust", "mode", "indicator", "market"):
            val = _coerce_str(v)
        elif key in ("start_date", "end_date"):
            val = _coerce_date(v) or _coerce_str(v)
        elif key in ("date", "trade_date") and interface_name in ("stock_yjbb_em", "stock_yjyg_em", "option_commodity_hist"):
            val = _normalize_date_compact(v) or _coerce_str(v)
        elif key == "end_month":
            val = _coerce_str(v)
            if val and re.match(r"^\d{4}$", val.replace("-", "")):
                val = val.replace("-", "")[-4:]  # 2503
        elif key == "exchange" and interface_name == "option_commodity_hist":
            val = (_coerce_str(v) or "").lower()
            if val in ("dce", "shfe", "czce"):
                pass
            elif val in ("大商所", "大连"):
                val = "dce"
            elif val in ("上期所", "上期"):
                val = "shfe"
            elif val in ("郑商所", "郑州"):
                val = "czce"
            else:
                val = val or None
        else:
            val = v
        if val is not None and val != "":
            out[key] = val
    return dict(sorted(out.items(), key=lambda x: x[0]))


def validate_required(interface_name: str, params: dict[str, Any]) -> tuple[bool, str | None]:
    """
    校验必填参数。返回 (是否通过, 错误信息)。
    错误信息面向 LLM，说明缺少什么、应如何填写。
    """
    req = REQUIRED_PARAMS.get(interface_name, {})
    if not req:
        return True, None
    if interface_name == "bond_cb_meta" and params.get("mode") == "summary":
        return True, None
    missing: list[str] = []
    for param, hint in req.items():
        val = params.get(param)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(f"{param}（{hint}）")
    if missing:
        return False, f"接口 {interface_name} 需要参数: {', '.join(missing)}"
    return True, None
