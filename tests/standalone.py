"""Dependency-free, isolated conformance smoke; run with python -I."""
import csv
import importlib.abc
from pathlib import Path
import sys
import tempfile
import unittest


class RejectApplication(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith("ckoseri_redcap_etl"):
            raise ImportError("open_dpc must not import the application")


sys.meta_path.insert(0, RejectApplication())
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from open_dpc.ef import EF_COLUMNS, read_ef_file
from open_dpc.ff1_all_payloads import CSV_COLUMNS, extract_info_from_dpc_ff1
from open_dpc.disease_master import load_disease_master


class StandaloneContracts(unittest.TestCase):
    def test_ef_sources_preserve_raw_codes_without_study_classification(self):
        with tempfile.TemporaryDirectory() as tmp:
            for kind in ("efn", "efg"):
                row = [""] * len(EF_COLUMNS)
                row[0:2] = ["000000001", "SYNTHETIC"]
                row[4], row[8], row[10], row[23] = "32", "000000123", "合成薬", "20240123"
                path = Path(tmp) / f"{kind}_synthetic.txt"
                path.write_text("\t".join(row) + "\n", encoding="cp932")
                result = read_ef_file(path)
                record = result["records"][0]
                self.assertEqual(record["receipt_code"], "000000123")
                self.assertEqual(record["eventDate"], "20240123")
                self.assertEqual(record["sourceKind"], kind)
                self.assertEqual(record[EF_COLUMNS[8]], "000000123")
                self.assertNotIn("drug_category", record)
                self.assertNotIn("medicationCandidates", result)

    def test_ff1_header_and_empty_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ff1_synthetic.txt"
            path.write_text("\t".join(CSV_COLUMNS) + "\n", encoding="cp932")
            result = extract_info_from_dpc_ff1(str(path))
            self.assertIsInstance(result, dict)
            row = [""] * len(CSV_COLUMNS)
            row[0], row[1], row[2], row[5], row[8] = "000000001", "SYNTHETIC", "20240120", "A000020", "20240120"
            path.write_text("\t".join(CSV_COLUMNS) + "\n" + "\t".join(row) + "\n", encoding="cp932")
            result = extract_info_from_dpc_ff1(str(path))
            self.assertEqual(len(result["A000020"]), 1)
            self.assertEqual(result["A000020"][0]["入院情報_ペイロード1_入院年月日"], "2024/01/20")

    def test_master_and_missing_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(load_disease_master(root).status, "missing")
            row = [""] * 46
            row[0], row[1], row[2], row[5], row[15] = "0", "B", "0000001", "合成病名", "A00.0"
            with (root / "b_20260101.txt").open("w", encoding="cp932", newline="") as handle:
                csv.writer(handle).writerow(row)
            master = load_disease_master(root)
            self.assertEqual(master.resolve("0000001").icd10, "A000")
            self.assertEqual(master.resolve("9999999", "B99").source, "dpc")


if __name__ == "__main__":
    unittest.main()
