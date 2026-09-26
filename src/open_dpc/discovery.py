"""DPC file discovery for case-scoped lazy loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

DPC_KINDS = ["ff1", "efn", "efg"]


def classify_dpc_file(path: Path) -> str | None:
    """Classify DPC file kind by lower-cased filename prefix."""
    name = path.name.lower()
    for kind in DPC_KINDS:
        if name.startswith(f"{kind}_"):
            return kind
    return None


def _month_tokens(case_context: dict[str, Any]) -> list[str]:
    tokens: list[str] = []
    for key in ["event_date", "encounter_start_date", "encounter_end_date"]:
        raw = str(case_context.get(key) or "")
        if len(raw) >= 6 and raw[:6].isdigit():
            tokens.append(raw[:6])
            tokens.append(raw[2:6])
    return tokens


def _identifier_tokens(case_context: dict[str, Any]) -> list[str]:
    tokens: list[str] = []
    for key in ["research_id", "data_identifier"]:
        value = str(case_context.get(key) or "").strip().lower()
        if value:
            tokens.append(value)
    return list(dict.fromkeys(tokens))


def discover_dpc_files_for_case(dpc_dir: Path, case_context: dict[str, Any]) -> dict[str, Any]:
    """Find DPC candidate files for a case without reading file contents."""
    result: dict[str, list[str]] = {kind: [] for kind in DPC_KINDS}
    warnings: list[dict[str, Any]] = []
    if not dpc_dir.exists():
        return {
            "dpc_files": result,
            "has_dpc": False,
            "warnings": [{"status": "dpc_dir_not_found", "path": str(dpc_dir)}],
        }
    if not dpc_dir.is_dir():
        return {
            "dpc_files": result,
            "has_dpc": False,
            "warnings": [{"status": "dpc_path_not_directory", "path": str(dpc_dir)}],
        }

    identifier_tokens = _identifier_tokens(case_context)
    month_tokens = [token.lower() for token in _month_tokens(case_context)]
    if not identifier_tokens:
        warnings.append({"status": "no_case_identifier_tokens"})
        return {"dpc_files": result, "has_dpc": False, "warnings": warnings}

    for path in sorted(dpc_dir.rglob("*")):
        if not path.is_file():
            continue
        kind = classify_dpc_file(path)
        if kind is None:
            continue
        haystack = str(path).lower()
        if any(token in haystack for token in identifier_tokens):
            result[kind].append(str(path))

    return {
        "dpc_files": result,
        "has_dpc": any(result.values()),
        "match_tokens": identifier_tokens,
        "month_tokens": month_tokens,
        "warnings": warnings,
    }
