"""Data-defined ICD-10 matching and observed Charlson scores (no age adjustment)."""
from __future__ import annotations

from functools import lru_cache
import hashlib
from importlib.resources import files
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Iterable

from open_dpc.semantics import SEMANTIC_RESULT_VERSION


def normalize_icd10(value: Any) -> str:
    return str(value or "").upper().replace(".", "").strip()


def matches_prefixes(code: str, prefixes: Iterable[str]) -> bool:
    """Pure prefix engine; definition/eligibility policy is provided by the caller."""
    return any(code.startswith(prefix) for prefix in prefixes)


def _validate(value):
    if not isinstance(value, dict) or value.get("definition_schema_version") != "1":
        raise ValueError("unsupported_definition_schema")
    if not isinstance(value.get("id"), str) or not value["id"] or not isinstance(value.get("version"), str):
        raise ValueError("definition_identity_required")
    conditions = value.get("conditions")
    if not isinstance(conditions, dict) or not conditions:
        raise ValueError("conditions_required")
    for key, condition in conditions.items():
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key) or not isinstance(condition, dict):
            raise ValueError("invalid_condition")
        prefixes = condition.get("icd10_prefixes")
        if not isinstance(prefixes, list) or not prefixes or any(not isinstance(p, str) or not re.fullmatch(r"[A-Z][0-9]{2}[A-Z0-9]*", p) for p in prefixes):
            raise ValueError("invalid_icd10_prefix")
        weight = condition.get("weight")
        if isinstance(weight, bool) or not isinstance(weight, int) or weight < 0:
            raise ValueError("invalid_condition_weight")
        supersedes = condition.get("suppresses", [])
        if not isinstance(supersedes, list) or any(target not in conditions or target == key for target in supersedes):
            raise ValueError("invalid_condition_hierarchy")
    def visit(key, active):
        if key in active:
            raise ValueError("cyclic_condition_hierarchy")
        for target in conditions[key].get("suppresses", []):
            visit(target, active | {key})
    for key in conditions:
        visit(key, set())
    return value


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_definition_key")
        result[key] = value
    return result


@lru_cache(maxsize=8)
def _builtin_bytes(filename: str) -> bytes:
    return files(__package__).joinpath("definitions", filename).read_bytes()


@lru_cache(maxsize=1)
def _registry() -> dict:
    data = files(__package__).joinpath("definitions", "registry.json").read_bytes()
    registry = json.loads(data, object_pairs_hook=_no_duplicate_keys)
    if not isinstance(registry, dict):
        raise ValueError("invalid_definition_registry")
    for entry in registry.values():
        if not isinstance(entry, dict) or entry.get("latest") not in entry.get("versions", {}):
            raise ValueError("invalid_definition_registry")
        for filename in entry["versions"].values():
            if not isinstance(filename, str) or not re.fullmatch(r"[a-z0-9-]+\.json", filename):
                raise ValueError("invalid_definition_registry")
    return registry


def load_definition(definition: str | Path = "quan-2005", *, version: str | None = None) -> tuple[dict, dict]:
    if isinstance(definition, Path):
        data = definition.read_bytes()
    else:
        entry = _registry().get(definition)
        if entry is None:
            raise ValueError("unknown_definition")
        resolved_version = entry["latest"] if version is None else version
        filename = entry["versions"].get(resolved_version)
        if filename is None:
            raise ValueError("unknown_definition_version")
        data = _builtin_bytes(filename)
    value = _validate(json.loads(data, object_pairs_hook=_no_duplicate_keys))
    if isinstance(definition, Path):
        if version is not None and value["version"] != version:
            raise ValueError("definition_version_mismatch")
    elif value["id"] != definition or value["version"] != resolved_version:
        raise ValueError("definition_registry_mismatch")
    metadata = {"id": value["id"], "version": value["version"], "sha256": hashlib.sha256(data).hexdigest()}
    return value, metadata


def calculate_charlson(diagnoses: Iterable[dict[str, Any] | str], *, definition: str | Path = "quan-2005", version: str | None = None) -> dict[str, Any]:
    """Score the supplied observations only; temporal/cohort selection is caller-owned.

    Non-matches are not clinical absence. Empty or entirely invalid input has no
    score. A partial result is an observed score, not a complete patient index.
    """
    return CharlsonEvaluator(definition=definition, version=version).evaluate(diagnoses)


class CharlsonEvaluator:
    """Resolve and retain an exact definition snapshot for repeated evaluations."""

    def __init__(self, *, definition: str | Path = "quan-2005", version: str | None = None):
        spec, identity = load_definition(definition, version=version)
        object.__setattr__(self, "_spec", _freeze(spec))
        object.__setattr__(self, "_identity", MappingProxyType(identity.copy()))

    def __setattr__(self, name, value):
        raise AttributeError("immutable_evaluator")

    @property
    def definition(self) -> dict:
        return dict(self._identity)

    def evaluate(self, diagnoses: Iterable[dict[str, Any] | str]) -> dict[str, Any]:
        return _evaluate(diagnoses, self._spec, self._identity)


def _evaluate(diagnoses, spec, identity):
    records = list(diagnoses)
    facts, unresolved = [], []
    for index, record in enumerate(records):
        item = {"icd10": record} if isinstance(record, str) else record
        if not isinstance(item, dict):
            raise TypeError("diagnosis_must_be_string_or_mapping")
        code = normalize_icd10(item.get("icd10"))
        if not re.fullmatch(r"[A-Z][0-9]{2}[A-Z0-9]*", code) or item.get("resolution_status") in {"unresolved", "invalid", "missing"}:
            unresolved.append({"record_index": index, "icd10": str(item.get("icd10") or ""), "status": "unresolved"})
            continue
        evidence = {"record_index": index, "icd10": code}
        for key in ("source", "date", "date_precision", "source_record_id"):
            if key in item:
                evidence[key] = item[key]
        facts.append(evidence)
    conditions = {}
    for name, condition in spec["conditions"].items():
        evidence = [fact.copy() for fact in facts if matches_prefixes(fact["icd10"], condition["icd10_prefixes"])]
        conditions[name] = {"matched": bool(evidence), "weight": condition["weight"], "counted": bool(evidence), "suppressed_by": [], "evidence": evidence}
    for name, condition in spec["conditions"].items():
        if conditions[name]["matched"]:
            for target in condition.get("suppresses", []):
                if conditions[target]["matched"]:
                    conditions[target]["counted"] = False
                    conditions[target]["suppressed_by"].append(name)
    score = sum(c["weight"] for c in conditions.values() if c["counted"]) if facts else None
    return {"semantic_result_version": SEMANTIC_RESULT_VERSION,
            "definition": dict(identity), "weighting": _thaw(spec.get("weighting")),
            "algorithm": {"id": "charlson-prefix-hierarchy", "version": "1"},
            "conditions": conditions, "score": score, "score_scope": "supplied-observations",
            "input_status": "empty" if not records else "partial" if unresolved else "resolved",
            "input_count": len(records), "resolved_count": len(facts), "unresolved": unresolved,
            "warnings": ["unresolved_diagnoses"] if unresolved else []}


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value):
    if isinstance(value, MappingProxyType):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value
