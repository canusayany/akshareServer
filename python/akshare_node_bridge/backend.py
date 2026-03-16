from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import math
import os
from typing import Any


_SSL_PATCHED = False


def _patch_ssl_if_needed(force: bool = False) -> None:
    """Disable SSL certificate verification when AKSHARE_NO_SSL_VERIFY=1 or force=True.

    In corporate / enterprise environments the outbound TLS proxy presents its
    own certificate, which Python's built-in SSL context rejects with
    "certificate verify failed".  Setting AKSHARE_NO_SSL_VERIFY=1 patches the
    three HTTP stacks that AKShare uses (stdlib ssl, requests, httpx) to skip
    verification globally for the life of the process.

    The patch is applied at most once and is completely skipped when the env
    var is absent or set to any value other than 1 / true / yes / on,
    unless ``force=True`` is passed (e.g. from a per-request verify_ssl=False).
    """
    global _SSL_PATCHED
    if _SSL_PATCHED:
        return
    if not force and os.environ.get("AKSHARE_NO_SSL_VERIFY", "").lower() not in {"1", "true", "yes", "on"}:
        return

    # 1. Patch stdlib ssl – covers urllib / urllib3 default context
    import ssl  # noqa: PLC0415
    ssl._create_default_https_context = ssl._create_unverified_context  # noqa: SLF001

    # 2. Patch requests (and its bundled urllib3)
    try:
        import requests  # noqa: PLC0415
        import urllib3   # noqa: PLC0415
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        _orig_send = requests.Session.send

        def _unverified_send(self, request, **kwargs):  # type: ignore[override]
            kwargs["verify"] = False
            return _orig_send(self, request, **kwargs)

        requests.Session.send = _unverified_send  # type: ignore[method-assign]
    except ImportError:
        pass

    # 3. Patch httpx if present (some AKShare versions use it)
    try:
        import httpx  # noqa: PLC0415

        _orig_client_init = httpx.Client.__init__

        def _unverified_client_init(self, *args, **kwargs):  # type: ignore[override]
            kwargs["verify"] = False
            _orig_client_init(self, *args, **kwargs)

        httpx.Client.__init__ = _unverified_client_init  # type: ignore[method-assign]

        _orig_async_init = httpx.AsyncClient.__init__

        def _unverified_async_init(self, *args, **kwargs):  # type: ignore[override]
            kwargs["verify"] = False
            _orig_async_init(self, *args, **kwargs)

        httpx.AsyncClient.__init__ = _unverified_async_init  # type: ignore[method-assign]
    except ImportError:
        pass

    _SSL_PATCHED = True


MACRO_DATASETS = (
    "macro_china_gdp",
    "macro_china_cpi",
    "macro_china_ppi",
    "macro_china_pmi",
    "macro_china_lpr",
    "macro_china_money_supply",
    "macro_china_new_financial_credit",
    "macro_china_fx_gold",
)

# LLM 可能传 "cpi,ppi,pm" 字符串，需要映射为完整 akshare 接口名
_MACRO_SHORTHAND: dict[str, str] = {
    "gdp": "macro_china_gdp",
    "cpi": "macro_china_cpi",
    "ppi": "macro_china_ppi",
    "pmi": "macro_china_pmi",
    "pm": "macro_china_pmi",  # pm 作为 pmi 的别名
    "lpr": "macro_china_lpr",
    "money_supply": "macro_china_money_supply",
    "credit": "macro_china_new_financial_credit",
    "fx_gold": "macro_china_fx_gold",
}


def _normalize_macro_datasets(value: Any) -> list[str]:
    """将 datasets 参数统一为 macro_china_* 接口名列表。"""
    if value is None:
        return list(MACRO_DATASETS)
    if isinstance(value, str):
        parts = [p.strip() for p in value.split(",") if p.strip()]
    elif isinstance(value, (list, tuple)):
        parts = [str(p).strip() for p in value if p]
    else:
        return list(MACRO_DATASETS)
    if not parts:
        return list(MACRO_DATASETS)
    result: list[str] = []
    for p in parts:
        if p.startswith("macro_china_"):
            result.append(p)
        else:
            resolved = _MACRO_SHORTHAND.get(p.lower(), f"macro_china_{p.lower()}")
            if resolved not in result:
                result.append(resolved)
    return result if result else list(MACRO_DATASETS)


def _make_json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(key): _make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_make_json_safe(item) for item in value]
    return str(value)


def _normalize_result(result: Any) -> list[dict[str, Any]]:
    if result is None:
        return []
    if isinstance(result, list):
        normalized: list[dict[str, Any]] = []
        for item in result:
            normalized.append(_make_json_safe(item) if isinstance(item, dict) else {"value": _make_json_safe(item)})
        return normalized
    if isinstance(result, dict):
        return [_make_json_safe(result)]
    if hasattr(result, "to_dict"):
        records = result.to_dict(orient="records")
        if isinstance(records, list):
            return [_make_json_safe(dict(item)) for item in records]
    return [{"value": _make_json_safe(result)}]


def _tag_rows(dataset: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"dataset": dataset, **row} for row in rows]


@dataclass
class BackendResult:
    rows: list[dict[str, Any]]


class StubBackend:
    def fetch(self, interface_name: str, params: dict[str, Any]) -> BackendResult:
        rows = self._rows_for(interface_name, params)
        return BackendResult(rows=rows)

    def _rows_for(self, interface_name: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        symbol = params.get("symbol", "000001")
        if interface_name == "stock_zh_a_hist":
            day = str(params.get("start_date", "2024-01-02"))[:10]
            return [
                {"symbol": symbol, "datetime": f"{day} 09:30:00", "close": 10.11, "volume": 1000},
                {"symbol": symbol, "datetime": f"{day} 10:00:00", "close": 10.12, "volume": 1100},
                {"symbol": symbol, "datetime": f"{day} 10:30:00", "close": 10.13, "volume": 1200},
                {"symbol": symbol, "datetime": f"{day} 11:00:00", "close": 10.14, "volume": 1300},
                {"symbol": symbol, "datetime": f"{day} 11:30:00", "close": 10.15, "volume": 1400},
                {"symbol": symbol, "datetime": f"{day} 13:00:00", "close": 10.16, "volume": 1500},
                {"symbol": symbol, "datetime": f"{day} 13:30:00", "close": 10.17, "volume": 1600},
                {"symbol": symbol, "datetime": f"{day} 14:00:00", "close": 10.18, "volume": 1700},
                {"symbol": symbol, "datetime": f"{day} 14:30:00", "close": 10.19, "volume": 1800},
                {"symbol": symbol, "datetime": f"{day} 15:00:00", "close": 10.20, "volume": 1900},
            ]
        if interface_name == "stock_zh_a_spot":
            return [
                {"symbol": "000001", "name": "PingAn", "price": 10.2},
                {"symbol": "000002", "name": "Vanke", "price": 9.8},
            ]
        if interface_name == "futures_zh_hist":
            return [
                {"symbol": "RB0", "date": "2024-01-02", "close": 3800},
                {"symbol": "RB0", "date": "2024-01-03", "close": 3810},
                {"symbol": "RB0", "date": "2024-01-04", "close": 3820},
            ]
        if interface_name == "macro_china_all":
            return [
                {"dataset": "macro_china_gdp", "date": "2024-03", "value": 5.3},
                {"dataset": "macro_china_cpi", "date": "2024-03", "value": 0.1},
                {"dataset": "macro_china_ppi", "date": "2024-03", "value": -2.8},
                {"dataset": "macro_china_pmi", "date": "2024-03", "value": 50.8},
                {"dataset": "macro_china_lpr", "date": "2024-03", "value": 3.45},
                {"dataset": "macro_china_money_supply", "date": "2024-03", "value": 8.3},
                {"dataset": "macro_china_new_financial_credit", "date": "2024-03", "value": 30900},
                {"dataset": "macro_china_fx_gold", "date": "2024-03", "value": 32457},
            ]
        return [{"interface": interface_name, "params": params}]


def _filter_by_symbol(records: list[dict[str, Any]], symbol: str) -> list[dict[str, Any]]:
    """按 代码/symbol 字段过滤记录"""
    sym = str(symbol).zfill(6)
    return [
        r for r in records
        if str(r.get("代码") or r.get("symbol", "")).zfill(6) == sym
    ]


def _stock_symbol_to_ts_code(symbol: str) -> str:
    """A股6位代码转 tushare ts_code：600xxx->SH，0/3xxx->SZ"""
    s = str(symbol).zfill(6)
    return f"{s}.SH" if s.startswith("6") else f"{s}.SZ"


def _get_tushare_pro():  # noqa: ANN202
    """获取 Tushare Pro API 实例，需设置 TUSHARE_TOKEN 环境变量。未捐赠账号有调用限制。"""
    token = os.environ.get("TUSHARE_TOKEN", "").strip()
    if not token:
        return None
    try:
        import tushare as ts  # type: ignore
        return ts.pro_api(token)
    except ImportError:
        return None


class AkshareBackend:
    def __init__(self) -> None:
        _patch_ssl_if_needed()
        import akshare as ak  # type: ignore

        self.ak = ak

    def _try_sources(self, fetchers: list[tuple[str, Any]], last_exc: Exception | None = None) -> Any:
        """依次尝试多个数据源，第一个成功即返回"""
        for name, fn in fetchers:
            try:
                result = fn() if callable(fn) else fn
                if result is not None and (not hasattr(result, "empty") or not result.empty):
                    return result
            except Exception as e:
                last_exc = e
        if last_exc:
            raise last_exc
        return []

    def fetch(self, interface_name: str, params: dict[str, Any]) -> BackendResult:
        method = getattr(self, f"_fetch_{interface_name}", None)
        if method is None:
            raise ValueError(f"Unsupported interface: {interface_name}")
        return BackendResult(rows=_normalize_result(method(params)))

    def _fetch_stock_zh_a_spot(self, params: dict[str, Any]) -> Any:
        symbol = params.get("symbol")

        def _em() -> Any:
            df = self.ak.stock_zh_a_spot_em()
            if symbol is None:
                return df
            rec = _normalize_result(df)
            return _filter_by_symbol(rec, symbol) or df

        def _sina() -> Any:
            df = self.ak.stock_zh_a_spot()
            if symbol is None:
                return df
            rec = _normalize_result(df)
            return _filter_by_symbol(rec, symbol) or df

        def _tushare() -> Any:
            """Tushare daily 作为行情备用：当日日线作为最新价。需 TUSHARE_TOKEN。"""
            pro = _get_tushare_pro()
            if pro is None:
                raise ValueError("TUSHARE_TOKEN not set")
            today = date.today().strftime("%Y%m%d")
            if symbol:
                ts_code = _stock_symbol_to_ts_code(symbol)
                df = pro.daily(ts_code=ts_code, trade_date=today)
            else:
                df = pro.daily(trade_date=today)
            if df is None or (hasattr(df, "empty") and df.empty):
                raise ValueError("Tushare daily returned empty")
            df = df.rename(columns={"trade_date": "日期", "vol": "成交量"})
            df["代码"] = df["ts_code"].str[:6]
            df["最新价"] = df["close"]
            df["涨跌幅"] = df.get("pct_chg")
            return df

        return self._try_sources([("em", _em), ("sina", _sina), ("tushare", _tushare)])

    def _fetch_stock_zh_a_hist(self, params: dict[str, Any]) -> Any:
        symbol = params["symbol"]
        period = params.get("period", "daily")
        if period in {"1m", "5m", "15m", "30m", "60m"}:
            return self.ak.stock_zh_a_hist_min_em(
                symbol=symbol,
                start_date=params.get("start_date"),
                end_date=params.get("end_date"),
                period=period.replace("m", ""),
                adjust=params.get("adjust", ""),
            )

        def _akshare() -> Any:
            return self.ak.stock_zh_a_hist(
                symbol=symbol,
                period=period,
                start_date=params.get("start_date"),
                end_date=params.get("end_date"),
                adjust=params.get("adjust", ""),
            )

        def _tushare() -> Any:
            """Tushare daily 作为日线备用。需 TUSHARE_TOKEN。"""
            pro = _get_tushare_pro()
            if pro is None:
                raise ValueError("TUSHARE_TOKEN not set")
            s = str(params.get("start_date") or "").replace("-", "")[:8]
            e = str(params.get("end_date") or "").replace("-", "")[:8]
            if not s or not e:
                from datetime import timedelta
                today = date.today()
                e = today.strftime("%Y%m%d")
                s = (today - timedelta(days=30)).strftime("%Y%m%d")
            ts_code = _stock_symbol_to_ts_code(symbol)
            df = pro.daily(ts_code=ts_code, start_date=s, end_date=e)
            if df is None or (hasattr(df, "empty") and df.empty):
                raise ValueError("Tushare daily returned empty")
            df = df.rename(columns={
                "trade_date": "日期", "open": "开盘", "close": "收盘",
                "high": "最高", "low": "最低", "vol": "成交量",
            })
            return df

        return self._try_sources([("akshare", _akshare), ("tushare", _tushare)])

    def _fetch_stock_intraday_em(self, params: dict[str, Any]) -> Any:
        return self.ak.stock_intraday_em(symbol=params["symbol"])

    def _fetch_stock_bid_ask_em(self, params: dict[str, Any]) -> Any:
        return self.ak.stock_bid_ask_em(symbol=params["symbol"])

    def _fetch_futures_zh_spot(self, params: dict[str, Any]) -> Any:
        import re

        symbol = params.get("symbol")
        market = params.get("market", "CF")
        adjust = params.get("adjust", "0")

        def _safe_spot(sym: str, mkt: str = "CF") -> Any:
            """调用 futures_zh_spot，捕获 AKShare 解析异常（如新浪返回格式异常）。"""
            try:
                return self.ak.futures_zh_spot(symbol=sym, market=mkt, adjust=adjust)
            except (IndexError, KeyError) as e:
                raise ValueError(
                    f"期货行情数据源返回异常 ({e.__class__.__name__})，请稍后重试"
                ) from e

        def _futures_symbol_to_ts_code(sym: str) -> str:
            """期货合约代码转 tushare ts_code：IF2606->IF2606.CFFEX, rb2505->RB2505.SHF"""
            sym_u = str(sym).strip().upper()
            m = re.match(r"^([A-Z]+)(\d*)", sym_u)
            if not m:
                raise ValueError(f"Invalid futures symbol: {sym}")
            var, num = m.group(1), m.group(2) or ""
            if len(var) >= 2:
                var = var[:2]
            mkt = self._FUTURES_SYMBOL_TO_MARKET.get(var)
            if not mkt:
                for k in sorted(self._FUTURES_SYMBOL_TO_MARKET.keys(), key=len, reverse=True):
                    if sym_u.startswith(k):
                        mkt = self._FUTURES_SYMBOL_TO_MARKET[k]
                        break
            if not mkt:
                raise ValueError(f"Unknown futures symbol: {sym}")
            suffix = self._TUSHARE_EXCHANGE_SUFFIX.get(mkt)
            if not suffix:
                raise ValueError(f"No Tushare suffix for {mkt}")
            return f"{var}{num}.{suffix}" if num else f"{var}.{suffix}"

        def _akshare_spot() -> Any:
            if symbol:
                if re.search(r"\d", str(symbol)):
                    return _safe_spot(symbol, market)
                try:
                    return self.ak.futures_zh_realtime(symbol=symbol)
                except (IndexError, KeyError) as e:
                    raise ValueError(
                        f"期货行情数据源返回异常 ({e.__class__.__name__})，请稍后重试"
                    ) from e
            for exch in ("cffex", "shfe", "dce"):
                try:
                    main = self.ak.match_main_contract(symbol=exch)
                    if main and isinstance(main, str):
                        first = (main.split(",")[0] if "," in main else main).strip()
                        if first:
                            return _safe_spot(first, "CF")
                except Exception:
                    pass
            yy = datetime.now().strftime("%y")
            for fallback in (f"IF{yy}06", f"rb{yy}05", f"au{yy}06", f"cu{yy}06"):
                try:
                    return _safe_spot(fallback, "CF")
                except ValueError:
                    continue
            raise ValueError("期货行情数据源暂时不可用，请稍后重试")

        def _tushare_spot() -> Any:
            """Tushare fut_daily 当日作为期货行情备用。需 TUSHARE_TOKEN。"""
            pro = _get_tushare_pro()
            if pro is None:
                raise ValueError("TUSHARE_TOKEN not set")
            today = date.today().strftime("%Y%m%d")
            contracts_to_try: list[str] = []
            if symbol and re.search(r"\d", str(symbol)):
                contracts_to_try = [str(symbol).strip()]
            else:
                for exch in ("cffex", "shfe", "dce"):
                    try:
                        main = self.ak.match_main_contract(symbol=exch)
                        if main and isinstance(main, str):
                            first = (main.split(",")[0] if "," in main else main).strip()
                            if first:
                                contracts_to_try.append(first)
                                break
                    except Exception:
                        pass
                if not contracts_to_try:
                    yy = datetime.now().strftime("%y")
                    contracts_to_try = [f"IF{yy}06", f"rb{yy}05", f"au{yy}06", f"cu{yy}06"]
            for sym in contracts_to_try:
                try:
                    ts_code = _futures_symbol_to_ts_code(sym)
                    df = pro.fut_daily(ts_code=ts_code, start_date=today, end_date=today)
                    if df is not None and not (hasattr(df, "empty") and df.empty):
                        df = df.rename(columns={"trade_date": "日期", "vol": "成交量"})
                        return df
                except Exception:
                    continue
            raise ValueError("期货行情数据源暂时不可用，请稍后重试")

        return self._try_sources([("akshare", _akshare_spot), ("tushare", _tushare_spot)])

    # 期货交易所 -> Tushare ts_code 后缀
    _TUSHARE_EXCHANGE_SUFFIX: dict[str, str] = {
        "SHFE": "SHF", "DCE": "DCE", "CZCE": "CZCE",
        "CFFEX": "CFFEX", "INE": "INE", "GFEX": "GFEX",
    }

    def _get_tushare_pro(self) -> Any:
        """返回 tushare pro_api 实例，未设置 TUSHARE_TOKEN 时返回 None。"""
        return _get_tushare_pro()

    # 期货合约代码 -> 交易所 (get_futures_daily 用)
    _FUTURES_SYMBOL_TO_MARKET: dict[str, str] = {
        "IF": "CFFEX", "IC": "CFFEX", "IH": "CFFEX", "IM": "CFFEX",
        "RB": "SHFE", "AU": "SHFE", "AG": "SHFE", "CU": "SHFE", "AL": "SHFE",
        "ZN": "SHFE", "PB": "SHFE", "NI": "SHFE", "SN": "SHFE", "RU": "SHFE",
        "HC": "SHFE", "SS": "SHFE", "SC": "INE", "FU": "SHFE", "BU": "SHFE",
        "PG": "DCE", "I": "DCE", "J": "DCE", "JM": "DCE", "C": "DCE",
        "CS": "DCE", "A": "DCE", "M": "DCE", "Y": "DCE", "P": "DCE",
        "L": "DCE", "V": "DCE", "PP": "DCE", "EG": "DCE", "EB": "DCE",
        "SR": "CZCE", "CF": "CZCE", "TA": "CZCE", "MA": "CZCE", "RM": "CZCE",
        "OI": "CZCE", "FG": "CZCE", "SF": "CZCE", "SM": "CZCE", "AP": "CZCE",
        "CJ": "CZCE", "UR": "CZCE", "SA": "CZCE", "PF": "CZCE", "PK": "CZCE",
        "SI": "GFEX", "LC": "GFEX", "BR": "INE",
    }

    # Tushare 交易所 -> ts_code 后缀（如 RB2505.SHF）
    _TUSHARE_EXCHANGE_SUFFIX: dict[str, str] = {
        "SHFE": "SHF", "DCE": "DCE", "CZCE": "CZCE",
        "CFFEX": "CFFEX", "INE": "INE", "GFEX": "GFEX",
    }

    def _get_tushare_pro(self) -> Any:
        """Tushare Pro API。需设置 TUSHARE_TOKEN，未捐赠账号有调用限制。"""
        token = os.environ.get("TUSHARE_TOKEN", "").strip()
        if not token:
            return None
        try:
            import tushare as ts  # noqa: PLC0415
            return ts.pro_api(token)
        except ImportError:
            return None

    def _fetch_futures_zh_hist(self, params: dict[str, Any]) -> Any:
        symbol = params["symbol"]
        period = params.get("period", "daily")
        if period in {"1m", "5m", "15m", "30m", "60m"}:
            return self._try_sources([("sina", lambda: self.ak.futures_zh_minute_sina(symbol=symbol, period=period))])
        start_date = params.get("start_date") or ""
        end_date = params.get("end_date") or ""
        for fmt in ("%Y-%m-%d", "%Y%m%d"):
            try:
                if start_date:
                    datetime.strptime(start_date[:10], fmt)
                if end_date:
                    datetime.strptime(end_date[:10], fmt)
            except ValueError:
                pass
        s = str(start_date).replace("-", "")[:8] if start_date else ""
        e = str(end_date).replace("-", "")[:8] if end_date else ""
        if not s or not e:
            from datetime import timedelta
            today = date.today()
            e = today.strftime("%Y%m%d")
            s = (today - timedelta(days=7)).strftime("%Y%m%d")  # 短期减轻请求量

        def _get_futures_daily() -> Any:
            import re
            sym_str = str(symbol).strip()
            m = re.match(r"^([a-zA-Z]+)\d*", sym_str)
            var = (m.group(1).upper() if m else sym_str.upper())
            if len(var) >= 2:
                var = var[:2]
            elif len(var) == 1:
                var = var  # e.g. I -> DCE
            market = self._FUTURES_SYMBOL_TO_MARKET.get(var)
            if not market:
                for k in sorted(self._FUTURES_SYMBOL_TO_MARKET.keys(), key=len, reverse=True):
                    if sym_str.upper().startswith(k):
                        market = self._FUTURES_SYMBOL_TO_MARKET[k]
                        break
            if not market:
                raise ValueError(f"Unknown futures symbol: {symbol}")
            df = self.ak.get_futures_daily(start_date=s, end_date=e, market=market)
            if df is None or (hasattr(df, "empty") and df.empty):
                raise ValueError("get_futures_daily returned empty")
            sym_lower = sym_str.lower()
            filter_pat = sym_lower
            if filter_pat.endswith("0") and len(filter_pat) <= 4:
                filter_pat = re.sub(r"0+$", "", filter_pat) or sym_lower[:-1]
            for col in ("symbol", "合约代码", "代码"):
                if col in df.columns:
                    df = df[df[col].astype(str).str.lower().str.contains(filter_pat, na=False)]
                    break
            if df is not None and hasattr(df, "empty") and not df.empty:
                return df
            raise ValueError("No matching symbol in get_futures_daily")

        def _tushare_fut_daily() -> Any:
            """Tushare fut_daily 备选，需 TUSHARE_TOKEN，未捐赠账号有调用限制。"""
            import re
            pro = self._get_tushare_pro()
            if pro is None:
                raise ValueError("TUSHARE_TOKEN not set")
            sym_str = str(symbol).strip().upper()
            m = re.match(r"^([A-Z]+)(\d*)", sym_str)
            if not m:
                raise ValueError(f"Invalid futures symbol: {symbol}")
            var, num = m.group(1), m.group(2) or ""
            if len(var) >= 2:
                var = var[:2]
            market = self._FUTURES_SYMBOL_TO_MARKET.get(var)
            if not market:
                for k in sorted(self._FUTURES_SYMBOL_TO_MARKET.keys(), key=len, reverse=True):
                    if sym_str.startswith(k):
                        market = self._FUTURES_SYMBOL_TO_MARKET[k]
                        break
            if not market:
                raise ValueError(f"Unknown futures symbol: {symbol}")
            suffix = self._TUSHARE_EXCHANGE_SUFFIX.get(market)
            if not suffix:
                raise ValueError(f"No Tushare suffix for {market}")
            ts_code = f"{var}{num}.{suffix}" if num else f"{var}.{suffix}"
            df = pro.fut_daily(ts_code=ts_code, start_date=s, end_date=e)
            if df is None or (hasattr(df, "empty") and df.empty):
                raise ValueError("Tushare fut_daily returned empty")
            if "trade_date" in df.columns and "date" not in df.columns:
                df = df.rename(columns={"trade_date": "date"})
            if "vol" in df.columns and "volume" not in df.columns:
                df = df.rename(columns={"vol": "volume"})
            return df

        # 日线：futures_daily / Tushare / sina / em（Tushare 需 TUSHARE_TOKEN，未捐赠有限制）
        fetchers_base = [
            ("futures_daily", _get_futures_daily),
            ("tushare", _tushare_fut_daily),
            ("sina", lambda: self.ak.futures_zh_daily_sina(symbol=symbol)),
            ("em", lambda: self.ak.futures_hist_em(symbol=symbol, period="daily")),
        ]
        if params.get("source") == "em":
            fetchers = [
                ("em", lambda: self.ak.futures_hist_em(symbol=symbol, period="daily")),
                ("futures_daily", _get_futures_daily),
                ("tushare", _tushare_fut_daily),
                ("sina", lambda: self.ak.futures_zh_daily_sina(symbol=symbol)),
            ]
        else:
            fetchers = fetchers_base
        return self._try_sources(fetchers)

    # 主力合约静态回退（新浪 API 返回 HTML 时使用）
    _MAIN_CONTRACT_FALLBACK: dict[str, str] = {
        "cffex": "IF2504,IC2504,IH2504,IM2504",
        "shfe": "rb2505,au2506,ag2506,cu2506",
        "dce": "i2505,j2505,jm2505",
        "czce": "TA505,MA505,RM505",
        "gfex": "si2506",
    }

    def _fetch_match_main_contract(self, params: dict[str, Any]) -> Any:
        symbol = str(params.get("symbol") or params.get("exchange") or "cffex").lower()

        def _sina() -> Any:
            raw = self.ak.match_main_contract(symbol=symbol)
            return [{"symbol": symbol, "contracts": raw}] if raw else None

        def _fallback() -> Any:
            fallback = self._MAIN_CONTRACT_FALLBACK.get(symbol)
            if fallback:
                return [{"symbol": symbol, "contracts": fallback, "_source": "fallback"}]
            return [{"symbol": symbol, "contracts": "", "_source": "fallback"}]

        return self._try_sources([
            ("sina", _sina),
            ("fallback", _fallback),
        ])

    def _fetch_futures_basis(self, params: dict[str, Any]) -> Any:
        if params.get("mode") == "sys":
            return self.ak.futures_spot_sys(symbol=params.get("symbol", "RU"))
        return self.ak.futures_spot_price(date=params.get("date"))

    def _fetch_fund_meta(self, params: dict[str, Any]) -> Any:
        if params.get("mode") == "purchase":
            return self.ak.fund_purchase_em()
        return self.ak.fund_name_em()

    def _fetch_fund_etf_market(self, params: dict[str, Any]) -> Any:
        if params.get("mode") == "hist":
            return self._try_sources(
                [
                    (
                        "em",
                        lambda: self.ak.fund_etf_hist_em(
                            symbol=params["symbol"],
                            period=params.get("period", "daily"),
                            start_date=params.get("start_date"),
                            end_date=params.get("end_date"),
                            adjust=params.get("adjust", ""),
                        ),
                    ),
                ]
            )
        return self._try_sources(
            [
                ("em", lambda: self.ak.fund_etf_spot_em()),
                ("ths", lambda: self.ak.fund_etf_spot_ths(date="")),
            ]
        )

    def _fetch_fund_open_info(self, params: dict[str, Any]) -> Any:
        symbol = params.get("symbol") or params.get("fund")
        if not symbol:
            raise ValueError("fund_open_info 需要 symbol 或 fund 参数")
        # 仅传递 akshare 接受的参数，避免传入 fund 导致报错
        return self.ak.fund_open_fund_info_em(
            symbol=str(symbol),
            indicator=str(params.get("indicator", "单位净值走势")),
        )

    _MACRO_SHORTHAND: dict[str, str] = {
        "gdp": "macro_china_gdp",
        "cpi": "macro_china_cpi",
        "ppi": "macro_china_ppi",
        "pmi": "macro_china_pmi",
        "pm": "macro_china_pmi",
        "lpr": "macro_china_lpr",
        "money_supply": "macro_china_money_supply",
        "credit": "macro_china_new_financial_credit",
        "fx_gold": "macro_china_fx_gold",
    }

    def _normalize_macro_datasets(self, raw: Any) -> tuple[str, ...]:
        """Convert datasets param (string or list) to full akshare method names."""
        if raw is None:
            return MACRO_DATASETS
        if isinstance(raw, str):
            parts = [p.strip() for p in raw.split(",") if p.strip()]
        elif isinstance(raw, (list, tuple)):
            parts = [str(p).strip() for p in raw if p]
        else:
            return MACRO_DATASETS
        if not parts:
            return MACRO_DATASETS
        result: list[str] = []
        for p in parts:
            if p.startswith("macro_china_"):
                result.append(p)
            else:
                result.append(self._MACRO_SHORTHAND.get(p.lower(), f"macro_china_{p}"))
        return tuple(result)

    def _fetch_macro_china_all(self, params: dict[str, Any]) -> Any:
        dataset_names = self._normalize_macro_datasets(params.get("datasets"))
        rows: list[dict[str, Any]] = []
        for dataset_name in dataset_names:
            fetcher = getattr(self.ak, dataset_name, None)
            if fetcher is None:
                continue
            rows.extend(_tag_rows(dataset_name, _normalize_result(fetcher())))
        return rows

    # Mapping from common futures/English codes to the Chinese commodity names
    # that akshare's spot_price_qh() and futures_spot_sys() expect.
    _COMMODITY_SYMBOL_MAP: dict[str, str] = {
        # futures codes (upper / lower)
        "CU": "铜", "cu": "铜",
        "AL": "铝", "al": "铝",
        "ZN": "锌", "zn": "锌",
        "PB": "铅", "pb": "铅",
        "NI": "镍", "ni": "镍",
        "SN": "锡", "sn": "锡",
        "AU": "黄金", "au": "黄金",
        "AG": "白银", "ag": "白银",
        "RU": "橡胶", "ru": "橡胶",
        "RB": "螺纹钢", "rb": "螺纹钢",
        "I": "铁矿石", "i": "铁矿石",
        "J": "焦炭", "j": "焦炭",
        "JM": "焦煤", "jm": "焦煤",
        "HC": "热卷", "hc": "热卷",
        "SS": "不锈钢", "ss": "不锈钢",
        "SC": "原油", "sc": "原油",
        "FU": "燃料油", "fu": "燃料油",
        "PG": "LPG", "pg": "LPG",
        "C": "玉米", "c": "玉米",
        "CS": "淀粉", "cs": "淀粉",
        "A": "大豆", "a": "大豆",
        "M": "豆粕", "m": "豆粕",
        "Y": "豆油", "y": "豆油",
        "P": "棕榈油", "p": "棕榈油",
        "RM": "菜粕", "rm": "菜粕",
        "OI": "菜油", "oi": "菜油",
        "SR": "白糖", "sr": "白糖",
        "CF": "棉花", "cf": "棉花",
        "TA": "PTA", "ta": "PTA",
        "MA": "甲醇", "ma": "甲醇",
        "L": "聚乙烯", "l": "聚乙烯",
        "PP": "聚丙烯", "pp": "聚丙烯",
        "V": "PVC", "v": "PVC",
    }

    def _resolve_commodity_symbol(self, raw: str | None, default: str) -> str:
        """Convert a futures code to the Chinese name expected by spot_price_qh."""
        if not raw:
            return default
        return self._COMMODITY_SYMBOL_MAP.get(raw.upper(), raw)

    def _fetch_commodity_basis(self, params: dict[str, Any]) -> Any:
        mode = params.get("mode", "")
        if mode == "futures_spot_price":
            return self.ak.futures_spot_price(date=params.get("date"))
        if mode == "futures_spot_sys":
            symbol = self._resolve_commodity_symbol(params.get("symbol"), "RU")
            raw = params.get("symbol", "RU")
            return self.ak.futures_spot_sys(symbol=raw)
        date = params.get("date")
        if date:
            return self.ak.futures_spot_price(date=date)
        # 无 date 时：spot_price_qh 依赖外部 token(_pcc) 可能失效，
        # 优先用 futures_spot_price 获取当日全市场快照
        try:
            chinese_name = self._resolve_commodity_symbol(params.get("symbol"), "铜")
            return self.ak.spot_price_qh(symbol=chinese_name)
        except (KeyError, Exception):
            from datetime import date as date_type

            return self.ak.futures_spot_price(date=date_type.today().isoformat())

    # Mapping from user-supplied aliases to the SGE symbol format.
    _SGE_SYMBOL_MAP: dict[str, str] = {
        "AU9999": "Au99.99", "au9999": "Au99.99",
        "AU995": "Au99.5",  "au995": "Au99.5",
        "AUTD": "Au(T+D)", "autd": "Au(T+D)",
        "AU": "Au99.99",   "au": "Au99.99",
        "AG9999": "Ag99.99", "ag9999": "Ag99.99",
        "AGTD": "Ag(T+D)", "agtd": "Ag(T+D)",
        "AG": "Ag99.99",   "ag": "Ag99.99",
        "黄金": "Au99.99",
        "白银": "Ag99.99",
    }

    def _resolve_sge_symbol(self, raw: str | None) -> str:
        if not raw:
            return "Au99.99"
        return self._SGE_SYMBOL_MAP.get(raw, self._SGE_SYMBOL_MAP.get(raw.upper(), raw))

    def _fetch_spot_sge(self, params: dict[str, Any]) -> Any:
        if params.get("mode") == "hist":
            symbol = self._resolve_sge_symbol(params.get("symbol"))
            return self.ak.spot_hist_sge(symbol=symbol)
        symbol = self._resolve_sge_symbol(params.get("symbol"))
        return self.ak.spot_quotations_sge(symbol=symbol)

    def _fetch_bond_zh_hs_market(self, params: dict[str, Any]) -> Any:
        if params.get("mode") == "hist":
            return self._try_sources([("sina", lambda: self.ak.bond_zh_hs_daily(symbol=params["symbol"]))])
        return self._try_sources(
            [
                ("sina_full", lambda: self.ak.bond_zh_hs_spot()),
                ("sina_short", lambda: self.ak.bond_zh_hs_spot(start_page="1", end_page="3")),
                ("bank_quote", lambda: self.ak.bond_spot_quote()),
            ]
        )

    def _fetch_bond_zh_hs_cov_market(self, params: dict[str, Any]) -> Any:
        if params.get("mode") == "hist":
            return self._try_sources([
                ("sina", lambda: self.ak.bond_zh_hs_cov_daily(symbol=params["symbol"])),
            ])

        def _tushare_cb_basic() -> Any:
            pro = self._get_tushare_pro()
            if pro is None:
                raise ValueError("TUSHARE_TOKEN not set")
            df = pro.cb_basic()
            if df is None or (hasattr(df, "empty") and df.empty):
                raise ValueError("Tushare cb_basic returned empty")
            return df

        return self._try_sources(
            [
                ("sina", lambda: self.ak.bond_zh_hs_cov_spot()),
                ("em_cov", lambda: self.ak.bond_zh_cov()),
                ("em_comparison", lambda: self.ak.bond_cov_comparison()),
                ("tushare_cb", _tushare_cb_basic),
            ]
        )

    def _fetch_bond_cb_meta(self, params: dict[str, Any]) -> Any:
        if params.get("mode") == "summary":
            return self.ak.bond_cb_summary_sina()
        return self.ak.bond_cb_profile_sina(symbol=params["symbol"])

    def _fetch_stock_board_industry(self, params: dict[str, Any]) -> Any:
        if params.get("mode") == "hist":
            return self._try_sources(
                [
                    (
                        "em",
                        lambda: self.ak.stock_board_industry_hist_em(
                            symbol=params["symbol"],
                            start_date=params.get("start_date"),
                            end_date=params.get("end_date"),
                            period=params.get("period", "daily"),
                            adjust=params.get("adjust", ""),
                        ),
                    ),
                ]
            )
        return self._try_sources(
            [
                ("em", lambda: self.ak.stock_board_industry_name_em()),
                ("ths", lambda: self.ak.stock_board_industry_name_ths()),
            ]
        )

    def _fetch_stock_board_concept(self, params: dict[str, Any]) -> Any:
        if params.get("mode") == "hist":
            return self._try_sources(
                [
                    (
                        "em",
                        lambda: self.ak.stock_board_concept_hist_em(
                            symbol=params["symbol"],
                            start_date=params.get("start_date"),
                            end_date=params.get("end_date"),
                            period=params.get("period", "daily"),
                            adjust=params.get("adjust", ""),
                        ),
                    ),
                ]
            )
        return self._try_sources(
            [
                ("em", lambda: self.ak.stock_board_concept_name_em()),
                ("ths", lambda: self.ak.stock_board_concept_name_ths()),
            ]
        )


def create_backend(test_mode: bool):
    return StubBackend() if test_mode else AkshareBackend()
