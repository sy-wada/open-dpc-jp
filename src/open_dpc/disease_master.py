"""Load the SSK disease-name master and resolve receipt codes to ICD-10."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

MASTER_FILENAME_PATTERN = re.compile(r"^b_(\d{8})\.txt$", re.IGNORECASE)
EXPECTED_COLUMN_COUNT = 46


def normalize_icd10(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().upper().replace(".", "").replace("-", "")


@dataclass(frozen=True)
class DiseaseMasterEntry:
    disease_code: str
    disease_name: str
    icd10_primary: str
    icd10_secondary: str


@dataclass(frozen=True)
class DiagnosisCodeResolution:
    icd10: str
    source: str
    disease_code: str
    dpc_icd10: str
    master_icd10: str
    master_icd10_secondary: str
    master_disease_name: str

    def event_metadata(self) -> dict[str, str]:
        return {
            "icd10_source": self.source,
            "dpc_icd10": self.dpc_icd10,
            "master_icd10": self.master_icd10,
            "master_icd10_secondary": self.master_icd10_secondary,
            "master_disease_name": self.master_disease_name,
        }


@dataclass
class DiseaseMaster:
    entries: dict[str, DiseaseMasterEntry] = field(default_factory=dict)
    status: str = "missing"
    file_name: str | None = None
    version: str | None = None
    warnings: list[dict[str, Any]] = field(default_factory=list)

    def resolve(self, disease_code: Any, dpc_icd10: Any = None) -> DiagnosisCodeResolution:
        code = str(disease_code or "").strip()
        source_icd10 = normalize_icd10(dpc_icd10)
        receipt_fallback = normalize_icd10(code)
        # EFg currently carries the receipt code in its icd10 slot. Treat that as
        # a fallback code rather than claiming it was supplied as a real ICD-10.
        if source_icd10 == receipt_fallback and code.isdigit() and len(code) == 7:
            source_icd10 = ""
        entry = self.entries.get(code)
        master_icd10 = entry.icd10_primary if entry else ""
        if master_icd10:
            resolved = master_icd10
            source = "master"
        elif source_icd10:
            resolved = source_icd10
            source = "dpc"
        else:
            resolved = receipt_fallback or "-"
            source = "receipt_code"
        return DiagnosisCodeResolution(
            icd10=resolved,
            source=source,
            disease_code=code,
            dpc_icd10=source_icd10,
            master_icd10=master_icd10,
            master_icd10_secondary=entry.icd10_secondary if entry else "",
            master_disease_name=entry.disease_name if entry else "",
        )

    def summary(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "file_name": self.file_name,
            "version": self.version,
            "record_count": len(self.entries),
            "warnings": self.warnings,
        }


def _latest_master_path(reference_dir: Path) -> tuple[Path | None, str | None]:
    candidates: list[tuple[str, Path]] = []
    if reference_dir.is_dir():
        for path in reference_dir.iterdir():
            match = MASTER_FILENAME_PATTERN.match(path.name)
            if path.is_file() and match:
                candidates.append((match.group(1), path))
    if not candidates:
        return None, None
    version, path = max(candidates, key=lambda item: item[0])
    return path, version


@lru_cache(maxsize=8)
def _read_master_cached(
    path_string: str, size: int, mtime_ns: int
) -> tuple[dict[str, DiseaseMasterEntry], tuple[dict[str, Any], ...]]:
    _ = size, mtime_ns
    with Path(path_string).open("r", encoding="cp932", newline="") as handle:
        return _parse_master_rows(csv.reader(handle))


def _parse_master_rows(rows):
    entries: dict[str, DiseaseMasterEntry] = {}
    invalid_rows = 0
    invalid_samples: list[int] = []
    for line_no, row in enumerate(rows, start=1):
        if (
            len(row) != EXPECTED_COLUMN_COUNT
            or row[1].upper() != "B"
            or len(row[2]) != 7
            or not row[2].isdigit()
        ):
            invalid_rows += 1
            if len(invalid_samples) < 5:
                invalid_samples.append(line_no)
            continue
        code = row[2]
        entries[code] = DiseaseMasterEntry(
            disease_code=code,
            disease_name=row[5].strip(),
            icd10_primary=normalize_icd10(row[15]),
            icd10_secondary=normalize_icd10(row[16]),
        )
    warnings: list[dict[str, Any]] = []
    if invalid_rows:
        warnings.append(
            {
                "status": "invalid_disease_master_rows",
                "count": invalid_rows,
                "sample_lines": invalid_samples,
            }
        )
    return entries, tuple(warnings)


def load_disease_master(reference_dir: Path | None, *, file_name: str | None = None) -> DiseaseMaster:
    """Return the newest usable disease master without making it a blocking dependency."""
    if reference_dir is None or not reference_dir.is_dir():
        return DiseaseMaster(
            warnings=[{"status": "disease_master_reference_dir_missing"}]
        )
    if file_name is not None:
        match = MASTER_FILENAME_PATTERN.fullmatch(file_name)
        if not match:
            return DiseaseMaster(status="error", warnings=[{"status": "invalid_master_file_name"}])
        path, version = reference_dir / file_name, match.group(1)
    else:
        path, version = _latest_master_path(reference_dir)
    if path is None:
        return DiseaseMaster(
            warnings=[{"status": "disease_master_file_missing"}]
        )
    try:
        stat = path.stat()
        entries, warnings = _read_master_cached(
            str(path.resolve()), stat.st_size, stat.st_mtime_ns
        )
    except (OSError, UnicodeError, csv.Error) as exc:
        return DiseaseMaster(
            status="error",
            file_name=path.name,
            version=version,
            warnings=[{"status": "disease_master_read_failed", "error": str(exc)}],
        )
    return DiseaseMaster(
        entries=entries,
        status="warning" if warnings else "ok",
        file_name=path.name,
        version=version,
        warnings=list(warnings),
    )
