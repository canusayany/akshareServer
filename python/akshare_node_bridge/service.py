from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .backend import _compact_row_keys, create_backend
from .cache import SqliteCache
from .calendar import is_same_day, is_trading_day, parse_datetime_like, split_date_range_by_month
from .limiter import extract_row_datetime, reduce_rows_evenly
from .params_guard import normalize_params as normalize_params_llm, validate_required


SUPPORTED_INTERFACES = {
    "stock_zh_a_spot",
    "stock_zh_a_hist",
    "stock_intraday_em",
    "stock_bid_ask_em",
    "stock_index_zh_hist",
    "stock_financial_abstract",
    "stock_yjbb_em",
    "stock_yjyg_em",
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
    "option_finance_board",
    "option_current_em",
    "option_sse_daily_sina",
    "option_commodity_hist",
}

# 支持按日期分片、差额补齐的接口（须有 start_date、end_date 参数）
INTERFACES_WITH_DATE_RANGE = frozenset({
    "stock_zh_a_hist",
    "stock_index_zh_hist",
    "futures_zh_hist",
    "fund_etf_market",
    "stock_board_industry",
    "stock_board_concept",
})

# 与交易日相关的接口：单日查询时，非交易日返回空数据+message
DATE_SENSITIVE_INTERFACES = frozenset({
    "stock_zh_a_spot",
    "stock_zh_a_hist",
    "stock_index_zh_hist",
    "futures_zh_spot",
    "futures_zh_hist",
})


def _sort_rows_by_datetime(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按时间字段对行排序，无时间字段的排在末尾。"""
    def key_fn(row: dict[str, Any]):
        dt = extract_row_datetime(row)
        return (0, dt) if dt else (1, None)
    return sorted(rows, key=key_fn)


class BridgeService:
    def __init__(self, db_path: str | Path, max_bytes: int = 2000, test_mode: bool = False) -> None:
        self.cache = SqliteCache(db_path)
        self.max_bytes = int(max_bytes)
        self.backend = create_backend(test_mode=test_mode)

    def handle(self, interface_name: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if interface_name not in SUPPORTED_INTERFACES:
            raise ValueError(f"Unsupported interface: {interface_name}")

        # LLM 防护：参数规范化与必填校验
        normalized_params = normalize_params_llm(params, interface_name)
        ok, err = validate_required(interface_name, normalized_params)
        if not ok and err:
            raise ValueError(err)
        normalized_params = self._normalize_params(normalized_params)

        # 非交易日检查：单日查询时，非交易日直接返回空数据+message
        if interface_name in DATE_SENSITIVE_INTERFACES:
            check_date = None
            if interface_name in ("stock_zh_a_spot", "futures_zh_spot"):
                from datetime import date as d
                check_date = d.today()
            elif interface_name in ("stock_zh_a_hist", "stock_index_zh_hist", "futures_zh_hist"):
                start_d = parse_datetime_like(normalized_params.get("start_date"))
                end_d = parse_datetime_like(normalized_params.get("end_date"))
                if start_d and end_d and start_d.date() == end_d.date():
                    check_date = start_d.date()
            if check_date is not None and not is_trading_day(check_date):
                limited = self._limit_rows(interface_name, normalized_params, [])
                return {
                    "ok": True,
                    "interface": interface_name,
                    "params": normalized_params,
                    "cache_hit": False,
                    "message": "非交易日",
                    "estimated_row_bytes": limited["estimated_row_bytes"],
                    "max_rows": limited["max_rows"],
                    "requested_rows": 0,
                    "returned_rows": 0,
                    "sampling_step": 1,
                    "rows": [],
                }
        # 支持日期分片的接口：优先查分片缓存，缺失部分再调接口补齐
        use_incremental = (
            interface_name in INTERFACES_WITH_DATE_RANGE
            and normalized_params.get("start_date")
            and normalized_params.get("end_date")
        )
        # fund_etf_market / stock_board_* 需 mode=hist 才使用 start_date/end_date
        if use_incremental and interface_name in ("fund_etf_market", "stock_board_industry", "stock_board_concept"):
            use_incremental = normalized_params.get("mode") == "hist"
        if use_incremental:
            return self._handle_with_incremental_cache(interface_name, normalized_params)

        # 其余接口：全量缓存
        request_key = self._build_request_key(interface_name, normalized_params)
        cached = self.cache.get(request_key)
        if cached is not None:
            limited = self._limit_rows(interface_name, normalized_params, cached.payload["rows"])
            return self._success_response(interface_name, normalized_params, limited, cache_hit=True)

        try:
            backend_result = self.backend.fetch(interface_name, normalized_params)
        except Exception as e:
            msg = str(e)
            if "not set" in msg.lower() or "token" in msg.lower():
                raise ValueError(f"数据源配置缺失: {msg}")
            if "returned empty" in msg.lower() or "empty" in msg.lower():
                raise ValueError(f"数据源暂无数据: {msg}")
            raise
        self.cache.set(interface_name, request_key, {"rows": backend_result.rows})
        limited = self._limit_rows(interface_name, normalized_params, backend_result.rows)
        return self._success_response(interface_name, normalized_params, limited, cache_hit=False)

    def _handle_with_incremental_cache(
        self, interface_name: str, normalized_params: dict[str, Any]
    ) -> dict[str, Any]:
        """按日期分片查询缓存，缺失部分通过接口获取并写入缓存。"""
        slices = split_date_range_by_month(
            normalized_params.get("start_date"),
            normalized_params.get("end_date"),
        )
        if not slices:
            try:
                backend_result = self.backend.fetch(interface_name, normalized_params)
            except Exception as e:
                msg = str(e)
                if "not set" in msg.lower() or "token" in msg.lower():
                    raise ValueError(f"数据源配置缺失: {msg}")
                raise
            limited = self._limit_rows(interface_name, normalized_params, backend_result.rows)
            return self._success_response(interface_name, normalized_params, limited, cache_hit=False)

        all_rows: list[dict[str, Any]] = []
        missing_slices: list[tuple[str, str]] = []

        for start_str, end_str in slices:
            slice_params = {**normalized_params, "start_date": start_str, "end_date": end_str}
            slice_key = self._build_request_key(interface_name, slice_params)
            cached = self.cache.get(slice_key)
            if cached is not None:
                all_rows.extend(cached.payload["rows"])
            else:
                missing_slices.append((start_str, end_str))

        for start_str, end_str in missing_slices:
            slice_params = {**normalized_params, "start_date": start_str, "end_date": end_str}
            slice_key = self._build_request_key(interface_name, slice_params)
            try:
                backend_result = self.backend.fetch(interface_name, slice_params)
            except Exception as e:
                msg = str(e)
                if "not set" in msg.lower() or "token" in msg.lower():
                    raise ValueError(f"数据源配置缺失: {msg}")
                raise
            self.cache.set(interface_name, slice_key, {"rows": backend_result.rows})
            all_rows.extend(backend_result.rows)

        merged = _sort_rows_by_datetime(all_rows)
        limited = self._limit_rows(interface_name, normalized_params, merged)
        cache_hit = len(missing_slices) == 0
        return self._success_response(interface_name, normalized_params, limited, cache_hit=cache_hit)

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
        rows = _compact_row_keys(limited["rows"], interface_name)
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
            "rows": rows,
        }
