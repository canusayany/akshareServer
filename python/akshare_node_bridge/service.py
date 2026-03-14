from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .backend import create_backend
from .cache import SqliteCache
from .calendar import is_same_day
from .limiter import reduce_rows_evenly


SUPPORTED_INTERFACES = {
    "stock_zh_a_spot",
    "stock_zh_a_hist",
    "stock_intraday_em",
    "stock_bid_ask_em",
    "futures_zh_spot",
    "futures_zh_hist",
    "match_main_contract",
    "futures_basis",
    "fund_meta",
    "fund_etf_market",
    "fund_open_info",
    "macro_china_all",
    "commodity_basis",
    "spot_sge",
    "bond_zh_hs_market",
    "bond_zh_hs_cov_market",
    "bond_cb_meta",
    "stock_board_industry",
    "stock_board_concept",
}


class BridgeService:
    def __init__(self, db_path: str | Path, max_bytes: int = 2000, test_mode: bool = False) -> None:
        self.cache = SqliteCache(db_path)
        self.max_bytes = int(max_bytes)
        self.backend = create_backend(test_mode=test_mode)

    def handle(self, interface_name: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if interface_name not in SUPPORTED_INTERFACES:
            raise ValueError(f"Unsupported interface: {interface_name}")

        normalized_params = self._normalize_params(params or {})
        request_key = self._build_request_key(interface_name, normalized_params)
        cached = self.cache.get(request_key)
        if cached is not None:
            limited = self._limit_rows(interface_name, normalized_params, cached.payload["rows"])
            return self._success_response(interface_name, normalized_params, limited, cache_hit=True)

        backend_result = self.backend.fetch(interface_name, normalized_params)
        self.cache.set(interface_name, request_key, {"rows": backend_result.rows})
        limited = self._limit_rows(interface_name, normalized_params, backend_result.rows)
        return self._success_response(interface_name, normalized_params, limited, cache_hit=False)

    def _normalize_params(self, params: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in sorted(params.items(), key=lambda item: item[0]) if value is not None}

    def _build_request_key(self, interface_name: str, params: dict[str, Any]) -> str:
        key_payload = json.dumps(
            {"interface": interface_name, "params": params, "max_bytes": self.max_bytes},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(key_payload.encode("utf-8")).hexdigest()

    def _limit_rows(self, interface_name: str, params: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
        apply_cn_half_hour_filter = (
            interface_name == "stock_zh_a_hist"
            and params.get("symbol") is not None
            and params.get("period") in {"1m", "5m", "15m", "30m", "60m"}
            and is_same_day(params.get("start_date"), params.get("end_date"))
        )
        return reduce_rows_evenly(rows=rows, max_bytes=self.max_bytes, apply_cn_half_hour_filter=apply_cn_half_hour_filter)

    def _success_response(
        self,
        interface_name: str,
        params: dict[str, Any],
        limited: dict[str, Any],
        cache_hit: bool,
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "interface": interface_name,
            "params": params,
            "cache_hit": cache_hit,
            "estimated_row_bytes": limited["estimated_row_bytes"],
            "max_rows": limited["max_rows"],
            "requested_rows": limited["requested_rows"],
            "returned_rows": limited["returned_rows"],
            "sampling_step": limited["sampling_step"],
            "rows": limited["rows"],
        }
