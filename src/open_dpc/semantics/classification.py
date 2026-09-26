"""Deterministic table lookup; meaning belongs to the supplied reference."""
from __future__ import annotations

import hashlib
from typing import Any, Iterable
from open_dpc.references import ReferenceSnapshot, normalize_receipt_code
from open_dpc.semantics import SEMANTIC_RESULT_VERSION


def annotate(records: Iterable[dict[str, Any]], *, reference: ReferenceSnapshot | None,
             kind: str) -> list[dict[str, Any]]:
    results = []
    for index, record in enumerate(records):
        raw = record.get("receipt_code", record.get("standardCode", ""))
        code = normalize_receipt_code(raw)
        status = "unmapped"
        match = None
        if not code or not code.isascii() or not code.isdigit():
            status = "invalid_code"
        elif reference is None:
            status = "reference_missing"
        else:
            match = reference.rows.get(code)
            if match is not None:
                status = "matched"
        concept = None
        if match is not None:
            label = match.get(f"{kind}_category", match.get("label", ""))
            # A supplied concept is reference-local, never claimed as ATC or another ontology.
            concept_id = match.get("concept_id") or (
                "label-" + hashlib.sha256(label.encode("utf-8")).hexdigest()[:20]
                if label else "receipt-" + code
            )
            concept = {"namespace": reference.dataset, "concept_id": concept_id,
                       "label": label, "attributes": dict(match)}
        results.append({
            "semantic_result_version": SEMANTIC_RESULT_VERSION,
            "source": {"record_index": index, "code_system": "receipt", "code": raw,
                       "normalized_code": code},
            "annotation": concept,
            "resolution": {"status": status},
            "reference": reference.metadata() if reference else None,
            "algorithm": {"id": f"receipt-{kind}-lookup", "version": "1"},
        })
    return results
