[日本語 README](README_ja.md)

# Open DPC JP

**Open Diagnosis Procedure Combination for Japan** is a Python library for structurally reading Japanese DPC FF1 and EF data with explicit year and revision profiles. It also provides versioned Charlson Comorbidity Index definitions. The first public release is `0.1.0`.

## Scope

The core interface is a library API. DPC extraction scripts are separate utilities in this repository. The browser-only Patient List Generator creates the CSV those scripts consume. The library does not include clinical patient data, official master files, CaseCurator application rules, storage, or REDCap exports. Structural parsing is not a complete DPC submission or clinical validity check.

## Installation

Python 3.12 or newer is required.

```bash
python -m pip install open-dpc-jp
```

## Quick start

```python
from pathlib import Path
from open_dpc_jp.parsing import parse_ef, parse_ff1

ef = parse_ef(Path("EFn.txt"), source_kind="efn", dataset_year=2025)
ff1 = parse_ff1(Path("FF1.txt"), schema_id="dpc-2025-20250530")
print(ef["diagnostics"], ff1["schema"])
```

## Supported data and documentation

Versioned structural profiles cover DPC years 2014–2026, with explicit revisions where needed. Source coverage and limits are recorded in `spec/dpc/source_ledger.json`. See the [Japanese documentation](https://open-dpc-jp.pages.dev/) for usage, methods, supported inputs, extraction, and the Patient List CSV contract. The [documentation source](docs/index.md) is also available in this repository.

## License and citation

Project-owned code is offered under [MIT](LICENSE). See [NOTICE](NOTICE.md) for its scope and third-party sources. Third-party publications, official DPC data and master files are not relicensed. See [CITATION.cff](CITATION.cff) for citation metadata and cite the original methods and DPC specification where applicable.
