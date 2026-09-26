"""Audit local DPC source PDFs against spec/dpc/source_ledger.json.

The PDFs stay outside normal package distribution. This tool records the
content hash in the ledger only when a local audit copy is supplied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit(root: Path, audit_dir: Path, *, update: bool = False) -> int:
    ledger_path = root / "spec/dpc/source_ledger.json"
    ledger = _read(ledger_path)
    failures = 0
    for source in ledger["sources"]:
        filename = Path(source["local_path"].replace("\\", "/")).name if source.get("local_path") else f"{source['year']}-{source['revision']}.pdf"
        path = audit_dir / filename
        if not path.is_file():
            print(f"MISSING\t{source['source_id']}\t{path}")
            continue
        digest = _hash(path)
        expected = source.get("sha256")
        if expected and expected != digest:
            print(f"MISMATCH\t{source['source_id']}\texpected={expected}\tactual={digest}")
            failures += 1
            continue
        print(f"OK\t{source['source_id']}\t{digest}")
        if update:
            source["sha256"] = digest
            source["status"] = "verified-local-audit-copy"
            source["local_path"] = str(path.relative_to(root))
    if update:
        ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-dir", type=Path, default=Path("audit-sources/dpc"))
    parser.add_argument("--update", action="store_true")
    args = parser.parse_args()
    package_root = Path(__file__).resolve().parents[1]
    raise SystemExit(audit(package_root, (package_root / args.audit_dir).resolve(), update=args.update))
