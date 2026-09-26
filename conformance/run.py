"""Run from a copied conformance directory against an installed distribution.

No source-path injection, application imports, network or clinical input.
"""
import hashlib
import json
from pathlib import Path

from legacy import run_vectors
from open_dpc import __version__, CONTRACT_VERSION
from open_dpc.schemas import resolve_schema
from open_dpc.semantics.comorbidity import calculate_charlson


def main():
    root = Path(__file__).resolve().parent
    actual = run_vectors()
    expected = json.loads((root / "legacy-v1.json").read_text(encoding="utf-8"))
    if actual != expected:
        raise AssertionError("contract-1 golden mismatch")
    score = calculate_charlson(["I21.0", "C78.0", "C34.9"], definition="quan-2005")
    if score["score"] != 7:
        raise AssertionError("Charlson severity suppression mismatch")
    canonical = json.dumps(actual, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    print(json.dumps({"package": __version__, "contract": CONTRACT_VERSION,
                      "legacy_vector_sha256": hashlib.sha256(canonical).hexdigest(),
    "schemas": [resolve_schema(dataset_year=2025).metadata(),
                 resolve_schema(dataset_date="20260717").metadata()],
                      "charlson_score": score["score"]}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
