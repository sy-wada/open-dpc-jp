"""Synthetic patient-list contract checks for the publication utility."""
import importlib.util
import csv
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "extraction" / "dpc_extractor.py"
if not SOURCE.exists():
    SOURCE = ROOT / "dpc_extraction_utilities" / "dpc_extractor.py"
spec = importlib.util.spec_from_file_location("dpc_extractor", SOURCE)
extractor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extractor)
HEADER = "pt_id,research_id,data_identifier,event_date,encounter_start_date,encounter_end_date\n"


class PatientListContract(unittest.TestCase):
    def write_list(self, directory, rows):
        path = Path(directory) / "pt_list.csv"
        path.write_text(HEADER + rows, encoding="utf-8-sig")
        return path

    def test_valid_bom_and_legacy_padding(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_list(directory, ",r_00001,123,20260102,20260101,20260110\n")
            result = extractor.load_pt_list(path)
            self.assertEqual(list(result), ["0000000123"])
            self.assertEqual(result["0000000123"]["research_id"], "r_00001")

    def test_rejects_duplicate_identifier_and_research_id(self):
        with tempfile.TemporaryDirectory() as directory:
            for rows in (
                ",r_1,1,,20260101,20260110\n,r_2,0000000001,,20260101,20260110\n",
                ",r_1,1,,20260101,20260110\n,r_1,2,,20260101,20260110\n",
            ):
                with self.subTest(rows=rows):
                    with self.assertRaises(ValueError):
                        extractor.load_pt_list(self.write_list(directory, rows))

    def test_rejects_invalid_identifier_date_and_path(self):
        with tempfile.TemporaryDirectory() as directory:
            for row in (
                ",r_1,1e3,,20260101,20260110\n",
                ",r_1,12345678901,,20260101,20260110\n",
                ",../escape,1,,20260101,20260110\n",
                ",CON,1,,20260101,20260110\n",
                ",r_1,1,,20260230,20260301\n",
                ",r_1,1,,20260110,20260101\n",
                ",r_1,1,,2026-01-01,20260110\n",
            ):
                with self.subTest(row=row):
                    with self.assertRaises(ValueError):
                        extractor.load_pt_list(self.write_list(directory, row))

    def test_invalid_list_creates_no_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.write_list(directory, ",../escape,1,,20260101,20260110\n")
            output = root / "outputs"
            with self.assertRaises(ValueError):
                extractor.main(root, str(path), "cp932", "\t", output_root=output, logger=lambda _: None)
            self.assertFalse(output.exists())

    def test_synthetic_extraction_filters_month_and_replaces_identifier(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            path = self.write_list(directory, ",r_00001,0000000123,20260102,20260101,20260110\n")
            (source / "EFn_synthetic_2601.txt").write_text(
                "年月\tデータ識別番号\t値\n"
                "2601\t0000000123\t合成\n"
                "2601\t9999999999\t除外\n", encoding="cp932")
            (source / "EFn_synthetic_2602.txt").write_text(
                "2602\t0000000123\t期間外\n", encoding="cp932")
            output = root / "outputs"
            result = extractor.main(source, str(path), "cp932", "\t", output_root=output,
                                    margin_before_days=0, margin_after_days=0,
                                    logger=lambda _: None, progress_callback=lambda _: None)
            self.assertEqual(result["total_files"], 1)
            self.assertEqual(result["total_extracted"], 1)
            with (output / "r_00001" / "2601" / "EFn_synthetic_2601.txt").open(encoding="cp932", newline="") as handle:
                rows = list(csv.reader(handle, delimiter="\t"))
            self.assertEqual(rows, [["年月", "データ識別番号", "値"], ["2601", "r_00001", "合成"]])
            self.assertFalse((output / "r_00001" / "2602").exists())


if __name__ == "__main__":
    unittest.main()
