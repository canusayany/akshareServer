from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import math
from typing import Any


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


class AkshareBackend:
    def __init__(self) -> None:
        import akshare as ak  # type: ignore

        self.ak = ak

    def fetch(self, interface_name: str, params: dict[str, Any]) -> BackendResult:
        method = getattr(self, f"_fetch_{interface_name}", None)
        if method is None:
            raise ValueError(f"Unsupported interface: {interface_name}")
        return BackendResult(rows=_normalize_result(method(params)))

    def _fetch_stock_zh_a_spot(self, params: dict[str, Any]) -> Any:
        df = self.ak.stock_zh_a_spot_em()
        symbol = params.get("symbol")
        if symbol is None:
            return df
        records = _normalize_result(df)
        return [row for row in records if str(row.get("代码") or row.get("symbol")) == str(symbol)]

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
        return self.ak.stock_zh_a_hist(
            symbol=symbol,
            period=period,
            start_date=params.get("start_date"),
            end_date=params.get("end_date"),
            adjust=params.get("adjust", ""),
        )

    def _fetch_stock_intraday_em(self, params: dict[str, Any]) -> Any:
        return self.ak.stock_intraday_em(symbol=params["symbol"])

    def _fetch_stock_bid_ask_em(self, params: dict[str, Any]) -> Any:
        return self.ak.stock_bid_ask_em(symbol=params["symbol"])

    def _fetch_futures_zh_spot(self, params: dict[str, Any]) -> Any:
        symbol = params.get("symbol")
        if symbol:
            return self.ak.futures_zh_realtime(symbol=symbol)
        return self.ak.futures_zh_spot(symbol=params.get("market", "FF"), adjust=params.get("adjust", "0"))

    def _fetch_futures_zh_hist(self, params: dict[str, Any]) -> Any:
        symbol = params["symbol"]
        period = params.get("period", "daily")
        if period in {"1m", "5m", "15m", "30m", "60m"}:
            return self.ak.futures_zh_minute_sina(symbol=symbol, period=period)
        if params.get("source") == "em":
            return self.ak.futures_hist_em(symbol=symbol, period="daily")
        return self.ak.futures_zh_daily_sina(symbol=symbol)

    def _fetch_match_main_contract(self, params: dict[str, Any]) -> Any:
        symbol = params.get("symbol") or params.get("exchange") or "cffex"
        return [{"symbol": symbol, "contracts": self.ak.match_main_contract(symbol=symbol)}]

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
            return self.ak.fund_etf_hist_em(
                symbol=params["symbol"],
                period=params.get("period", "daily"),
                start_date=params.get("start_date"),
                end_date=params.get("end_date"),
                adjust=params.get("adjust", ""),
            )
        return self.ak.fund_etf_spot_em()

    def _fetch_fund_open_info(self, params: dict[str, Any]) -> Any:
        return self.ak.fund_open_fund_info_em(
            fund=params["symbol"],
            indicator=params.get("indicator", "单位净值走势"),
        )

    def _fetch_macro_china_all(self, params: dict[str, Any]) -> Any:
        dataset_names = params.get("datasets") or MACRO_DATASETS
        rows: list[dict[str, Any]] = []
        for dataset_name in dataset_names:
            fetcher = getattr(self.ak, dataset_name, None)
            if fetcher is None:
                continue
            rows.extend(_tag_rows(dataset_name, _normalize_result(fetcher())))
        return rows

    def _fetch_commodity_basis(self, params: dict[str, Any]) -> Any:
        mode = params.get("mode", "spot_price_qh")
        if mode == "futures_spot_price":
            return self.ak.futures_spot_price(date=params.get("date"))
        if mode == "futures_spot_sys":
            return self.ak.futures_spot_sys(symbol=params.get("symbol", "RU"))
        return self.ak.spot_price_qh(symbol=params.get("symbol", "RU"))

    def _fetch_spot_sge(self, params: dict[str, Any]) -> Any:
        if params.get("mode") == "hist":
            return self.ak.spot_hist_sge(symbol=params["symbol"])
        return self.ak.spot_quotations_sge(symbol=params.get("symbol", "Au99.99"))

    def _fetch_bond_zh_hs_market(self, params: dict[str, Any]) -> Any:
        if params.get("mode") == "hist":
            return self.ak.bond_zh_hs_daily(symbol=params["symbol"])
        return self.ak.bond_zh_hs_spot()

    def _fetch_bond_zh_hs_cov_market(self, params: dict[str, Any]) -> Any:
        if params.get("mode") == "hist":
            return self.ak.bond_zh_hs_cov_daily(symbol=params["symbol"])
        return self.ak.bond_zh_hs_cov_spot()

    def _fetch_bond_cb_meta(self, params: dict[str, Any]) -> Any:
        if params.get("mode") == "summary":
            return self.ak.bond_cb_summary_sina()
        return self.ak.bond_cb_profile_sina(symbol=params["symbol"])

    def _fetch_stock_board_industry(self, params: dict[str, Any]) -> Any:
        if params.get("mode") == "hist":
            return self.ak.stock_board_industry_hist_em(
                symbol=params["symbol"],
                start_date=params.get("start_date"),
                end_date=params.get("end_date"),
                period=params.get("period", "daily"),
                adjust=params.get("adjust", ""),
            )
        return self.ak.stock_board_industry_name_em()

    def _fetch_stock_board_concept(self, params: dict[str, Any]) -> Any:
        if params.get("mode") == "hist":
            return self.ak.stock_board_concept_hist_em(
                symbol=params["symbol"],
                start_date=params.get("start_date"),
                end_date=params.get("end_date"),
                period=params.get("period", "daily"),
                adjust=params.get("adjust", ""),
            )
        return self.ak.stock_board_concept_name_em()


def create_backend(test_mode: bool):
    return StubBackend() if test_mode else AkshareBackend()
