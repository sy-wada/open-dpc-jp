import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from open_dpc.parsing import parse_ef, parse_ff1
from open_dpc.schemas import resolve_schema, legacy_schema, source_ledger
from open_dpc.ef import EF_COLUMNS, read_ef_file


class SchemaParsingTests(unittest.TestCase):
    def test_explicit_resolution_and_fallback(self):
        with self.assertRaisesRegex(ValueError, "explicit"):
            resolve_schema()
        with self.assertRaisesRegex(ValueError, "unsupported"):
            resolve_schema(dataset_year=2027)
        for year, selected in ((2027,2026), (2013,2014)):
            resolved = resolve_schema(dataset_year=year, allow_fallback=True)
            self.assertEqual(resolved.metadata()["parser_schema_year"], selected)
            self.assertEqual(resolved.resolution,"fallback")
            self.assertTrue(resolved.metadata()["warnings"])
        with self.assertRaisesRegex(ValueError, "schema_date_required"):
            resolve_schema(dataset_year=2026)
        self.assertEqual(resolve_schema(dataset_date="2026-07-17").schema_id, "dpc-2026-20260601")
        self.assertEqual(resolve_schema(schema_id="dpc-2026-20260717").metadata()["document_revision"], "20260717")
        self.assertEqual(resolve_schema(schema_id="legacy-mixed-v1").resolution,"legacy")

    def test_declared_compatibility_resolution_and_detached_metadata(self):
        # Exercise the contract with a synthetic registry declaration, without
        # asserting any real cross-year compatibility that was not audited.
        import open_dpc.schemas as schemas
        registry = json.loads(json.dumps(schemas._registry()))
        registry["schemas"][1]["compatible_input_years"] = [2030]
        with patch.object(schemas, "_registry", return_value=registry):
            result = resolve_schema(dataset_year=2030)
            self.assertEqual(result.resolution, "compatible")
            self.assertEqual(result.metadata()["parser_schema_year"], 2014)
        meta = resolve_schema(dataset_year=2025).metadata()
        meta["validation_scope"].clear()
        self.assertTrue(resolve_schema(dataset_year=2025).metadata()["validation_scope"])
        self.assertEqual(resolve_schema(dataset_year=2027, allow_fallback=True).metadata()["selection_reason"], "latest_preceding_year")
        self.assertEqual(resolve_schema(dataset_year=2013, allow_fallback=True).metadata()["selection_reason"], "earliest_subsequent_year")

    def test_effective_date_boundaries_and_date_inference(self):
        self.assertEqual(resolve_schema(dataset_date="2026-05-31").schema_id, "dpc-2026-20260401")
        self.assertEqual(resolve_schema(dataset_date="20260601").schema_id, "dpc-2026-20260601")
        self.assertEqual(resolve_schema(dataset_date="20260717").schema_id, "dpc-2026-20260601")
        with self.assertRaisesRegex(ValueError, "schema_date_required"):
            resolve_schema(dataset_year=2026)

    def test_official_annual_codes_and_applicability(self):
        for year, absent in ((2015, "FIM0010"), (2017, "A004020"),
                             (2017, "M180010"), (2019, "ADL0030"),
                             (2021, "M050070")):
            self.assertNotIn(absent, resolve_schema(dataset_year=year).definition["ff1"]["codes"])
        for year, present in ((2016, "FIM0010"), (2018, "A004020"),
                              (2020, "ADL0030"), (2022, "M050070")):
            self.assertIn(present, resolve_schema(dataset_year=year).definition["ff1"]["codes"])
        with self.assertRaisesRegex(ValueError, "schema_date_required"):
            resolve_schema(dataset_year=2024)
        self.assertEqual(resolve_schema(dataset_date="2024-05-31").schema_id, "dpc-2024-20240401")
        self.assertEqual(resolve_schema(dataset_date="2024-06-01").schema_id, "dpc-2024-20240601")
        self.assertNotIn("FIM0020", resolve_schema(dataset_date="2024-05-31").definition["ff1"]["codes"])
        self.assertIn("FIM0020", resolve_schema(dataset_date="2024-06-01").definition["ff1"]["codes"])
        self.assertEqual(resolve_schema(dataset_date="2026-06-01").metadata()["document_revision"], "20260325")

    def test_ef17_annual_positions_and_raw_preservation(self):
        old = resolve_schema(dataset_year=2016).definition["ef"]
        self.assertTrue(old["efn_ef17"]["positions"]["6"]["reserved"])
        self.assertTrue(old["efg_ef17"]["positions"]["3"]["reserved"])
        self.assertEqual(resolve_schema(dataset_year=2015).definition["ef"]["ef17_length"], 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "EF.txt"
            cells = [""] * 31
            cells[1], cells[4], cells[16], cells[23] = "SYNTHETIC", "21", "123456000000", "20160601"
            path.write_text("\t".join(cells), encoding="cp932")
            efg = parse_ef(path, source_kind="efg", dataset_year=2016)["records"][0]["values"]
            self.assertEqual(efg["ef17_raw"], "123456000000")
            self.assertEqual(efg["generic_prescription_flag"], "2")
            self.assertNotIn("sex_code", efg)
            self.assertNotIn("refill_prescription_flag", efg)
            efn = parse_ef(path, source_kind="efn", dataset_year=2016)["records"][0]["values"]
            self.assertNotIn("basic_lab_xray_inclusive_flag", efn)
            self.assertEqual(efn["ef17_raw"], "123456000000")

    def test_old_fixed_width_ef_uses_annual_width_and_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "old_ef.txt"
            for year, flag in ((2015, "1"), (2016, "123450000000")):
                spec = resolve_schema(dataset_year=year).definition["ef"]
                cells = [""] * len(spec["widths"])
                cells[1], cells[4], cells[16], cells[23] = "SYNTHETIC", "21", flag, f"{year}0601"
                path.write_text("".join(value.ljust(width) for value, width in zip(cells, spec["widths"])), encoding="cp932")
                result = parse_ef(path, source_kind="efn", dataset_year=year)
                self.assertEqual(result["records"][0]["values"]["ef17_raw"], flag)
                self.assertTrue(result["records"][0]["values"]["ef17_valid"])
                self.assertFalse(result["diagnostics"])
                values = result["records"][0]["values"]
                if year == 2015:
                    self.assertEqual(values["fee_for_service_inclusive_flag"], "1")
                else:
                    self.assertNotIn("basic_lab_xray_inclusive_flag", values)

    def test_ef_research_identifier_is_preserved_in_cp932_tsv_readers(self):
        research_id = "RESEARCH-ID_2026-00001"
        columns = resolve_schema(dataset_year=2025).definition["ef"]["columns"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "EFn_synthetic.txt"
            row = [""] * len(columns)
            row[1], row[4], row[23] = research_id, "21", "20250601"
            path.write_text(
                "\t".join(columns) + "\n" + "\t".join(row) + "\n",
                encoding="cp932",
            )

            legacy_record = read_ef_file(path)["records"][0]
            parsed = parse_ef(path, source_kind="efn", dataset_year=2025)
            parsed_record = parsed["records"][0]["values"]

            for record in (legacy_record, parsed_record):
                self.assertEqual(record["patient_id"], research_id)
                self.assertEqual(record["データ識別番号"], research_id)
            self.assertFalse(parsed["diagnostics"])

    def test_old_outpatient_columns_do_not_become_birth_or_visit_dates(self):
        spec = resolve_schema(dataset_year=2015).definition["ef"]
        self.assertEqual(spec["outpatient_columns"][2:4], ["退院年月日", "入院年月日"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "EFg.txt"
            cells = [""] * 31
            cells[1], cells[2], cells[3], cells[4] = "SYNTHETIC", "20150501", "20150401", "21"
            cells[13], cells[16], cells[23] = "10", "1", "20150501"
            for content in ("\t".join(spec["outpatient_source_columns"]) + "\n" +
                            "\t".join(cells),
                            "".join(value.ljust(width) for value, width in zip(cells, spec["widths"]))):
                path.write_text(content, encoding="cp932")
                result = parse_ef(path, source_kind="efg", dataset_year=2015)
                values = result["records"][0]["values"]
                self.assertEqual(values["退院年月日"], "20150501")
                self.assertEqual(values["入院年月日"], "20150401")
                self.assertEqual(values["amount_or_points"], "10")
                self.assertEqual(values["ef17_raw"], "1")
                self.assertNotIn("birth_date", values)
                self.assertNotIn("visit_date", values)
                self.assertNotIn("行為明細区分情報", values)
                self.assertFalse(result["diagnostics"])
            modern = [""] * 31
            modern[1], modern[2], modern[3], modern[4] = "SYNTHETIC", "19700101", "20180501", "21"
            modern[16], modern[23] = "120000000000", "20180501"
            path.write_text("\t".join(modern), encoding="cp932")
            current = parse_ef(path, source_kind="efg", dataset_year=2018)["records"][0]["values"]
            self.assertEqual(current["birth_date"], "19700101")
            self.assertEqual(current["visit_date"], "20180501")

    def test_older_year_unknown_code_remains_raw(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "FF1.txt"
            row = ["000000001", "SYNTHETIC", "20230501", "0", "0", "FIM0020", "20240601", "0", "raw"] + [""] * 8
            path.write_text("\t".join(row), encoding="cp932")
            result = parse_ff1(path, dataset_year=2023)
            self.assertIn("unknown_ff1_code", {item["code"] for item in result["diagnostics"]})
            self.assertEqual(result["records"][0]["values"]["payloads"][0]["raw"], "raw")
            self.assertIsNone(result["records"][0]["values"]["payloads"][0]["name"])

    def test_annual_registry_and_source_ledger_contract(self):
        registry = resolve_schema(schema_id="dpc-2014-20140501").metadata()
        self.assertEqual(registry["validation_status"], "structural-table-checked")
        self.assertFalse(registry["warnings"])
        ledger = source_ledger()
        source_ids = {item["source_id"] for item in ledger["sources"]}
        verified = [item for item in ledger["sources"] if item["status"].startswith("verified")]
        self.assertTrue(verified)
        self.assertTrue(all(len(item["sha256"]) == 64 for item in verified))
        self.assertEqual(next(item for item in ledger["sources"] if item["source_id"] == "dpc-2020-mhlw-candidate")["status"], "unavailable")
        for year in range(2014, 2027):
            selected = resolve_schema(dataset_date=f"{year}0701" if year != 2026 else "20260717")
            self.assertEqual(selected.metadata()["parser_schema_year"], year)
            self.assertTrue(set(selected.metadata()["source_ids"]).issubset(source_ids))
        self.assertEqual(resolve_schema(schema_id="dpc-2020-20200330").definition["sources"][0]["authority"], "dpc_office_primary")

    def test_filename_date_is_used_when_explicit_date_is_omitted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "EFn_2026-06-01.txt"
            path.write_text("\t".join([""] * 31), encoding="cp932")
            result = parse_ef(path, source_kind="efn")
            self.assertEqual(result["schema"]["id"], "dpc-2026-20260601")

    def test_annual_code_changes_and_detached_schema(self):
        old=resolve_schema(dataset_year=2025).definition
        new=resolve_schema(dataset_date="20260717").definition
        self.assertEqual(len(old["ff1"]["codes"]),70)
        self.assertEqual(len(new["ff1"]["codes"]),67)
        self.assertIn("A000021",new["ff1"]["codes"])
        self.assertNotIn("A000021",old["ff1"]["codes"])
        self.assertNotIn("A006060",new["ff1"]["codes"])
        old["ff1"]["codes"].clear()
        self.assertEqual(len(resolve_schema(dataset_year=2025).definition["ff1"]["codes"]),70)

    def test_ff1_retains_unknown_short_and_extra_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"ff1.txt"
            research_id = "RESEARCH-ID_2026-00001"
            rows=[["x"], ["", research_id, "", "", "", "UNKNOWN", "", "", "keep"]+[""]*8+["extra"]]
            path.write_text("\n".join("\t".join(row) for row in rows),encoding="cp932")
            result=parse_ff1(path,dataset_date="20260717")
            self.assertEqual(len(result["records"]),2)
            identifier_column = resolve_schema(dataset_date="20260717").definition["ff1"]["columns"][1]
            self.assertEqual(result["records"][1]["values"]["header"][identifier_column], research_id)
            self.assertEqual(result["source_rows"][1]["cells"][-1],"extra")
            self.assertIn("unknown_ff1_code",[d["code"] for d in result["diagnostics"]])
            self.assertEqual(result,parse_ff1(path,dataset_date="20260717"))
            json.dumps(result,allow_nan=False)

    def test_all_annual_payload_positions_have_source_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"ff1.txt"
            for year in (2025,2026):
                schema=resolve_schema(dataset_year=year, dataset_date="20260717" if year == 2026 else None).definition
                rows=[]
                for code,definition in schema["ff1"]["codes"].items():
                    row=["000000001","SYNTHETIC","20260601","0","0",code,definition["version"],"0"]+[""]*9
                    for number,field in definition["payloads"].items():
                        row[int(number)+7]="20260601" if field["type"]=="date" else "01"
                    rows.append(row)
                    self.assertIn(code,schema["source_coverage"]["ff1_payload_pdf_pages"])
                path.write_text("\n".join("\t".join(row) for row in rows),encoding="cp932")
                result=parse_ff1(path,dataset_year=year, dataset_date="20260717" if year == 2026 else None)
                self.assertEqual(len(result["records"]),len(rows))
                self.assertFalse(result["diagnostics"])
                self.assertEqual(result["records"][0]["values"]["payloads"][1]["value"],"01")

    def test_ef_duplicate_headers_invalid_date_and_extra_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"ef.txt"
            headers=list(EF_COLUMNS)+["診療明細名称"]
            row=[""]*len(headers)
            row[1],row[4],row[10],row[23],row[-1]="SYNTHETIC","XX","first","20250230","second"
            path.write_text("\t".join(headers)+"\n"+"\t".join(row+["overflow"]),encoding="cp932")
            result=parse_ef(path,source_kind="efn",dataset_year=2025)
            self.assertEqual(result["records"][0]["values"]["name"],"first")
            self.assertIsNone(result["records"][0]["values"]["eventDate"])
            self.assertEqual(result["source_rows"][1]["cells"][-2:],["second","overflow"])
            self.assertTrue({"duplicate_header","column_count_mismatch","invalid_calendar_date","unknown_data_category"}.issubset({d["code"] for d in result["diagnostics"]}))

    def test_invalid_encoding_is_lossless(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"ff1.txt"
            path.write_bytes(b"\x81")
            result=parse_ff1(path,dataset_year=2025)
            self.assertEqual(result["source"]["unparsed_bytes_base64"],"gQ==")
            self.assertEqual(result["records"],[])

    def test_ff1_duplicate_header_is_retained_and_diagnosed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "headers.txt"
            columns = resolve_schema(dataset_year=2025).definition["ff1"]["columns"]
            columns[-1] = columns[-2]
            path.write_text("\t".join(columns), encoding="cp932")
            result = parse_ff1(path, dataset_year=2025)
            self.assertEqual(result["source_rows"][0]["cells"], columns)
            self.assertTrue(result["source_rows"][0]["header"])
            self.assertEqual(result["records"], [])
            self.assertEqual({item["code"] for item in result["diagnostics"]},
                             {"duplicate_header", "header_schema_mismatch"})

    def test_previous_admission_special_values_are_not_invalid_dates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "previous.txt"
            row = ["", "SYNTHETIC", "20250601", "", "", "A000070", "20140401", "1", "99999999", "00000000"] + [""] * 7
            path.write_text("\t".join(row), encoding="cp932")
            for year in (2025, 2026):
                result = parse_ff1(path, dataset_year=year, dataset_date="20260717" if year == 2026 else None)
                payloads = result["records"][0]["values"]["payloads"]
                self.assertEqual(payloads[0]["special_value"], "no_previous_admission")
                self.assertEqual(payloads[1]["special_value"], "unknown")
                self.assertIsNone(payloads[0]["value"])
                self.assertFalse(result["diagnostics"])

    def test_malformed_quoted_record_retains_unparsed_remainder(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.txt"
            raw = '"unterminated\tfield\nsecond physical line'
            path.write_text(raw, encoding="cp932", newline="")
            for parse in (lambda: parse_ff1(path, dataset_year=2025),
                          lambda: parse_ef(path, source_kind="efn", dataset_year=2025)):
                result = parse()
                self.assertEqual(result["source"]["unparsed_text"], raw)
                self.assertEqual(result["diagnostics"][-1]["code"], "malformed_delimited_record")

    def test_zero_and_invalid_dates_never_leave_positionable_periods(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dates.txt"
            rows = []
            for date in ("00000000", "20250230", ""):
                row = [""] * 31
                row[1], row[4], row[23] = "SYNTHETIC", "21", date
                rows.append("\t".join(row))
            path.write_text("\n".join(rows), encoding="cp932")
            result = parse_ef(path, source_kind="efn", dataset_year=2025)
            self.assertEqual(len(result["records"]), 3)
            for record in result["records"]:
                self.assertIsNone(record["values"]["service_date"])
                self.assertIsNone(record["values"]["period_start_date"])
                self.assertIsNone(record["values"]["period_end_date"])

    def test_legacy_golden(self):
        directory=Path(__file__).resolve().parents[1]/"conformance"
        spec=importlib.util.spec_from_file_location("legacy_vectors",directory/"legacy.py")
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        expected=json.loads((directory/"legacy-v1.json").read_text(encoding="utf-8"))
        self.assertEqual(json.loads(json.dumps(module.run_vectors(),default=str)),expected)
