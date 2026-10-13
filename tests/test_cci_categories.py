"""Independent Japanese category boundaries and pre-study revision contracts."""
from copy import deepcopy
from importlib.resources import files
import hashlib
import unittest

from open_dpc.semantics.comorbidity import calculate_charlson, load_definition, _validate


MIXED = {
    "F05": ["dementia"], "G04": ["hemiplegia_paraplegia"], "G11": ["hemiplegia_paraplegia"],
    "G31": ["dementia"], "G80": ["hemiplegia_paraplegia"], "G83": ["hemiplegia_paraplegia"],
    "H34": ["cerebrovascular_disease"], "I09": ["congestive_heart_failure"],
    "I11": ["congestive_heart_failure"], "I12": ["renal_disease"],
    "I13": ["congestive_heart_failure", "renal_disease"],
    "I25": ["myocardial_infarction", "congestive_heart_failure"], "I27": ["chronic_pulmonary_disease"],
    "I42": ["congestive_heart_failure"], "I73": ["peripheral_vascular_disease"],
    "I77": ["peripheral_vascular_disease"], "I79": ["peripheral_vascular_disease"],
    "I86": ["moderate_severe_liver_disease"], "I98": ["moderate_severe_liver_disease"],
    "J68": ["chronic_pulmonary_disease"], "J70": ["chronic_pulmonary_disease"],
    "K55": ["peripheral_vascular_disease"], "K71": ["mild_liver_disease", "moderate_severe_liver_disease"],
    "K72": ["moderate_severe_liver_disease"], "K76": ["mild_liver_disease", "moderate_severe_liver_disease"],
    "M31": ["rheumatic_disease"], "M35": ["rheumatic_disease"], "M36": ["rheumatic_disease"],
    "N03": ["renal_disease"], "N05": ["renal_disease"], "N25": ["renal_disease"],
    "P29": ["congestive_heart_failure"], "Z94": ["mild_liver_disease", "renal_disease"],
    "Z95": ["peripheral_vascular_disease"], "Z99": ["renal_disease"],
}


def revised(codes):
    return calculate_charlson(codes, definition="mirai-id-cci", version="1")


class CategoryTests(unittest.TestCase):
    def test_category_positives_and_minimum_weight_evidence(self):
        for code, condition, weight in [*( (f"E{i}", "diabetes_without_complication", 1) for i in range(10, 15)),
                                        ("K70", "mild_liver_disease", 1),
                                        ("I85", "moderate_severe_liver_disease", 3), ("Z49", "renal_disease", 2)]:
            with self.subTest(code=code):
                result = revised([code.lower()])
                self.assertEqual(result["score"], weight)
                ev = result["conditions"][condition]["evidence"][0]
                self.assertEqual(ev["match_type"], "exact_category")
                if code.startswith("E") or code == "K70":
                    self.assertEqual(ev["severity_status"], "unspecified")
                    self.assertEqual(ev["scoring_basis"], "minimum_weight")
                self.assertEqual(result["algorithm"]["version"], "2")

    def test_detailed_codes_and_severity_suppression_are_not_reclassified(self):
        for codes, expected in [(["E11", "E11.7", "E117"], 2), (["E11", "E119"], 1),
                                (["K70", "K704"], 3), (["K70", "K703"], 1)]:
            self.assertEqual(revised(codes)["score"], expected)
        self.assertFalse(revised(["E117"])["conditions"]["diabetes_without_complication"]["matched"])
        self.assertFalse(revised(["K704"])["conditions"]["mild_liver_disease"]["matched"])

    def test_i74_and_i983_extensions_with_negative_controls(self):
        for code in ["I74", "I740", "I741", "I742", "I743", "I744", "I74.5", "I748", "I749"]:
            self.assertTrue(revised([code])["conditions"]["peripheral_vascular_disease"]["matched"])
        for code in ["I730", "I770", "I80", "I82", "I26", "E11X", "K70X", "Z49X"]:
            self.assertEqual(revised([code])["score"], 0, code)
            self.assertEqual(revised([code])["category_evidence"], [])
        self.assertEqual(revised(["I98.3"])["score"], 3)

    def test_all_35_mixed_categories_are_related_not_positive(self):
        self.assertEqual(len(MIXED), 35)
        for code, expected in MIXED.items():
            with self.subTest(code=code):
                result = revised([code])
                self.assertEqual(result["score"], 0)
                self.assertFalse(any(c["matched"] for c in result["conditions"].values()))
                self.assertEqual(set(result["category_evidence"][0]["possible_conditions"]), set(expected))
                self.assertIn("insufficient_category_specificity", result["warnings"])

    def test_quan_and_archived_definition_keep_the_old_algorithm(self):
        archive = files("open_dpc.semantics.comorbidity").joinpath("definitions/archive/mirai-id-cci-v1-20260923.json")
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(),
                         "462fe404950ebe51e42c054d3819ce78f4aec34d9191050b9f5735817dd23e45")
        old = calculate_charlson(["E11", "I745"], definition=archive, version="1")
        self.assertEqual(old["score"], 0)
        self.assertEqual(old["algorithm"]["version"], "1")
        for code in ["E11", "I745", "I983", "K70", "I85", "Z49"]:
            quan = calculate_charlson([code])
            self.assertEqual(quan["score"], 0)
            self.assertEqual(quan["algorithm"]["version"], "1")
            self.assertNotIn("category_evidence", quan)

    def test_invalid_exact_codes_and_notes_are_rejected(self):
        spec, _ = load_definition("mirai-id-cci")
        for codes in [["E11", "E11"], ["E119"], [None], ["e11"]]:
            bad = deepcopy(spec)
            bad["conditions"]["diabetes_without_complication"]["exact_icd10_codes"] = codes
            with self.assertRaises(ValueError):
                _validate(bad)
        bad = deepcopy(spec)
        bad["conditions"]["mild_liver_disease"]["exact_code_notes"]["K71"] = {}
        with self.assertRaises(ValueError):
            _validate(bad)
