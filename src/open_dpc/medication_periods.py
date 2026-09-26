"""Shared source-period derivation and course merging for DPC medications."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from datetime import date, timedelta
import math
from typing import Any, Hashable


def _display(value: Any) -> str:
    return str(value or "").strip()


def _date_from_yyyymmdd(value: Any) -> date | None:
    raw = _display(value)
    if len(raw) != 8 or not raw.isdigit():
        return None
    try:
        return date.fromisoformat(f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}")
    except ValueError:
        return None


def _date_value(value: date) -> str:
    return value.strftime("%Y%m%d")


def _source_date(record: Mapping[str, Any]) -> str:
    for key in ("service_date", "eventDate", "event_date", "date"):
        value = _display(record.get(key))
        if value:
            return value
    return ""


def _positive_integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric) or numeric <= 0 or not numeric.is_integer():
        return None
    return int(numeric)


def derive_medication_period(record: Mapping[str, Any]) -> dict[str, Any]:
    """Derive a JSON-safe inclusive source interval for one EF medication record.

    EF data category 21 represents an oral prescription: its positive integer
    ``action_count_num`` is prescription days.  Every other category remains a
    one-day source event, including injections, whose action count is not a
    duration in this stage.
    """
    start_date = _source_date(record)
    data_kubun = _display(record.get("data_kubun") or record.get("データ区分"))
    duration_days = 1
    warning: dict[str, str] | None = None
    if data_kubun == "21":
        days = _positive_integer(record.get("action_count_num"))
        if days is None:
            warning = {
                "code": "INVALID_ORAL_ACTION_COUNT_FALLBACK_ONE_DAY",
                "message": "Oral prescription action_count_num must be a positive integer; using one day.",
            }
            rationale = "oral_invalid_action_count_fallback_one_day"
        else:
            duration_days = days
            rationale = "oral_action_count_prescription_days"
    else:
        rationale = "one_day_source_event"

    parsed_start = _date_from_yyyymmdd(start_date)
    end_date = _date_value(parsed_start + timedelta(days=duration_days - 1)) if parsed_start else start_date
    result: dict[str, Any] = {
        "period_start_date": start_date,
        "period_end_date": end_date,
        "period_duration_days": duration_days,
        "period_rationale": rationale,
    }
    if warning is not None:
        result["period_warning"] = warning
    return result


def medication_period_is_positionable(record: Mapping[str, Any]) -> bool:
    """Whether a medication candidate can be located on the calendar.

    Only extracted medication candidates call this helper.  A malformed
    medication date therefore blocks negative medication inference, while
    unrelated EF rows remain outside that completeness decision.
    """
    period = derive_medication_period(record)
    return (
        _date_from_yyyymmdd(period["period_start_date"]) is not None
        and _date_from_yyyymmdd(period["period_end_date"]) is not None
    )


def merge_medication_periods(
    records: Iterable[Mapping[str, Any]],
    *,
    group_key: Callable[[Mapping[str, Any]], Hashable],
) -> list[dict[str, Any]]:
    """Merge same-key medication intervals with at most one uncovered day.

    The returned courses retain their source records and period metadata so
    timeline, Abx Log, and prior-antimicrobial logic can share the same rule.
    Records with invalid dates are excluded because they cannot be positioned
    on a calendar timeline.
    """
    grouped: dict[Hashable, list[dict[str, Any]]] = {}
    for source_record in records:
        record = dict(source_record)
        period = derive_medication_period(record)
        record.update(period)
        start = _date_from_yyyymmdd(period["period_start_date"])
        end = _date_from_yyyymmdd(period["period_end_date"])
        if start is None or end is None:
            continue
        record["_medication_period_start"] = start
        record["_medication_period_end"] = end
        grouped.setdefault(group_key(record), []).append(record)

    courses: list[dict[str, Any]] = []
    for key, group_records in grouped.items():
        ordered = sorted(
            group_records,
            key=lambda item: (
                item["_medication_period_start"],
                item["_medication_period_end"],
            ),
        )
        current: list[dict[str, Any]] = []
        current_start: date | None = None
        current_end: date | None = None
        for record in ordered:
            start = record["_medication_period_start"]
            end = record["_medication_period_end"]
            # A course may have no gap or one uncovered calendar day.  Two
            # absent days means the next administration starts a new course.
            if current and current_end is not None and start > current_end + timedelta(days=2):
                assert current_start is not None
                courses.append(_course(key, current, current_start, current_end))
                current = []
                current_start = None
                current_end = None
            current.append(record)
            current_start = start if current_start is None else min(current_start, start)
            current_end = end if current_end is None else max(current_end, end)
        if current and current_start is not None and current_end is not None:
            courses.append(_course(key, current, current_start, current_end))
    return courses


def _course(
    key: Hashable, records: list[dict[str, Any]], start: date, end: date
) -> dict[str, Any]:
    return {
        "group_key": key,
        "start_date": _date_value(start),
        "end_date": _date_value(end),
        "duration_days": (end - start).days + 1,
        "records": records,
        "warnings": [record["period_warning"] for record in records if record.get("period_warning")],
    }
