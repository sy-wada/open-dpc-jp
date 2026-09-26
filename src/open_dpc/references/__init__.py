"""Explicit, immutable reference snapshots. No bundled clinical master data."""
from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


def normalize_receipt_code(value: Any) -> str:
    """Normalize spreadsheet numeric cells without inventing missing zeroes."""
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value).strip()
    text = str(value).strip()
    return text[:-2] if text.endswith(".0") and text[:-2].isdigit() else text


def read_classification_csv(data: bytes, *, allow_legacy_placeholder: bool = False) -> dict[str, dict[str, str]]:
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline=""))
    if not reader.fieldnames or "receipt_code" not in reader.fieldnames:
        raise ValueError("classification_csv_missing_receipt_code")
    if len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError("classification_csv_duplicate_columns")
    result = {}
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise ValueError("classification_csv_invalid_row")
        code = row["receipt_code"].strip()
        if not (allow_legacy_placeholder and code == "-") and (not code or not code.isascii() or not code.isdigit()):
            raise ValueError("classification_csv_invalid_code")
        if code in result:
            raise ValueError("classification_csv_duplicate_code")
        result[code] = {key: value for key, value in row.items() if value != ""}
    return result


@dataclass(frozen=True)
class ReferenceSnapshot:
    dataset: str
    version: str
    sha256: str
    rows: Mapping[str, Mapping[str, str]]
    source: str = "user-supplied"
    valid_from: str | None = None
    valid_to: str | None = None
    hash_scope: str = "file-bytes"

    def __post_init__(self):
        if not self.dataset or not self.version:
            raise ValueError("reference_identity_required")
        if len(self.sha256) != 64 or any(c not in "0123456789abcdef" for c in self.sha256):
            raise ValueError("invalid_reference_sha256")
        if any(not isinstance(key, str) or not isinstance(value, str)
               for row in self.rows.values() for key, value in row.items()):
            raise ValueError("reference_attributes_must_be_strings")
        frozen = {str(code): MappingProxyType(dict(row)) for code, row in self.rows.items()}
        object.__setattr__(self, "rows", MappingProxyType(frozen))

    def metadata(self) -> dict[str, Any]:
        return {key: getattr(self, key) for key in (
            "dataset", "version", "sha256", "source", "valid_from", "valid_to", "hash_scope"
        )}

    def as_lookup(self) -> dict[str, dict[str, str]]:
        """Detached compatibility projection; editing it cannot change this snapshot."""
        return {code: dict(row) for code, row in self.rows.items()}


def load_reference(path: Path, *, dataset: str, version: str, source: str = "user-supplied",
                   valid_from: str | None = None, valid_to: str | None = None,
                   allow_legacy_placeholder: bool = False) -> ReferenceSnapshot:
    data = Path(path).read_bytes()
    return ReferenceSnapshot(dataset, version, hashlib.sha256(data).hexdigest(),
                             read_classification_csv(data, allow_legacy_placeholder=allow_legacy_placeholder),
                             source, valid_from, valid_to)


def snapshot_mapping(rows: Mapping[str, Mapping[str, str]], *, dataset: str,
                     version: str = "unversioned", source: str = "caller-supplied") -> ReferenceSnapshot:
    """Hash the parsed content when source bytes are unavailable (explicit scope)."""
    copied = {str(code): dict(row) for code, row in rows.items()}
    data = json.dumps(copied, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return ReferenceSnapshot(dataset, version, hashlib.sha256(data).hexdigest(), copied,
                             source=source, hash_scope="canonical-lookup")
