from __future__ import annotations

from datetime import date, datetime, timedelta

# A股/指数/期货共用上交所交易日历
_XSHG_CALENDAR = None


def _get_xshg_calendar():
    """懒加载上交所交易日历。"""
    global _XSHG_CALENDAR
    if _XSHG_CALENDAR is None:
        try:
            import exchange_calendars as xcals  # noqa: PLC0415
            _XSHG_CALENDAR = xcals.get_calendar("XSHG")
        except Exception:
            _XSHG_CALENDAR = False
    return _XSHG_CALENDAR if _XSHG_CALENDAR else None


def is_trading_day(d: date | datetime | str | None) -> bool:
    """判断给定日期是否为 A 股/指数/期货交易日。非交易日（周末、节假日）返回 False。"""
    if d is None:
        return False
    if isinstance(d, str):
        dt = parse_datetime_like(d)
        d = dt.date() if dt else None
    elif isinstance(d, datetime):
        d = d.date()
    if d is None:
        return False
    cal = _get_xshg_calendar()
    if cal is None:
        # 无 exchange_calendars 时退化为周末检查
        return d.weekday() < 5
    return cal.is_session(d)


CN_A_HALF_HOUR_SLOTS = {
    "09:30",
    "10:00",
    "10:30",
    "11:00",
    "11:30",
    "13:00",
    "13:30",
    "14:00",
    "14:30",
    "15:00",
}


def parse_datetime_like(value: object) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    candidates = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y%m%d",
    ]
    for fmt in candidates:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def is_same_day(start_date: object, end_date: object) -> bool:
    start_dt = parse_datetime_like(start_date)
    end_dt = parse_datetime_like(end_date)
    if start_dt is None or end_dt is None:
        return False
    return start_dt.date() == end_dt.date()


def split_date_range_by_month(start_date: object, end_date: object) -> list[tuple[str, str]]:
    """将日期范围按月拆分为 (start_str, end_str) 列表，用于分片缓存。"""
    start_dt = parse_datetime_like(start_date)
    end_dt = parse_datetime_like(end_date)
    if start_dt is None or end_dt is None:
        return []
    start_d = start_dt.date()
    end_d = end_dt.date()
    if start_d > end_d:
        return []
    result: list[tuple[str, str]] = []
    current = start_d
    while current <= end_d:
        month_start = current.replace(day=1)
        next_month = month_start + timedelta(days=32)
        month_end = (next_month.replace(day=1) - timedelta(days=1))
        slice_end = min(month_end, end_d)
        result.append((current.strftime("%Y-%m-%d"), slice_end.strftime("%Y-%m-%d")))
        current = slice_end + timedelta(days=1)
    return result

