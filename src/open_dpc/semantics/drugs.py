"""Drug annotations using caller-selected reference data."""
from .classification import annotate


def annotate_drugs(records, *, reference):
    return annotate(records, reference=reference, kind="drug")
