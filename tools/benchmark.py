"""Same synthetic 100,000 rows, five repetitions; run each revision separately.

Install/select the desired revision outside this script. Output has no local
paths. Timing excludes generation and imports but includes normal reader work.
"""
import argparse
import csv
import gc
import json
from pathlib import Path
import platform
import statistics
import tempfile
import time

from open_dpc.ef import EF_COLUMNS, read_ef_file
from open_dpc.ff1_all_payloads import extract_info_from_dpc_ff1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--new-api", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="open-dpc-benchmark-") as folder:
        root = Path(folder)
        ef = root / "EFn_synthetic.txt"
        row = [""] * 31
        row[0:5] = ["000000000", "SYNTHETIC", "20250131", "20250101", "21"]
        row[8], row[10], row[16], row[20], row[23] = "123456789", "synthetic", "000000000000", "3", "20250101"
        ff = root / "FF1_synthetic.txt"
        ffrow = ["000000000", "SYNTHETIC", "20250101", "0", "1", "A000010", "20140401", "1", "19900101", "1"] + [""] * 7
        for path, cells in ((ef, row), (ff, ffrow)):
            with path.open("w", encoding="cp932", newline="") as handle:
                csv.writer(handle, delimiter="\t").writerows([cells] * 100_000)
        functions = {"ef_contract1": lambda: read_ef_file(ef, source_kind="efn"),
                     "ff1_contract1": lambda: extract_info_from_dpc_ff1(str(ff))}
        if args.new_api:
            from open_dpc.parsing import parse_ef, parse_ff1
            functions = {"ef_envelope": lambda: parse_ef(ef, source_kind="efn", dataset_year=2025),
                         "ff1_envelope": lambda: parse_ff1(ff, dataset_year=2025)}
        measurements = {}
        for name, call in functions.items():
            samples = []
            for _ in range(5):
                gc.collect()
                start = time.perf_counter()
                result = call()
                samples.append(time.perf_counter() - start)
                del result
            measurements[name] = {"seconds": samples, "median_seconds": statistics.median(samples)}
        print(json.dumps({"python": platform.python_version(), "platform": platform.system(),
                          "rows": 100_000, "repetitions": 5, "measurements": measurements}, sort_keys=True))


if __name__ == "__main__":
    main()
