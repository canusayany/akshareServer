from __future__ import annotations

from datetime import datetime


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

