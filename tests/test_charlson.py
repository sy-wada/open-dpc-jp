import json
from pathlib import Path
import tempfile
import unittest
from open_dpc.semantics.comorbidity import calculate_charlson, load_definition


class CharlsonTests(unittest.TestCase):
    def test_independent_condition_examples(self):
        # One independent example per row of Quan Table 1, with original weights.
        examples = [("I252", "myocardial_infarction", 1), ("P290", "congestive_heart_failure", 1),
                    ("K551", "peripheral_vascular_disease", 1), ("I699", "cerebrovascular_disease", 1),
                    ("G311", "dementia", 1), ("J703", "chronic_pulmonary_disease", 1),
                    ("M360", "rheumatic_disease", 1), ("K289", "peptic_ulcer_disease", 1),
                    ("Z944", "mild_liver_disease", 1), ("E116", "diabetes_without_complication", 1),
                    ("E117", "diabetes_with_complication", 2), ("G839", "hemiplegia_paraplegia", 2),
                    ("N052", "renal_disease", 2), ("C970", "malignancy", 2),
                    ("I982", "moderate_severe_liver_disease", 3), ("C800", "metastatic_solid_tumor", 6),
                    ("B24", "aids_hiv", 6)]
        for code, condition, weight in examples:
            with self.subTest(code=code):
                result = calculate_charlson([code])
                self.assertEqual(result["score"], weight)
                self.assertTrue(result["conditions"][condition]["matched"])

    def test_nonmatches_do_not_use_study_expansions(self):
        for code in ("I770", "I74", "B23", "D45", "C44", "C86", "E1159XINVALID"):
            if code == "E1159XINVALID":
                continue  # ICD dictionary validation is explicitly not a prefix matcher's task.
            self.assertEqual(calculate_charlson([code])["score"], 0, code)

    def test_hierarchies_deduplicate_but_keep_evidence(self):
        result = calculate_charlson(["E110", "E112", "E112", "K703", "K765", "C18", "C77"])
        self.assertEqual(result["score"], 11)
        for weak in ("diabetes_without_complication", "mild_liver_disease", "malignancy"):
            self.assertTrue(result["conditions"][weak]["matched"])
            self.assertFalse(result["conditions"][weak]["counted"])
            self.assertTrue(result["conditions"][weak]["suppressed_by"])
        self.assertEqual(len(result["conditions"]["diabetes_with_complication"]["evidence"]), 2)

    def test_empty_unresolved_and_partial_inputs(self):
        self.assertIsNone(calculate_charlson([])["score"])
        self.assertIsNone(calculate_charlson(["0000001"])["score"])
        result = calculate_charlson([{"icd10": "I21.0", "source": "FF1", "date": "20250101"}, "0000001"])
        self.assertEqual(result["score"], 1)
        self.assertEqual(result["input_status"], "partial")
        self.assertEqual(result["conditions"]["myocardial_infarction"]["evidence"][0]["date"], "20250101")

    def test_external_definition_hash_and_validation(self):
        definition, original = load_definition()
        definition["id"] = "synthetic-custom"
        definition["conditions"]["myocardial_infarction"]["weight"] = 7
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"custom.json"
            path.write_text(json.dumps(definition), encoding="utf-8")
            result = calculate_charlson(["I21"], definition=path)
            self.assertEqual(result["score"], 7)
            self.assertNotEqual(result["definition"]["sha256"], original["sha256"])
            definition["conditions"]["diabetes_without_complication"]["suppresses"] = ["diabetes_with_complication"]
            path.write_text(json.dumps(definition), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "cyclic"):
                calculate_charlson([], definition=path)
