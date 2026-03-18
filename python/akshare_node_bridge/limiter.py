from __future__ import annotations

import json
import math
from collections import OrderedDict
from typing import Any

from .calendar import CN_A_HALF_HOUR_SLOTS, parse_datetime_like


TIMESTAMP_KEYS = (
    "datetime",
    "date",
    "time",
    "timestamp",
    "日期时间",
    "日期",
    "时间",
)


def compact_json_bytes(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def estimate_row_bytes(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 1
    return max(1, math.ceil(compact_json_bytes(rows) / len(rows)))


def extract_row_datetime(row: dict[str, Any]):
    lowered = {str(key).lower(): key for key in row.keys()}
    for candidate in TIMESTAMP_KEYS:
        key = lowered.get(candidate.lower())
        if key is not None:
            dt = parse_datetime_like(row.get(key))
            if dt is not None:
                return dt
    return None


def group_rows_by_day(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    grouped: "OrderedDict[str, list[dict[str, Any]]]" = OrderedDict()
    for row in rows:
        dt = extract_row_datetime(row)
        day_key = dt.strftime("%Y-%m-%d") if dt else "__all__"
        grouped.setdefault(day_key, []).append(row)
    return list(grouped.values())


def filter_cn_half_hour_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for row in rows:
        dt = extract_row_datetime(row)
        if dt is None:
            filtered.append(row)
            continue
        slot = dt.strftime("%H:%M")
        if slot in CN_A_HALF_HOUR_SLOTS:
            filtered.append(row)
    return filtered


def sample_group(group: list[dict[str, Any]], step: int) -> list[dict[str, Any]]:
    if step <= 1 or len(group) <= 1:
        return list(group)
    sampled = [row for index, row in enumerate(group) if index % step == 0]
    if sampled[-1] is not group[-1]:
        sampled.append(group[-1])
    return sampled


def sample_rows_evenly(rows: list[dict[str, Any]], step: int) -> list[dict[str, Any]]:
    if step <= 1 or len(rows) <= 1:
        return list(rows)
    sampled = [row for index, row in enumerate(rows) if index % step == 0]
    if sampled[-1] is not rows[-1]:
        sampled.append(rows[-1])
    return sampled


def reduce_rows_evenly(
    rows: list[dict[str, Any]],
    max_bytes: int,
    apply_cn_half_hour_filter: bool = False,
) -> dict[str, Any]:
    source_rows = list(rows)
    if apply_cn_half_hour_filter:
        source_rows = filter_cn_half_hour_rows(source_rows)

    requested_rows = len(source_rows)
    estimated_row_bytes = estimate_row_bytes(source_rows)
    max_rows = max(1, max_bytes // estimated_row_bytes)

    if compact_json_bytes(source_rows) <= max_bytes:
        return {
            "rows": source_rows,
            "estimated_row_bytes": estimated_row_bytes,
            "max_rows": max_rows,
            "requested_rows": requested_rows,
            "returned_rows": len(source_rows),
            "sampling_step": 1,
        }

    groups = group_rows_by_day(source_rows)
    step = 2
    while True:
        reduced_rows: list[dict[str, Any]] = []
        for group in groups:
            reduced_rows.extend(sample_group(group, step))
        if compact_json_bytes(reduced_rows) <= max_bytes or len(reduced_rows) <= 1:
            return {
                "rows": reduced_rows,
                "estimated_row_bytes": estimated_row_bytes,
                "max_rows": max_rows,
                "requested_rows": requested_rows,
                "returned_rows": len(reduced_rows),
                "sampling_step": step,
            }
        if len(reduced_rows) >= len(source_rows):
            break
        step += 1

    global_step = 2
    while True:
        reduced_rows = sample_rows_evenly(source_rows, global_step)
        if compact_json_bytes(reduced_rows) <= max_bytes or len(reduced_rows) <= 1:
            return {
                "rows": reduced_rows,
                "estimated_row_bytes": estimated_row_bytes,
                "max_rows": max_rows,
                "requested_rows": requested_rows,
                "returned_rows": len(reduced_rows),
                "sampling_step": global_step,
            }
        global_step += 1

