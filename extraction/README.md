# DPC extraction utilities

The Python and PowerShell scripts in this directory are utilities separate from the `open_dpc_jp` library API. They read a local DPC source directory and a `pt_list.csv` following the [Patient List CSV specification](../docs/specifications/patient-list.md). They write patient-specific files under `outputs/<research_id>/<YYMM>/` and replace the DPC identifier with the research ID.

```bash
python extraction/dpc_extractor.py --path-to-dir <source-dir> --target-sheet pt_list.csv --output-root outputs
```

The default DPC file encoding is cp932, delimiter is tab, and the date margin is 90 days on either side. Inspect output locally before using it in research. Never upload patient lists or extracted files to a public issue.

The PowerShell wrapper is an alternative fast implementation. It must pass the same synthetic contract checks before release; the Python and PowerShell outputs should be compared for the same input and options.

Filename matching is case-insensitive for FF1/EFn/EFg and `.txt`. The third
underscore-separated token accepts YYMM (interpreted as 20YYMM) or YYYYMM,
including suffixes such as `2504-1`, `202504-1`, `2504_1` and `202504_1`.
The leading ASCII digit run must contain exactly four or six digits and a valid
month (01–12, year greater than zero). Invalid filename-month counts are logged.
File selection and patient-specific selection both compare full YYYYMM.

Output directories always use YYMM; original filenames are retained:
`EFn_999999999_202504.txt` becomes
`outputs/r_00001/2504/EFn_999999999_202504.txt`. Data cells containing dates are
not converted. Mixed four/six-digit names are supported in the same input tree.
ZIP files must already be expanded.

Previously, six-digit months were tested using their first four characters and
suffix-bearing months failed patient-specific selection. Re-extract into a new,
empty output directory, verify it locally, then select it in the application.
Keep previous output for recovery; no migration or deduplication is performed.
Identical original filenames from different input directories retain the existing
overwrite behavior. Different filenames for the same month remain separate.
Support for filenames does not establish compatibility with changed file contents.
