"""Disease-master resolution with a snapshot of the exact bytes parsed."""
import csv
from dataclasses import asdict
from functools import lru_cache
import hashlib
import io
from pathlib import Path

from open_dpc.disease_master import (
    DiseaseMaster, MASTER_FILENAME_PATTERN, _latest_master_path, _parse_master_rows,
)
from . import ReferenceSnapshot


@lru_cache(maxsize=4)
def _decode_snapshot(data, version):
    entries, warnings = _parse_master_rows(csv.reader(io.StringIO(data.decode("cp932"), newline="")))
    snapshot = ReferenceSnapshot("ssk-disease-master", version, hashlib.sha256(data).hexdigest(),
                                 {code: asdict(entry) for code, entry in entries.items()}, source="caller-selected-disease-master")
    return entries, warnings, snapshot


def load_disease_master_with_snapshot(reference_dir: Path | None, *, file_name=None):
    """Return (legacy-compatible master, immutable snapshot or None).

    No mtime-only cache: same-size replacement files must change the identity.
    A missing or unreadable source has no falsely asserted source-byte hash.
    """
    if reference_dir is None or not reference_dir.is_dir():
        return DiseaseMaster(warnings=[{"status": "disease_master_reference_dir_missing"}]), None
    if file_name is not None:
        match = MASTER_FILENAME_PATTERN.fullmatch(file_name)
        if not match:
            return DiseaseMaster(status="error", warnings=[{"status": "invalid_master_file_name"}]), None
        path, version = reference_dir / file_name, match.group(1)
    else:
        path, version = _latest_master_path(reference_dir)
    if path is None:
        return DiseaseMaster(warnings=[{"status": "disease_master_file_missing"}]), None
    try:
        data = path.read_bytes()
        entries, warnings, snapshot = _decode_snapshot(data, version)
    except (OSError, UnicodeError, csv.Error) as exc:
        return DiseaseMaster(status="error", file_name=path.name, version=version,
                             warnings=[{"status": "disease_master_read_failed", "error": str(exc)}]), None
    return DiseaseMaster(entries=dict(entries), status="warning" if warnings else "ok",
                         file_name=path.name, version=version, warnings=list(warnings)), snapshot
