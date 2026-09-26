# DPC extraction utilities

The Python and PowerShell scripts in this directory are utilities separate from the `open_dpc_jp` library API. They read a local DPC source directory and a `pt_list.csv` following the [Patient List CSV specification](../docs/specifications/patient-list.md). They write patient-specific files under `outputs/<research_id>/<YYMM>/` and replace the DPC identifier with the research ID.

```bash
python extraction/dpc_extractor.py --path-to-dir <source-dir> --target-sheet pt_list.csv --output-root outputs
```

The default DPC file encoding is cp932, delimiter is tab, and the date margin is 90 days on either side. Inspect output locally before using it in research. Never upload patient lists or extracted files to a public issue.

The PowerShell wrapper is an alternative fast implementation. It must pass the same synthetic contract checks before release; the Python and PowerShell outputs should be compared for the same input and options.
