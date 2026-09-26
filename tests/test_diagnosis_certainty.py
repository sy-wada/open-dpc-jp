import unittest
from pathlib import Path
import tempfile

from open_dpc.parsing import parse_ff1

from open_dpc.semantics.diagnosis import (
    diagnosis_certainty, diagnosis_observations, ff1_diagnosis_certainty,
    select_diagnoses,
)


class DiagnosisCertaintyTests(unittest.TestCase):
    def test_modifier_and_name_evidence(self):
        record = {"主傷病": "心不全", "A006010_payload5_raw": "1001",
                  "A006010_payload6_raw": "8002"}
        result = ff1_diagnosis_certainty(record, code="A006010", label="主傷病")
        self.assertEqual(result["certainty"], "suspected")
        self.assertEqual(result["certainty_evidence"][1]["field"], "A006010_payload6_raw")
        self.assertEqual(result["certainty_evidence"][1]["raw"], "8002")
        self.assertEqual(diagnosis_certainty("心不全", modifiers=[("code", "18002")])["certainty"], "not_marked_suspected")
        self.assertEqual(diagnosis_certainty(None, modifiers=[("code", "8OO2")])["certainty"], "unknown")
        self.assertEqual(diagnosis_certainty(None)["certainty"], "unknown")
        self.assertEqual(diagnosis_certainty("　心不全の疑い　")["certainty"], "suspected")
        self.assertEqual(diagnosis_certainty("心不全疑い")["certainty"], "suspected")
        self.assertEqual(diagnosis_certainty("心不全")["certainty"], "not_marked_suspected")

    def test_annual_and_legacy_use_same_certainty(self):
        payloads = [{"number": i, "name": "修飾語コード", "raw": "8002" if i == 7 else ""} for i in range(5, 9)]
        payloads += [{"number": 2, "raw": "I50"}, {"number": 9, "raw": "心不全"}]
        envelope = {"source": {"kind": "ff1"}, "records": [{"source_row": 3, "values": {
            "code": "A006010", "payloads": payloads}}]}
        annual = diagnosis_observations(envelope)[0]
        legacy = ff1_diagnosis_certainty({"主傷病": "心不全", "主傷病_修飾語コード": "1001|8002"}, code="A006010", label="主傷病")
        self.assertEqual(annual["certainty"], legacy["certainty"])
        self.assertEqual(annual["certainty"], "suspected")
        self.assertEqual(annual["source_row"], 3)

    def test_annual_file_parse_exposes_modifier_without_changing_parse_shape(self):
        row = ["279900249", "SYNTHETIC", "20240601", "0", "0", "A006010", "20140401", "1",
               "", "I50", "", "D123", "", "8002", "", "", "心不全"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "FF1.txt"
            path.write_text("\t".join(row), encoding="cp932")
            parsed = parse_ff1(path, dataset_year=2024, dataset_date="20240601")
            observations = diagnosis_observations(parsed)
        self.assertEqual(observations[0]["certainty"], "suspected")
        self.assertEqual(observations[0]["disease_name"], "心不全")
        self.assertEqual(parsed["records"][0]["values"]["payloads"][5]["raw"], "8002")

    def test_selection_does_not_mutate_and_unknown_remains(self):
        items = [{"icd10": "I50", "certainty": "suspected"}, {"icd10": "I50", "certainty": "unknown"}]
        selected, excluded = select_diagnoses(items, suspected_policy="exclude")
        self.assertEqual(selected, items[1:])
        self.assertEqual(excluded, items[:1])
        self.assertEqual(len(items), 2)
        with self.assertRaisesRegex(ValueError, "invalid_suspected_policy"):
            select_diagnoses(items, suspected_policy="confirmed_only")

    def test_efg_projection_reads_original_name(self):
        envelope = {"source": {"kind": "efg"}, "records": [
            {"source_row": 4, "values": {"is_diagnosis_row": True, "item_name": "心不全の疑い"}},
            {"source_row": 5, "values": {"is_diagnosis_row": False, "item_name": "心不全の疑い"}},
        ]}
        observations = diagnosis_observations(envelope)
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0]["certainty"], "suspected")
        self.assertEqual(observations[0]["certainty_evidence"][0]["raw"], "心不全の疑い")

    def test_legacy_envelope_uses_compatibility_values(self):
        envelope = {"source": {"kind": "ff1"}, "records": [{"source_row": 2, "values": {
            "code": "A006010", "payloads": [], "legacy_values": {
                "主傷病": "心不全", "主傷病_修飾語コード": "8002"}}}]}
        self.assertEqual(diagnosis_observations(envelope)[0]["certainty"], "suspected")


if __name__ == "__main__":
    unittest.main()
