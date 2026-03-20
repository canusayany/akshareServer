from __future__ import annotations

import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .backend import _compact_row_keys, create_backend
from .cache import SqliteCache
from .calendar import is_same_day, is_trading_day, parse_datetime_like, split_date_range_by_month
from .logger import get_logger
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

INTERFACES_WITH_DATE_RANGE = frozenset({
    "stock_zh_a_hist",
    "stock_index_zh_hist",
    "futures_zh_hist",
    "fund_etf_market",
    "stock_board_industry",
    "stock_board_concept",
})

DATE_SENSITIVE_INTERFACES = frozenset({
    "stock_zh_a_spot",
    "stock_zh_a_hist",
    "stock_index_zh_hist",
    "futures_zh_spot",
    "futures_zh_hist",
})


def _sort_rows_by_datetime(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key_fn(row: dict[str, Any]):
        dt = extract_row_datetime(row)
        return (0, dt) if dt else (1, None)

    return sorted(rows, key=key_fn)


class BridgeService:
    def __init__(self, db_path: str | Path, max_bytes: int = 5000, test_mode: bool = False) -> None:
        self.cache = SqliteCache(db_path)
        self.max_bytes = int(max_bytes)
        self.backend = create_backend(test_mode=test_mode)
        raw_workers = os.environ.get("AKSHARE_BRIDGE_MAX_WORKERS", "").strip()
        self.max_workers = max(1, int(raw_workers)) if raw_workers.isdigit() else 4
        self.logger = get_logger()

    def handle(self, interface_name: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        started_at = time.perf_counter()
        if interface_name not in SUPPORTED_INTERFACES:
            raise ValueError(f"Unsupported interface: {interface_name}")

        normalized_params = normalize_params_llm(params, interface_name)
        ok, err = validate_required(interface_name, normalized_params)
        if not ok and err:
            raise ValueError(err)
        normalized_params = self._normalize_params(normalized_params)

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

        use_incremental = (
            interface_name in INTERFACES_WITH_DATE_RANGE
            and normalized_params.get("start_date")
            and normalized_params.get("end_date")
        )
        if use_incremental and interface_name in ("fund_etf_market", "stock_board_industry", "stock_board_concept"):
            use_incremental = normalized_params.get("mode") == "hist"
        if use_incremental:
            return self._handle_with_incremental_cache(interface_name, normalized_params)

        request_key = self._build_request_key(interface_name, normalized_params)
        cached = self.cache.get(request_key)
        if cached is not None:
            filtered_rows = self._post_process_rows(interface_name, normalized_params, cached.payload["rows"])
            limited = self._limit_rows(interface_name, normalized_params, filtered_rows)
            response = self._success_response(interface_name, normalized_params, limited, cache_hit=True)
            self._log_request(interface_name, normalized_params, response, started_at)
            return response

        try:
            backend_result = self.backend.fetch(interface_name, normalized_params)
        except Exception as e:
            self._log_failure(interface_name, normalized_params, started_at, e)
            msg = str(e)
            if "not set" in msg.lower() or "token" in msg.lower():
                raise ValueError(f"数据源配置缺失: {msg}")
            if "returned empty" in msg.lower() or "empty" in msg.lower():
                raise ValueError(f"数据源暂无数据: {msg}")
            raise
        filtered_rows = self._post_process_rows(interface_name, normalized_params, backend_result.rows)
        self.cache.set(interface_name, request_key, {"rows": filtered_rows})
        limited = self._limit_rows(interface_name, normalized_params, filtered_rows)
        response = self._success_response(interface_name, normalized_params, limited, cache_hit=False)
        self._log_request(interface_name, normalized_params, response, started_at)
        return response

    def _handle_with_incremental_cache(
        self, interface_name: str, normalized_params: dict[str, Any]
    ) -> dict[str, Any]:
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
            filtered_rows = self._post_process_rows(interface_name, normalized_params, backend_result.rows)
            limited = self._limit_rows(interface_name, normalized_params, filtered_rows)
            return self._success_response(interface_name, normalized_params, limited, cache_hit=False)

        all_rows: list[dict[str, Any]] = []
        missing_slices: list[tuple[str, str]] = []

        for start_str, end_str in slices:
            slice_params = {**normalized_params, "start_date": start_str, "end_date": end_str}
            slice_key = self._build_request_key(interface_name, slice_params)
            cached = self.cache.get(slice_key)
            if cached is not None:
                all_rows.extend(self._post_process_rows(interface_name, slice_params, cached.payload["rows"]))
            else:
                missing_slices.append((start_str, end_str))

        if missing_slices:
            self.logger.info(
                "incremental_fetch interface=%s missing_slices=%s max_workers=%s params=%s",
                interface_name,
                len(missing_slices),
                min(self.max_workers, len(missing_slices)),
                self._compact_json(normalized_params),
            )
            max_workers = min(self.max_workers, len(missing_slices))
            if max_workers <= 1:
                for start_str, end_str in missing_slices:
                    all_rows.extend(self._fetch_and_cache_slice(interface_name, normalized_params, start_str, end_str))
            else:
                with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="akshare-slice") as executor:
                    futures = {
                        executor.submit(
                            self._fetch_and_cache_slice,
                            interface_name,
                            normalized_params,
                            start_str,
                            end_str,
                        ): (start_str, end_str)
                        for start_str, end_str in missing_slices
                    }
                    for future in as_completed(futures):
                        all_rows.extend(future.result())

        merged = self._post_process_rows(interface_name, normalized_params, all_rows)
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

    def _fetch_and_cache_slice(
        self,
        interface_name: str,
        normalized_params: dict[str, Any],
        start_str: str,
        end_str: str,
    ) -> list[dict[str, Any]]:
        started_at = time.perf_counter()
        slice_params = {**normalized_params, "start_date": start_str, "end_date": end_str}
        slice_key = self._build_request_key(interface_name, slice_params)
        try:
            backend_result = self.backend.fetch(interface_name, slice_params)
        except Exception as e:
            self.logger.exception(
                "slice_error interface=%s start=%s end=%s duration_ms=%.1f params=%s error=%s",
                interface_name,
                start_str,
                end_str,
                (time.perf_counter() - started_at) * 1000,
                self._compact_json(slice_params),
                str(e),
            )
            msg = str(e)
            if "not set" in msg.lower() or "token" in msg.lower():
                raise ValueError(f"数据源配置缺失: {msg}")
            raise
        filtered_rows = self._post_process_rows(interface_name, slice_params, backend_result.rows)
        self.cache.set(interface_name, slice_key, {"rows": filtered_rows})
        self.logger.info(
            "slice_ok interface=%s start=%s end=%s duration_ms=%.1f rows=%s",
            interface_name,
            start_str,
            end_str,
            (time.perf_counter() - started_at) * 1000,
            len(filtered_rows),
        )
        return filtered_rows

    def _post_process_rows(
        self,
        interface_name: str,
        params: dict[str, Any],
        rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        processed = self._filter_rows_by_date_range(interface_name, params, rows)
        return self._dedupe_and_sort_rows(processed)

    def _filter_rows_by_date_range(
        self,
        interface_name: str,
        params: dict[str, Any],
        rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if interface_name not in INTERFACES_WITH_DATE_RANGE:
            return list(rows)

        start_dt = parse_datetime_like(params.get("start_date"))
        end_dt = parse_datetime_like(params.get("end_date"))
        if start_dt is None and end_dt is None:
            return list(rows)

        start_bound = start_dt.date() if start_dt is not None else None
        end_bound = end_dt.date() if end_dt is not None else None
        filtered: list[dict[str, Any]] = []
        for row in rows:
            row_dt = extract_row_datetime(row)
            if row_dt is None:
                continue
            row_day = row_dt.date()
            if start_bound is not None and row_day < start_bound:
                continue
            if end_bound is not None and row_day > end_bound:
                continue
            filtered.append(row)
        return filtered

    def _dedupe_and_sort_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            row_key = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            if row_key in seen:
                continue
            seen.add(row_key)
            deduped.append(row)
        return _sort_rows_by_datetime(deduped)

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

    def _log_request(
        self,
        interface_name: str,
        params: dict[str, Any],
        response: dict[str, Any],
        started_at: float,
    ) -> None:
        self.logger.info(
            "request_ok interface=%s duration_ms=%.1f cache_hit=%s requested_rows=%s returned_rows=%s sampling_step=%s params=%s",
            interface_name,
            (time.perf_counter() - started_at) * 1000,
            response.get("cache_hit"),
            response.get("requested_rows"),
            response.get("returned_rows"),
            response.get("sampling_step"),
            self._compact_json(params),
        )

    def _log_failure(
        self,
        interface_name: str,
        params: dict[str, Any],
        started_at: float,
        error: Exception,
    ) -> None:
        self.logger.exception(
            "request_error interface=%s duration_ms=%.1f params=%s error=%s",
            interface_name,
            (time.perf_counter() - started_at) * 1000,
            self._compact_json(params),
            str(error),
        )

    def _compact_json(self, value: dict[str, Any]) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
