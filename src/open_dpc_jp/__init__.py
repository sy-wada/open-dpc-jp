"""Public Open DPC JP namespace, backed by the legacy-compatible core."""
import importlib
import sys

__version__ = "0.1.0"

_ALIASES = (
    "parsing", "schemas", "references", "references.disease", "semantics",
    "semantics.drugs", "semantics.procedures", "semantics.diagnosis",
    "semantics.classification", "semantics.comorbidity", "ef", "discovery",
    "disease_master", "master_archive", "medication_periods", "variables",
    "ff1_all_payloads",
)

for _name in _ALIASES:
    sys.modules[f"{__name__}.{_name}"] = importlib.import_module(f"open_dpc.{_name}")

del _name, _ALIASES, importlib, sys
