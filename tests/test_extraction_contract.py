"""Synthetic patient-list contract checks for the publication utility."""
import importlib.util
import csv
from pathlib import Path
import tempfile
import unittest
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "extraction" / "dpc_extractor.py"
if not SOURCE.exists():
    SOURCE = ROOT / "dpc_extraction_utilities" / "dpc_extractor.py"
spec = importlib.util.spec_from_file_location("dpc_extractor", SOURCE)
extractor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extractor)
HEADER = "pt_id,research_id,data_identifier,event_date,encounter_start_date,encounter_end_date\n"


class FilenameMonthContract(unittest.TestCase):
    """Generated synthetic rows exercise both implementations with identical inputs."""

    def prepare(self, root):
        source = root / "source" / "deep" / "nested"
        source.mkdir(parents=True)
        patient_list = root / "pt_list.csv"
        patient_list.write_text(
            HEADER + ",r_dec,0000000123,20251231,20251231,20251231\n"
            ",r_apr,0000000456,20260410,20260401,20260430\n",
            encoding="utf-8-sig",
        )
        accepted = ["2512", "202512", "2512-1", "202512-1", "2512_1", "202512_1",
                    "2601", "202601", "2604", "202604"]
        invalid = ["20251", "2025120", "20251201", "202500", "202513", "2513",
                   "000001", "month", "２５１２"]
        outside = ["2511", "202511", "202602", "192512", "212512"]
        for kind in ("FF1", "efn", "eFg"):
            for token in accepted + invalid + outside:
                (source / f"{kind}_synthetic_{token}.TXT").write_text(
                    "年月\tデータ識別番号\t値\n"
                    "unchanged\t0000000123\t合成A\n"
                    "unchanged\t0000000456\t合成B\n"
                    "unchanged\t9999999999\t対象外\n", encoding="cp932",
                )
            (source / f"{kind}_missing.txt").write_text("not opened", encoding="cp932")
        return source.parents[1], patient_list, accepted, len(invalid) * 3 + 3

    def extract(self, source, patient_list, output, margin=1):
        logs = []
        result = extractor.main(source, str(patient_list), "cp932", "\t", output_root=output,
                                margin_before_days=margin, margin_after_days=margin,
                                logger=logs.append, progress_callback=lambda _: None)
        return result, logs

    def snapshot(self, output):
        result = {}
        for path in output.rglob("*"):
            if path.is_file():
                with path.open(encoding="utf-8-sig" if path.suffix == ".csv" else "cp932", newline="") as f:
                    result[path.relative_to(output).as_posix()] = list(csv.reader(
                        f, delimiter="," if path.suffix == ".csv" else "\t"))
        return result

    def test_mixed_filename_months_and_patient_periods(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, patients, accepted, invalid_count = self.prepare(root)
            output = root / "output"
            result, logs = self.extract(source, patients, output)
            self.assertEqual(result["total_files"], len(accepted) * 3)
            self.assertEqual(result["total_extracted"], len(accepted) * 3)
            self.assertEqual(result["error_files"], [])
            self.assertIn(f"不正なファイル名年月による除外数: {invalid_count}", logs)
            snapshot = self.snapshot(output)
            self.assertEqual(len(snapshot), len(accepted) * 3 + 1)
            for kind in ("FF1", "efn", "eFg"):
                for token in accepted:
                    month = "2604" if token in ("2604", "202604") else (
                        "2601" if token in ("2601", "202601") else "2512")
                    rid, value = ("r_apr", "合成B") if month == "2604" else ("r_dec", "合成A")
                    self.assertEqual(snapshot[f"{rid}/{month}/{kind}_synthetic_{token}.TXT"],
                                     [["年月", "データ識別番号", "値"], ["unchanged", rid, value]])
            self.assertEqual(snapshot["summary.csv"], [
                ["research_id", "FF1", "EFn", "EFg"], ["r_apr", "2", "2", "2"],
                ["r_dec", "8", "8", "8"],
            ])
            # With no margin, January must no longer be selected for r_dec.
            no_margin, _ = self.extract(source, patients, root / "no-margin", margin=0)
            self.assertEqual(no_margin["total_files"], (len(accepted) - 2) * 3)

    @unittest.skipUnless(sys.platform == "win32" and shutil.which("powershell.exe"),
                         "Windows PowerShell 5.1 required")
    def test_windows_powershell_matches_python(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, patients, _, invalid_count = self.prepare(root)
            script = SOURCE.with_name("dpc_extractor_fast.ps1")
            for margin in (0, 1):
                with self.subTest(margin=margin):
                    python_output = root / f"python-{margin}"
                    ps_output = root / f"powershell-{margin}"
                    self.extract(source, patients, python_output, margin=margin)
                    completed = subprocess.run([
                        "powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                        "-File", str(script), "-PathToDir", str(source), "-TargetSheet", str(patients),
                        "-OutputRoot", str(ps_output), "-MarginDays", str(margin),
                    ], capture_output=True, timeout=120)
                    self.assertEqual(completed.returncode, 0, completed.stderr.decode(errors="replace"))
                    self.assertEqual(self.snapshot(ps_output), self.snapshot(python_output))
                    log = completed.stdout.decode("utf-8", errors="replace")
                    if "不正なファイル名年月" not in log:
                        log = completed.stdout.decode("cp932", errors="replace")
                    self.assertIn(f"不正なファイル名年月による除外数: {invalid_count}", log)

    def test_six_digit_year_is_not_a_four_digit_month(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            # 201204 must not be opened as YYMM=2012 (December 2020).
            (source / "EFn_synthetic_201204.txt").write_text(
                "x\t0000000123\t合成\n", encoding="cp932")
            patients = root / "pt.csv"
            patients.write_text(HEADER + ",r_1,0000000123,,20200101,20201231\n", encoding="utf-8-sig")
            result, _ = self.extract(source, patients, root / "output", margin=0)
            self.assertEqual(result["total_files"], 0)
            self.assertEqual(result["total_extracted"], 0)


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
