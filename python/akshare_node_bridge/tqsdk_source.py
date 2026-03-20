from __future__ import annotations

import os
import time
from typing import Any, Optional

from .logger import get_logger


LOGGER = get_logger()


class TqSdkDataSource:
    """
    天勤 SDK 期货期权数据源。
    优先级：TqSdk > AkShare > 其他源
    """

    def __init__(self) -> None:
        self.api: Optional[Any] = None
        self.username = os.environ.get("TQSDK_USERNAME", "").strip()
        self.password = os.environ.get("TQSDK_PASSWORD", "").strip()
        self.enabled = bool(self.username and self.password)
        self.logger = LOGGER

    def _ensure_connected(self) -> bool:
        """确保 TqApi 已连接。"""
        if not self.enabled:
            self.logger.debug("TqSdk disabled: missing TQSDK_USERNAME or TQSDK_PASSWORD")
            return False

        if self.api is not None:
            return True

        try:
            from tqsdk import TqApi, TqAuth

            self.api = TqApi(auth=TqAuth(self.username, self.password))
            self.logger.info("TqSdk connected successfully")
            return True
        except Exception as e:
            self.logger.warning("Failed to connect TqSdk: %s", str(e))
            self.enabled = False
            return False

    def fetch_futures_spot(self, symbol: str, timeout: float = 10.0) -> Optional[dict[str, Any]]:
        """
        获取期货实时行情。
        symbol: 标准格式如 'SHFE.au' 或 'KQ.m@SHFE.au'
        返回包含 last_price, ask_price1, bid_price1 等字段的字典
        """
        if not self._ensure_connected():
            return None

        try:
            quote = self.api.get_quote(symbol)
            deadline = time.time() + timeout
            while time.time() < deadline:
                if getattr(quote, "datetime", ""):
                    return self._quote_to_dict(quote)
                self.api.wait_update(deadline=deadline)
            self.logger.warning("fetch_futures_spot timeout for symbol=%s after %.1f seconds", symbol, timeout)
            return None
        except Exception as e:
            self.logger.warning("fetch_futures_spot failed for symbol=%s: %s", symbol, str(e))
            return None

    def fetch_futures_klines(
        self,
        symbol: str,
        duration: int = 60,
        data_length: int = 100,
        timeout: float = 10.0,
    ) -> Optional[list[dict[str, Any]]]:
        """
        获取期货 K 线数据。
        symbol: 标准格式如 'SHFE.au2504'
        duration: K 线周期（秒），如 60（1分钟）、3600（1小时）、86400（1天）
        data_length: 返回条数，最多 10000
        """
        if not self._ensure_connected():
            return None

        try:
            klines = self.api.get_kline_serial(symbol, duration, data_length=data_length)
            deadline = time.time() + timeout

            while time.time() < deadline:
                if int(klines.iloc[-1]["datetime"]) > 0:
                    return self._klines_to_list(klines)
                self.api.wait_update(deadline=deadline)

            self.logger.warning("fetch_futures_klines timeout for symbol=%s after %.1f seconds", symbol, timeout)
            return None
        except Exception as e:
            self.logger.warning("fetch_futures_klines failed for symbol=%s: %s", symbol, str(e))
            return None

    def fetch_futures_ticks(
        self,
        symbol: str,
        data_length: int = 100,
        timeout: float = 10.0,
    ) -> Optional[list[dict[str, Any]]]:
        """
        获取期货 Tick 数据。
        symbol: 标准格式如 'SHFE.au2504'
        data_length: 返回条数，最多 10000
        """
        if not self._ensure_connected():
            return None

        try:
            ticks = self.api.get_tick_serial(symbol, data_length=data_length)
            deadline = time.time() + timeout

            while time.time() < deadline:
                if int(ticks.iloc[-1]["datetime"]) > 0:
                    return self._ticks_to_list(ticks)
                self.api.wait_update(deadline=deadline)

            self.logger.warning("fetch_futures_ticks timeout for symbol=%s after %.1f seconds", symbol, timeout)
            return None
        except Exception as e:
            self.logger.warning("fetch_futures_ticks failed for symbol=%s: %s", symbol, str(e))
            return None

    def query_symbols(self, ins_class: Optional[str] = None, timeout: float = 10.0) -> Optional[list[dict[str, Any]]]:
        """
        查询合约列表。
        ins_class: 如 'FUTURE'、'OPTION' 等，如果为空则返回所有
        """
        if not self._ensure_connected():
            return None

        try:
            symbols = self.api.query_symbol_info()
            deadline = time.time() + timeout

            while time.time() < deadline:
                self.api.wait_update(deadline=deadline)

            result = []
            for symbol, info in symbols.items():
                if ins_class and getattr(info, "ins_class", "") != ins_class:
                    continue
                result.append(self._symbol_info_to_dict(symbol, info))
            return result
        except Exception as e:
            self.logger.warning("query_symbols failed: %s", str(e))
            return None

    def close(self) -> None:
        """关闭连接。"""
        if self.api is not None:
            try:
                self.api.close()
                self.api = None
                self.logger.info("TqSdk connection closed")
            except Exception as e:
                self.logger.warning("Error closing TqSdk: %s", str(e))

    @staticmethod
    def _quote_to_dict(quote: Any) -> dict[str, Any]:
        """将 Quote 对象转换为字典。"""
        return {
            "datetime": getattr(quote, "datetime", ""),
            "last_price": getattr(quote, "last_price", None),
            "ask_price1": getattr(quote, "ask_price1", None),
            "bid_price1": getattr(quote, "bid_price1", None),
            "bid_price2": getattr(quote, "bid_price2", None),
            "bid_price3": getattr(quote, "bid_price3", None),
            "bid_price4": getattr(quote, "bid_price4", None),
            "bid_price5": getattr(quote, "bid_price5", None),
            "ask_price2": getattr(quote, "ask_price2", None),
            "ask_price3": getattr(quote, "ask_price3", None),
            "ask_price4": getattr(quote, "ask_price4", None),
            "ask_price5": getattr(quote, "ask_price5", None),
            "bid_volume1": getattr(quote, "bid_volume1", None),
            "bid_volume2": getattr(quote, "bid_volume2", None),
            "bid_volume3": getattr(quote, "bid_volume3", None),
            "bid_volume4": getattr(quote, "bid_volume4", None),
            "bid_volume5": getattr(quote, "bid_volume5", None),
            "ask_volume1": getattr(quote, "ask_volume1", None),
            "ask_volume2": getattr(quote, "ask_volume2", None),
            "ask_volume3": getattr(quote, "ask_volume3", None),
            "ask_volume4": getattr(quote, "ask_volume4", None),
            "ask_volume5": getattr(quote, "ask_volume5", None),
            "volume": getattr(quote, "volume", None),
            "open_interest": getattr(quote, "open_interest", None),
            "high": getattr(quote, "high", None),
            "low": getattr(quote, "low", None),
            "open": getattr(quote, "open", None),
            "close": getattr(quote, "close", None),
            "price_tick": getattr(quote, "price_tick", None),
            "volume_multiple": getattr(quote, "volume_multiple", None),
            "instrument_name": getattr(quote, "instrument_name", ""),
            "ins_class": getattr(quote, "ins_class", ""),
            "expired": getattr(quote, "expired", False),
            "underlying_symbol": getattr(quote, "underlying_symbol", ""),
        }

    @staticmethod
    def _klines_to_list(klines: Any) -> list[dict[str, Any]]:
        """将 K 线 DataFrame 转换为字典列表。"""
        result = []
        for index, row in klines.iterrows():
            result.append({
                "datetime": int(row["datetime"]),
                "open": float(row["open"]) if row["open"] else None,
                "high": float(row["high"]) if row["high"] else None,
                "low": float(row["low"]) if row["low"] else None,
                "close": float(row["close"]) if row["close"] else None,
                "volume": int(row["volume"]) if row["volume"] else None,
                "open_oi": int(row["open_oi"]) if row.get("open_oi") else None,
                "close_oi": int(row["close_oi"]) if row.get("close_oi") else None,
            })
        return result

    @staticmethod
    def _ticks_to_list(ticks: Any) -> list[dict[str, Any]]:
        """将 Tick DataFrame 转换为字典列表。"""
        result = []
        for index, row in ticks.iterrows():
            result.append({
                "datetime": int(row["datetime"]),
                "last_price": float(row["last_price"]) if row["last_price"] else None,
                "ask_price1": float(row["ask_price1"]) if row.get("ask_price1") else None,
                "bid_price1": float(row["bid_price1"]) if row.get("bid_price1") else None,
                "highest": float(row["highest"]) if row.get("highest") else None,
                "lowest": float(row["lowest"]) if row.get("lowest") else None,
                "volume": int(row["volume"]) if row["volume"] else None,
                "amount": float(row["amount"]) if row.get("amount") else None,
                "open_interest": int(row["open_interest"]) if row.get("open_interest") else None,
            })
        return result

    @staticmethod
    def _symbol_info_to_dict(symbol: str, info: Any) -> dict[str, Any]:
        """将合约信息对象转换为字典。"""
        return {
            "symbol": symbol,
            "instrument_name": getattr(info, "instrument_name", ""),
            "ins_class": getattr(info, "ins_class", ""),
            "exchange_id": getattr(info, "exchange_id", ""),
            "price_tick": getattr(info, "price_tick", None),
            "volume_multiple": getattr(info, "volume_multiple", None),
            "expired": getattr(info, "expired", False),
            "underlying_symbol": getattr(info, "underlying_symbol", ""),
        }
