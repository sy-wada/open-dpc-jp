"""Source-preserving DPC diagnosis certainty; inclusion remains caller policy."""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable

CERTAINTY_RULE_VERSION = "1"
CERTAINTIES = frozenset({"suspected", "not_marked_suspected", "unknown"})
SUSPECTED_POLICIES = frozenset({"include", "exclude"})
_DIAGNOSIS_CODES = frozenset({"A006010", "A006020", "A006030", "A006031", "A006040", "A006050"})
_LEGACY_LABELS = {"A006010": "主傷病", "A006020": "入院契機", "A006030": "医療資源",
                  "A006031": "医療資源2", "A006040": "併存症", "A006050": "続発症"}


def diagnosis_certainty(name: Any = None, *, modifiers: Iterable[tuple[str, Any]] = ()) -> dict[str, Any]:
    """Classify only explicit DPC suspicion marks, retaining their source values."""
    evidence: list[dict[str, Any]] = []
    readable = False
    suspected = False
    for field, raw in modifiers:
        if raw is None or raw == "":
            continue
        for token in str(raw).split("|"):
            code = unicodedata.normalize("NFKC", token).strip()
            if not code:
                continue
            valid = bool(re.fullmatch(r"[0-9]{4}", code))
            readable |= valid
            marked = valid and code == "8002"
            suspected |= marked
            evidence.append({"field": field, "method": "modifier_code" if valid else "invalid_modifier", "raw": token, "suspected": marked})
    if isinstance(name, str) and name.strip():
        normalized = unicodedata.normalize("NFKC", name).strip()
        marked = normalized.endswith("疑い")
        readable = True
        suspected |= marked
        evidence.append({"field": "disease_name", "method": "name_suffix", "raw": name, "suspected": marked})
    return {"certainty": "suspected" if suspected else "not_marked_suspected" if readable else "unknown",
            "certainty_evidence": evidence, "certainty_rule_version": CERTAINTY_RULE_VERSION}


def ff1_diagnosis_certainty(record: dict[str, Any], *, code: str, label: str) -> dict[str, Any]:
    """Read the legacy raw slots before the joined compatibility field."""
    slots = [(f"{code}_payload{index}_raw", record.get(f"{code}_payload{index}_raw")) for index in range(5, 9)]
    if any(value not in (None, "") for _, value in slots):
        modifiers = slots
    else:
        modifiers = [(f"{label}_修飾語コード", record.get(f"{label}_修飾語コード"))]
    return diagnosis_certainty(record.get(label), modifiers=modifiers)


def efg_diagnosis_certainty(diagnosis: dict[str, Any]) -> dict[str, Any]:
    return diagnosis_certainty(diagnosis.get("disease_name"))


def diagnosis_observations(envelope: dict[str, Any]) -> list[dict[str, Any]]:
    """Project versioned FF1/EFg parse records without changing the parse envelope."""
    kind = envelope.get("source", {}).get("kind")
    result = []
    for row in envelope.get("records", []):
        values = row.get("values", {})
        if kind == "ff1" and values.get("code") in _DIAGNOSIS_CODES:
            payloads = {item["number"]: item for item in values.get("payloads", [])}
            legacy_values = values.get("legacy_values")
            if isinstance(legacy_values, dict):
                label = _LEGACY_LABELS[values["code"]]
                name = legacy_values.get(label)
                certainty = ff1_diagnosis_certainty(legacy_values, code=values["code"], label=label)
            else:
                name = payloads.get(9, {}).get("raw")
                modifiers = [(f"payload{index}", payloads.get(index, {}).get("raw"))
                             for index in range(5, 9) if payloads.get(index, {}).get("name") == "修飾語コード"]
                certainty = diagnosis_certainty(name, modifiers=modifiers)
            result.append({"source_row": row.get("source_row"), "source_kind": kind,
                           "role": values["code"], "icd10": payloads.get(2, {}).get("raw"),
                           "disease_name": name, **certainty})
        elif kind == "efg" and values.get("is_diagnosis_row"):
            name = values.get("item_name") or values.get("disease_name")
            result.append({"source_row": row.get("source_row"), "source_kind": kind,
                           "disease_name": name, **diagnosis_certainty(name)})
    return result


def select_diagnoses(diagnoses: Iterable[dict[str, Any]], *, suspected_policy: str = "include") -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if suspected_policy not in SUSPECTED_POLICIES:
        raise ValueError("invalid_suspected_policy")
    selected, excluded = [], []
    for diagnosis in diagnoses:
        (excluded if suspected_policy == "exclude" and diagnosis.get("certainty") == "suspected" else selected).append(diagnosis)
    return selected, excluded
