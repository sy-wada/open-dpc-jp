"""Versioned, loss-preserving opt-in readers; contract-1 readers remain separate."""
from __future__ import annotations

import base64
import csv
from datetime import datetime
import hashlib
import io
from pathlib import Path
import re
import unicodedata

from .ef import normalize_ef_record
from .ff1_all_payloads import extract_one_record, ALL_REGISTERED_CODES
from .schemas import resolve_schema

PARSE_ENVELOPE_VERSION = "1"


def _envelope(data, kind, schema):
    return {"parse_envelope_version": PARSE_ENVELOPE_VERSION,
            "source": {"kind": kind, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)},
            "schema": schema.metadata(), "records": [], "source_rows": [], "diagnostics": []}


def _diagnostic(output, code, row=None, **details):
    output["diagnostics"].append({"code": code, "source_row": row, **details})


def _text(data, encoding, output):
    try:
        return data.decode(encoding)
    except UnicodeDecodeError:
        # No replacement characters silently erase data. Retain the exact input
        # for this explicit local parse result; never pass it to app provenance.
        output["source"]["unparsed_bytes_base64"] = base64.b64encode(data).decode("ascii")
        _diagnostic(output, "invalid_encoding")
        return None


def _calendar(raw):
    if not raw:
        return {"raw": raw, "value": None, "precision": "missing"}
    if len(raw) == 8 and raw.isascii() and raw.isdigit():
        if raw == "00000000":
            return {"raw": raw, "value": None, "precision": "unknown"}
        precision = "year" if raw[4:] == "0000" else "month" if raw[6:] == "00" else "day"
        normalized = raw[:4] + "0101" if precision == "year" else raw[:6] + "01" if precision == "month" else raw
        try:
            datetime.strptime(normalized, "%Y%m%d")
            return {"raw": raw, "value": normalized, "precision": precision}
        except ValueError:
            pass
    return {"raw": raw, "value": None, "precision": "invalid"}


def _rows(text, delimiter, output):
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
    previous = 0
    while True:
        try:
            cells = next(reader)
        except StopIteration:
            return
        except csv.Error:
            # A quoted malformed record may consume multiple physical lines.
            # Preserve the whole uninterpreted remainder rather than guessing
            # new record boundaries or dropping a partially read record.
            output["source"]["unparsed_text"] = "".join(text.splitlines(keepends=True)[previous:])
            _diagnostic(output, "malformed_delimited_record", previous + 1)
            return
        yield previous + 1, reader.line_num, cells
        previous = reader.line_num


def _dataset_date(path: Path, value: str | None) -> str | None:
    if value is not None:
        candidate = value.strip().replace("-", "") if isinstance(value, str) else value
        if not isinstance(candidate, str) or not re.fullmatch(r"\d{8}", candidate):
            raise ValueError("invalid_dataset_date")
        return candidate
    match = re.search(r"(?<!\d)(20\d{2})[-_]?([01]\d)[-_]?([0-3]\d)(?!\d)", Path(path).name)
    return "".join(match.groups()) if match else None


def parse_ef(path: Path, *, source_kind: str, schema_id=None, dataset_year=None,
             dataset_date=None, allow_fallback=False, encoding="cp932", delimiter=None):
    if source_kind not in {"efn", "efg"}:
        raise ValueError("source_kind_must_be_efn_or_efg")
    normalized_date = None if schema_id is not None and dataset_date is None else _dataset_date(path, dataset_date)
    if normalized_date and dataset_year is not None and int(normalized_date[:4]) != dataset_year:
        raise ValueError("dataset_date_year_mismatch")
    resolved = resolve_schema(schema_id=schema_id, dataset_year=dataset_year, dataset_date=normalized_date, allow_fallback=allow_fallback)
    schema = resolved.definition
    spec = schema["ef"]
    data = Path(path).read_bytes()
    output = _envelope(data, source_kind, resolved)
    text = _text(data, encoding, output)
    if text is None:
        return output
    first = text.splitlines()[0] if text.splitlines() else ""
    separator = delimiter or ("\t" if "\t" in first else "," if "," in first else None)
    if not separator and schema["year"] is not None and "ef-layout-not-yet-transcribed" in schema.get("limitations", []):
        # The later fixed widths are not a substitute for an earlier annual layout.
        output["source"]["unparsed_text"] = text
        _diagnostic(output, "unsupported_fixed_width_ef_layout")
        return output
    if separator:
        rows = _rows(text, separator, output)
    else:
        def fixed_rows():
            for number, line in enumerate(text.splitlines(), 1):
                cells, offset = [], 0
                for width in spec["widths"]:
                    cells.append(line[offset:offset+width])
                    offset += width
                if len(line) > offset:
                    cells.append(line[offset:])
                if len(line) < offset:
                    _diagnostic(output, "short_fixed_width_row", number)
                yield number, number, cells
        rows = fixed_rows()
    canonical_columns = list(spec.get("outpatient_columns", spec["columns"]) if source_kind == "efg" else spec["columns"])
    source_columns = spec.get("outpatient_source_columns" if source_kind == "efg" else "source_columns", canonical_columns)
    columns = canonical_columns[:]
    for number, end, cells in rows:
        normalized_columns = [unicodedata.normalize("NFKC", cell).strip() for cell in cells]
        is_header = number == 1 and len(cells)>1 and normalized_columns[1] == "データ識別番号"
        output["source_rows"].append({"line": number, "end_line": end, "cells": cells, "header": is_header})
        if is_header:
            columns = normalized_columns
            if len(set(columns)) != len(columns):
                _diagnostic(output, "duplicate_header", number)
            continue
        if len(cells) != len(columns):
            _diagnostic(output, "column_count_mismatch", number, expected=len(columns), actual=len(cells))
        record = {}
        for index, column in enumerate(columns):
            # First occurrence is interpreted; every duplicate remains in cells.
            record.setdefault(column, cells[index].strip() if index < len(cells) else "")
        compatibility = record.copy()
        for source_name, canonical_name in zip(source_columns, canonical_columns):
            if source_name in record:
                compatibility.setdefault(canonical_name, record[source_name])
        if "明細点数" in compatibility:
            compatibility.setdefault("明細点数・金額", compatibility["明細点数"])
        if "出来高・包括フラグ" in compatibility:
            compatibility.setdefault("行為明細区分情報", compatibility["出来高・包括フラグ"])
        if source_kind == "efg" and (schema["year"] is None or schema["year"] >= 2018):
            aliases = {"生年月日":"退院年月日", "外来受診年月日":"入院年月日"}
            compatibility.update({old: compatibility[new] for new, old in aliases.items() if new in compatibility})
        try:
            result = normalize_ef_record(compatibility, source_kind)
        except (ValueError, OverflowError):
            _diagnostic(output, "record_normalization_failed", number)
            output["records"].append({"source_row": number, "values": record, "status": "unresolved"})
            continue
        result["categoryLabel"] = spec["category_labels"].get(result["data_kubun"], result["data_kubun"])
        if schema["year"] is not None:
            if source_kind == "efg" and schema["year"] < 2018:
                # EF-3/4 are discharge/admission in these official layouts.
                for name in ("birth_date", "visit_date", "visit_month"):
                    result.pop(name, None)
            if schema["year"] <= 2015:
                for source_name, alias in (("明細点数", "明細点数・金額"),
                                           ("出来高・包括フラグ", "行為明細区分情報")):
                    if source_name in compatibility and alias not in record:
                        result.pop(alias, None)
            flags = result["ef17_raw"]
            # The compatibility normalizer uses recent EF17 meanings. Remove them
            # before assigning only meanings documented for this annual profile.
            for name in set(spec.get("efn_flags", []) + spec.get("efg_flags", [])) | {
                "fee_for_service_inclusive_flag", "discharge_prescription_flag",
                "inclusive_item_flag", "brought_in_drug_flag", "brought_in_prescriber_flag",
                "dpc_applicability_flag", "basic_lab_xray_inclusive_flag",
                "outside_prescription_flag", "generic_prescription_flag", "sex_code",
                "outcome_code", "main_disease_flag", "inclusive_management_flag",
                "refill_prescription_flag",
            }:
                result.pop(name, None)
            position_spec = spec.get(f"{source_kind}_ef17", {})
            length = position_spec.get("length")
            valid = length is not None and len(flags) == length and flags.isascii() and flags.isdigit()
            result["ef17_valid"] = valid
            if length is None:
                _diagnostic(output, "unsupported_ef17_definition", number)
            elif not valid and flags not in ("", "NULL"):
                _diagnostic(output, "invalid_ef17_length_or_value", number)
            if valid:
                for position, definition in position_spec["positions"].items():
                    if "name" in definition:
                        result[definition["name"]] = flags[int(position) - 1]
        calendar = _calendar(result["raw_date"])
        if calendar["precision"] == "invalid":
            _diagnostic(output, "invalid_calendar_date", number, field="service_date")
        if calendar["value"] is None:
            result["eventDate"] = result["service_date"] = None
            result["date_precision"] = result["service_date_precision"] = calendar["precision"]
            result["period_start_date"] = result["period_end_date"] = None
        if result["data_kubun"] not in spec["category_labels"]:
            _diagnostic(output, "unknown_data_category", number)
        output["records"].append({"source_row": number, "values": result})
    return output


def parse_ff1(path: Path, *, schema_id=None, dataset_year=None, dataset_date=None, allow_fallback=False,
              encoding="cp932", delimiter="\t", reference_date=None):
    normalized_date = None if schema_id is not None and dataset_date is None else _dataset_date(path, dataset_date)
    if normalized_date and dataset_year is not None and int(normalized_date[:4]) != dataset_year:
        raise ValueError("dataset_date_year_mismatch")
    resolved = resolve_schema(schema_id=schema_id, dataset_year=dataset_year, dataset_date=normalized_date, allow_fallback=allow_fallback)
    schema = resolved.definition
    spec = schema["ff1"]
    data = Path(path).read_bytes()
    output = _envelope(data, "ff1", resolved)
    text = _text(data, encoding, output)
    if text is None:
        return output
    for number, end, cells in _rows(text, delimiter, output):
        normalized = [unicodedata.normalize("NFKC", s).strip() for s in cells]
        expected_columns = [unicodedata.normalize("NFKC", s).strip() for s in spec["columns"]]
        is_header = normalized == expected_columns or (
            number == 1 and len(normalized) > 1 and normalized[1] == expected_columns[1]
        )
        output["source_rows"].append({"line": number, "end_line": end, "cells": cells, "header": is_header})
        if is_header:
            if len(set(normalized)) != len(normalized):
                _diagnostic(output, "duplicate_header", number)
            if normalized != expected_columns:
                _diagnostic(output, "header_schema_mismatch", number)
            continue
        if len(cells) != 17:
            _diagnostic(output, "column_count_mismatch", number, expected=17, actual=len(cells))
        row = cells + [""] * max(0, 17-len(cells))
        code = row[5]
        value = {"code": code, "version": row[6], "header": dict(zip(spec["columns"][:8], row[:8])), "payloads": []}
        if schema["year"] is None:
            known = code in ALL_REGISTERED_CODES
            if known:
                try:
                    value["legacy_values"] = extract_one_record(row, event_date=reference_date)
                except (ValueError, IndexError, KeyError) as error:
                    _diagnostic(output, "legacy_record_unresolved", number, error_type=type(error).__name__)
            payload_spec = {}
        else:
            code_spec = spec["codes"].get(code)
            known = code_spec is not None
            payload_spec = code_spec["payloads"] if known else {}
            if known and row[6] != code_spec["version"]:
                _diagnostic(output, "payload_version_mismatch", number, expected=code_spec["version"], actual=row[6])
        if not known:
            _diagnostic(output, "unknown_ff1_code", number, code_value=code)
        for index, raw in enumerate(row[8:17], 1):
            item = payload_spec.get(str(index), {})
            payload = {"number": index, "name": item.get("name"), "type": item.get("type", "string"), "raw": raw, "value": raw}
            if raw in item.get("special_values", {}):
                payload.update(value=None, precision="special", special_value=item["special_values"][raw])
            elif item.get("type") == "date":
                calendar = _calendar(raw)
                payload.update(value=calendar["value"], precision=calendar["precision"])
                if calendar["precision"] == "invalid":
                    _diagnostic(output, "invalid_calendar_date", number, payload=index)
            if known and schema["year"] is not None and not item and raw:
                _diagnostic(output, "unregistered_payload_value", number, payload=index)
            value["payloads"].append(payload)
        output["records"].append({"source_row": number, "values": value})
    return output
