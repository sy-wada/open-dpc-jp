"""Procedure annotations using caller-selected reference data."""
from .classification import annotate


def annotate_procedures(records, *, reference):
    return annotate(records, reference=reference, kind="procedure")
