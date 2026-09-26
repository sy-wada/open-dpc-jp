"""Cached annual schema resolution, independent of patient clinical event dates."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
import hashlib
from importlib.resources import files
import json
import re
from typing import Any


@lru_cache(maxsize=1)
def _registry():
    return json.loads(files(__package__).joinpath("compiled/registry.json").read_bytes())


@lru_cache(maxsize=1)
def source_ledger():
    return deepcopy(json.loads(files(__package__).joinpath("compiled/source_ledger.json").read_bytes()))


@lru_cache(maxsize=16)
def _resource(schema_id):
    if schema_id not in {entry["id"] for entry in _registry()["schemas"]}:
        raise ValueError("unknown_schema_id")
    data = files(__package__).joinpath("compiled", schema_id + ".json").read_bytes()
    return json.loads(data), hashlib.sha256(data).hexdigest()


def legacy_schema() -> dict[str, Any]:
    """Detached constants for compatibility modules; no shared mutable registry."""
    return deepcopy(_resource("legacy-mixed-v1")[0])


@dataclass(frozen=True)
class ResolvedSchema:
    schema_id: str
    input_year: int | None
    resolution: str
    input_date: str | None = None

    @property
    def definition(self):
        return deepcopy(_resource(self.schema_id)[0])

    def metadata(self):
        schema, digest = _resource(self.schema_id)
        reason = ("latest_preceding_year" if schema["year"] < self.input_year else "earliest_subsequent_year") if self.resolution == "fallback" else self.resolution
        return deepcopy({"id": self.schema_id, "version": schema["schema_version"], "sha256": digest,
                "input_schema_year": self.input_year, "parser_schema_year": schema["year"],
                "input_schema_date": self.input_date,
                "revision": schema["revision"], "schema_resolution": self.resolution,
                "selection_reason": reason,
                "validation_status": schema["validation_status"],
                "effective_from": schema.get("effective_from"), "effective_to": schema.get("effective_to"),
                "data_effective_from": schema.get("data_effective_from", schema.get("effective_from")),
                "data_effective_to": schema.get("data_effective_to", schema.get("effective_to")),
                "document_revision": schema.get("document_revision", schema["revision"]),
                "source_ids": schema.get("source_ids", []),
                "definition_evidence": schema.get("definition_evidence", {}),
                "validation_scope": schema.get("validation_scope", []),
                "limitations": schema.get("limitations", ["legacy-definition-not-annual-conformance"]),
                "warnings": (["exact_schema_not_available"] if self.resolution == "fallback" else [])
                    + (["partial_source_coverage"] if schema.get("validation_status") == "partial-source-coverage" else [])})


def resolve_schema(*, schema_id: str | None = None, dataset_year: int | None = None,
                   dataset_date: str | None = None, allow_fallback: bool = False) -> ResolvedSchema:
    if schema_id is not None and (dataset_year is not None or dataset_date is not None):
        raise ValueError("specify_schema_id_or_dataset_date")
    if schema_id is not None:
        _resource(schema_id)
        return ResolvedSchema(schema_id, _resource(schema_id)[0]["year"], "legacy" if schema_id == "legacy-mixed-v1" else "exact")
    normalized_date = _normalize_dataset_date(dataset_date)
    if normalized_date is not None:
        if dataset_year is not None and dataset_year != int(normalized_date[:4]):
            raise ValueError("dataset_date_year_mismatch")
        dataset_year = int(normalized_date[:4])
    if isinstance(dataset_year, bool) or not isinstance(dataset_year, int):
        raise ValueError("explicit_schema_selection_required")
    entries = [e for e in _registry()["schemas"] if e["year"] is not None and e.get("selectable_by_date", True)]
    if normalized_date is not None:
        matching = [e for e in entries if _date_matches(e, normalized_date)]
        if len(matching) == 1:
            return ResolvedSchema(matching[0]["id"], dataset_year, "effective_date", normalized_date)
        if len(matching) > 1:
            raise ValueError("ambiguous_schema_date")
        if not allow_fallback:
            raise ValueError("unsupported_schema_date")
    exact = [e for e in entries if e["year"] == dataset_year]
    if exact:
        if len(exact) > 1:
            raise ValueError("schema_date_required")
        return ResolvedSchema(exact[0]["id"], dataset_year, "exact", normalized_date)
    compatible = [e for e in entries if dataset_year in e["compatible_input_years"]]
    if compatible:
        if len(compatible) > 1:
            raise ValueError("schema_date_required")
        return ResolvedSchema(compatible[0]["id"], dataset_year, "compatible", normalized_date)
    if not allow_fallback:
        raise ValueError("unsupported_schema_year")
    earlier = [e for e in entries if e["year"] < dataset_year]
    selected = max(earlier, key=lambda e: (e["year"], e["id"])) if earlier else min(entries, key=lambda e: (e["year"], e["id"]))
    return ResolvedSchema(selected["id"], dataset_year, "fallback", normalized_date)


def _normalize_dataset_date(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("invalid_dataset_date")
    candidate = value.strip().replace("-", "")
    if not re.fullmatch(r"\d{8}", candidate):
        raise ValueError("invalid_dataset_date")
    try:
        datetime.strptime(candidate, "%Y%m%d")
    except ValueError as error:
        raise ValueError("invalid_dataset_date") from error
    return candidate


def _date_matches(entry: dict[str, Any], dataset_date: str) -> bool:
    start = entry.get("effective_from")
    end = entry.get("effective_to")
    return bool(start and end and start <= dataset_date <= end)
