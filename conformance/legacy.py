"""Synthetic contract-1 vectors; expected results are frozen, never auto-updated."""
from pathlib import Path
import csv
import tempfile

from open_dpc.ef import EF_COLUMNS, read_ef_file
from open_dpc.ff1_all_payloads import (
    CSV_COLUMNS, ALL_REGISTERED_CODES, extract_info_from_dpc_ff1,
    extract_info_from_dpc_ff1_flat,
)
from open_dpc.disease_master import load_disease_master


def run_vectors():
    output = {}
    with tempfile.TemporaryDirectory(prefix="open-dpc-contract-") as directory:
        root = Path(directory)
        rows = []
        for code in sorted(ALL_REGISTERED_CODES):
            row = [""] * 17
            row[:8] = ["000000001", "SYNTHETIC", "20250101", "1", "0", code, "1", "1"]
            if code == "A000010":
                row[8:10] = ["19700102", "1"]
            rows.append(row)
        path = root / "FF1_synthetic.txt"
        with path.open("w", encoding="cp932", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t")
            writer.writerow(CSV_COLUMNS)
            writer.writerows(rows)
        for raw in (True, False):
            output[f"ff1_raw_{raw}"] = extract_info_from_dpc_ff1(str(path), include_raw_payloads=raw, event_date="20250101")
        output["ff1_flat"] = extract_info_from_dpc_ff1_flat(str(path), event_date="20250101")
        for kind in ("efn", "efg"):
            rows = []
            for date, category, count in (("20250123", "21", "7"), ("20250100", "32", "1"), ("20250000", "SY", ""), ("20250230", "99", "-1")):
                row = [""] * len(EF_COLUMNS)
                row[0:2] = ["000000001", "SYNTHETIC"]
                row[4], row[6], row[8], row[10], row[16], row[20], row[23] = category, "001", "000000123", "合成", "1234567", count, date
                rows.append(row)
            path = root / f"{kind}_synthetic.txt"
            for header in (True, False):
                with path.open("w", encoding="cp932", newline="") as handle:
                    writer = csv.writer(handle, delimiter="\t")
                    if header:
                        writer.writerow(EF_COLUMNS)
                    writer.writerows(rows)
                result = read_ef_file(path)
                result["sourcePath"] = path.name
                output[f"{kind}_header_{header}"] = result
        master_root = root / "master"
        master_root.mkdir()
        output["missing_master"] = load_disease_master(master_root).status
        row = [""] * 46
        row[0], row[1], row[2], row[5], row[15] = "0", "B", "0000001", "合成病名", "I21.0"
        with (master_root / "b_20250101.txt").open("w", encoding="cp932", newline="") as handle:
            csv.writer(handle).writerow(row)
        from dataclasses import asdict
        master = load_disease_master(master_root)
        output["master_resolved"] = asdict(master.resolve("0000001", "B99"))
        output["master_unresolved"] = asdict(master.resolve("9999999", "B99"))
    return output
