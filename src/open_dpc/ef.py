"""Reader for DPC EF integrated files (EFn/EFg)."""

from __future__ import annotations

import csv
from calendar import monthrange
from datetime import datetime
import math
import unicodedata
from pathlib import Path
from typing import Any

from open_dpc.medication_periods import derive_medication_period

from open_dpc.schemas import legacy_schema as _legacy_schema
_legacy_ef = _legacy_schema()['ef']
EF_COLUMNS = _legacy_ef['columns']

EF_FIXED_WIDTHS = _legacy_ef['widths']

DATA_CATEGORY_LABELS = _legacy_ef['category_labels']


HEADER_MARKER_COLUMN = "データ識別番号"

def _normalize_column_name(name: str) -> str:
    return unicodedata.normalize("NFKC", name).strip()


def _normalize_columns(row: list[str]) -> list[str]:
    return [_normalize_column_name(value) for value in row]


def _is_header_row(row: list[str]) -> bool:
    if len(row) < 2:
        return False
    return _normalize_column_name(row[1]) == HEADER_MARKER_COLUMN


def _resolve_columns(rows: list[list[str]]) -> tuple[list[str], list[list[str]]]:
    if rows and _is_header_row(rows[0]):
        return _normalize_columns(rows[0]), rows[1:]
    return EF_COLUMNS, rows


def _field_value(record: dict[str, str], *names: str) -> str:
    for name in names:
        value = record.get(name)
        if value:
            return value
    return record.get(names[0], "") if names else ""


def _to_number(raw: Any) -> float | None:
    value = str(raw or "").strip().replace(",", "")
    if not value:
        return None
    try:
        numeric = float(value)
    except ValueError:
        return None
    return numeric if math.isfinite(numeric) else None


def normalize_ef_date(raw: Any) -> dict[str, str]:
    """Normalize EF date strings for timeline coordinates while preserving precision."""
    raw_date = str(raw or "").strip()
    digits = "".join(ch for ch in raw_date if ch.isdigit())
    if len(digits) < 8:
        return {"date": digits, "raw_date": raw_date, "date_precision": "unknown"}
    digits = digits[:8]
    year = digits[:4]
    month = digits[4:6]
    day = digits[6:8]
    if month == "00" and day == "00":
        return {"date": f"{year}0101", "raw_date": raw_date, "date_precision": "year"}
    if day == "00":
        return {"date": f"{year}{month}01", "raw_date": raw_date, "date_precision": "month"}
    return {"date": digits, "raw_date": raw_date, "date_precision": "day"}


def ef_period_end_date(normalized_date: str, date_precision: str) -> str:
    """Return an EF precision-span end without raising on malformed calendar data."""
    normalized_date = str(normalized_date or "")
    date_precision = str(date_precision or "")
    if not (len(normalized_date) == 8 and normalized_date.isdigit()):
        return normalized_date
    try:
        year = int(normalized_date[:4])
        month = int(normalized_date[4:6])
        day = int(normalized_date[6:8])
        if date_precision == "year":
            datetime(year, 1, 1)
            return f"{year:04d}1231"
        if date_precision == "month":
            datetime(year, month, 1)
            return f"{year:04d}{month:02d}{monthrange(year, month)[1]:02d}"
        datetime(year, month, day)
    except ValueError:
        return normalized_date
    return normalized_date


def _truthy_detail_no(value: str) -> bool:
    return value.isdigit() and value != "000"


def is_ef_parent_row(record: dict[str, Any]) -> bool:
    """Return whether an EF record is an E-derived parent row, not a detail row."""
    detail_no = str(_field_value(record, "行為明細番号", "detail_no") or "").strip()
    ef17 = str(_field_value(record, "行為明細区分情報") or "").strip().upper()
    return detail_no == "000" or ef17 == "NULL"


def is_comment_row(record: dict[str, Any]) -> bool:
    """Return whether an EF record is a receipt comment row."""
    code = str(_field_value(record, "レセプト電算処理システム用コード", "standardCode") or "")
    return code.startswith("8")


def is_efg_diagnosis_row(record: dict[str, Any]) -> bool:
    """Return whether an EFg record is an SY diagnosis row."""
    return str(_field_value(record, "データ区分", "data_kubun") or "").upper() == "SY"


def split_ef17(raw: dict[str, Any] | str, source_kind: str) -> dict[str, Any]:
    """Split EF-17 flags according to EFn or EFg semantics."""
    if isinstance(raw, dict):
        value = str(_field_value(raw, "行為明細区分情報") or "").strip()
    else:
        value = str(raw or "").strip()
    result: dict[str, Any] = {"ef17_raw": value, "ef17_valid": len(value) >= 7 and value.isdigit()}
    if not result["ef17_valid"]:
        return result

    source_kind = source_kind.lower()
    if source_kind == "efg":
        result.update(
            {
                "outside_prescription_flag": value[0],
                "generic_prescription_flag": value[1],
                "sex_code": value[2],
                "outcome_code": value[3],
                "main_disease_flag": value[4],
                "inclusive_management_flag": value[5],
                "refill_prescription_flag": value[6],
            }
        )
    else:
        result.update(
            {
                "discharge_prescription_flag": value[0],
                "inclusive_item_flag": value[1],
                "brought_in_drug_flag": value[2],
                "brought_in_prescriber_flag": value[3],
                "dpc_applicability_flag": value[4],
                "basic_lab_xray_inclusive_flag": value[5],
            }
        )
    return result


def normalize_ef_record(record: dict[str, Any], source_kind: str) -> dict[str, Any]:
    """Attach source-kind-specific aliases while preserving the original EF columns."""
    source_kind = source_kind.lower()
    data_kubun = str(_field_value(record, "データ区分") or "")
    detail_no = str(_field_value(record, "行為明細番号") or "")
    usage_raw = _field_value(record, "使用量")
    action_count_raw = _field_value(record, "行為回数")
    event_date_info = normalize_ef_date(
        _field_value(record, "実施年月日", "実施年月日・診療開始日")
    )
    normalized: dict[str, Any] = {
        **record,
        "sourceKind": source_kind,
        "facility_code": _field_value(record, "施設コード"),
        "patient_id": _field_value(record, "データ識別番号"),
        "data_kubun": data_kubun,
        "categoryLabel": DATA_CATEGORY_LABELS.get(data_kubun, data_kubun),
        "order_no": _field_value(record, "順序番号"),
        "detail_no": detail_no,
        "hospital_item_code": _field_value(record, "病院点数マスタコード"),
        "receipt_code": _field_value(
            record, "レセプト電算処理システム用コード", "レセプト電算コード"
        ),
        "interpretation_code": _field_value(record, "解釈番号"),
        "item_name": _field_value(record, "診療明細名称"),
        "usage_value_raw": usage_raw,
        "usage_value_num": _to_number(usage_raw),
        "unit_code": _field_value(record, "基準単位"),
        "amount_or_points": _field_value(record, "明細点数・金額"),
        "yen_point_kubun": _field_value(record, "円・点区分"),
        "fee_for_service_points": _field_value(record, "出来高実績点数"),
        "action_count": action_count_raw,
        "action_count_num": _to_number(action_count_raw),
        "receipt_type_code": _field_value(record, "レセプト種別コード"),
        "receipt_department_code": _field_value(record, "レセプト科区分"),
        "department_code": _field_value(record, "診療科区分"),
        "eventDate": event_date_info["date"],
        "raw_date": event_date_info["raw_date"],
        "date_precision": event_date_info["date_precision"],
        "standardCode": _field_value(
            record, "レセプト電算処理システム用コード", "レセプト電算コード"
        ),
        "masterCode": _field_value(record, "病院点数マスタコード"),
        "interpretationCode": _field_value(record, "解釈番号"),
        "name": _field_value(record, "診療明細名称"),
        "quantity": usage_raw,
        "unitCode": _field_value(record, "基準単位"),
    }
    normalized.update(split_ef17(record, source_kind))
    normalized["is_parent_row"] = is_ef_parent_row(normalized)
    normalized["is_comment_row"] = is_comment_row(normalized)
    normalized["is_diagnosis_row"] = source_kind == "efg" and is_efg_diagnosis_row(normalized)
    if source_kind == "efg":
        normalized.update(
            {
                "birth_date": _field_value(record, "退院年月日"),
                "visit_date": _field_value(record, "入院年月日"),
                "visit_month": _field_value(record, "入院年月日")[:6],
                "service_date": event_date_info["date"],
                "raw_service_date": event_date_info["raw_date"],
                "service_date_precision": event_date_info["date_precision"],
            }
        )
    else:
        normalized.update(
            {
                "admission_date": _field_value(record, "入院年月日"),
                "discharge_date": _field_value(record, "退院年月日"),
                "service_date": event_date_info["date"],
                "raw_service_date": event_date_info["raw_date"],
                "service_date_precision": event_date_info["date_precision"],
            }
        )
    normalized.update(derive_medication_period(normalized))
    return normalized


def _split_fixed_width(line: str) -> list[str]:
    values: list[str] = []
    offset = 0
    for width in EF_FIXED_WIDTHS:
        values.append(line[offset : offset + width].strip())
        offset += width
    return values


def _iter_rows(path: Path, *, encoding: str, delimiter: str | None) -> list[list[str]]:
    with path.open("r", encoding=encoding, newline="") as f:
        if delimiter:
            return list(csv.reader(f, delimiter=delimiter))
        rows: list[list[str]] = []
        for raw in f:
            line = raw.rstrip("\r\n")
            if "\t" in line:
                rows.append(next(csv.reader([line], delimiter="\t")))
            elif "," in line:
                rows.append(next(csv.reader([line])))
            else:
                rows.append(_split_fixed_width(line))
        return rows


def _to_record(row: list[str], source_kind: str, columns: list[str]) -> dict[str, Any]:
    padded = row + [""] * max(0, len(columns) - len(row))
    record = {column: padded[index].strip() for index, column in enumerate(columns)}
    return normalize_ef_record(record, source_kind)


def read_ef_file(
    path: Path,
    *,
    source_kind: str | None = None,
    encoding: str = "cp932",
    delimiter: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Read EFn/EFg source records without study classification or GUI projections."""
    inferred_kind = source_kind or path.name[:3].lower()
    rows = _iter_rows(path, encoding=encoding, delimiter=delimiter)
    columns, data_rows = _resolve_columns(rows)
    records = [_to_record(row, inferred_kind, columns) for row in data_rows]
    if limit is not None:
        records = records[:limit]
    return {
        "sourcePath": str(path),
        "sourceKind": inferred_kind,
        "columns": columns,
        "recordCount": len(records),
        "records": records,
    }


