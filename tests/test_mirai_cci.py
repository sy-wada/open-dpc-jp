"""Scientific definition and public version-resolution regressions."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from open_dpc.semantics.comorbidity import CharlsonEvaluator, calculate_charlson, load_definition


ROOT = Path(__file__).resolve().parents[1]
QUAN_SHA256 = "ba7a0c1a231d05cd37e5bbeb9962d13b5c270dfed92983fd970ce04439aecf1d"


class MiraiCciTests(unittest.TestCase):
    def test_complete_definition_is_quan_plus_three_documented_prefixes(self):
        quan, quan_identity = load_definition("quan-2005", version="1")
        mirai, mirai_identity = load_definition("mirai-id-cci", version="1")
        self.assertEqual(len(quan["conditions"]), 17)
        self.assertEqual(set(mirai["conditions"]), set(quan["conditions"]))
        additions = {"malignancy": {"C86", "D45"}, "aids_hiv": {"B23"}}
        for name, expected in quan["conditions"].items():
            actual = mirai["conditions"][name]
            self.assertEqual(set(actual["icd10_prefixes"]), set(expected["icd10_prefixes"]) | additions.get(name, set()), name)
            self.assertEqual(actual["weight"], expected["weight"], name)
            self.assertEqual(actual.get("suppresses", []), expected.get("suppresses", []), name)
        self.assertEqual(mirai["weighting"], quan["weighting"])
        self.assertEqual(mirai["derived_from"]["id"], "quan-2005")
        self.assertFalse(mirai["standard"])
        self.assertEqual(quan_identity["sha256"], QUAN_SHA256)
        self.assertEqual(mirai_identity["sha256"], hashlib.sha256(
            (ROOT / "spec/semantics/mirai-id-cci-v1.json").read_bytes()).hexdigest())
        self.assertEqual((ROOT / "spec/semantics/quan-2005.json").read_bytes(),
                         (ROOT / "src/open_dpc/semantics/comorbidity/definitions/quan-2005.json").read_bytes())

    def test_membership_boundaries_and_no_extension_leakage(self):
        cases = {
            "peripheral_vascular_disease": {"yes": ["I731", "I738", "I739", "I771", "K551", "Z958"],
                                            "no": ["I730", "I740", "I772"]},
            "cerebrovascular_disease": {"yes": ["H340", "I650", "I660", "I670", "I680", "I690"]},
            "diabetes_with_complication": {"yes": ["E102", "E105", "E107"], "no": ["E106", "E108"]},
            "diabetes_without_complication": {"yes": ["E106", "E108"], "no": ["E102", "E105", "E107"]},
            "malignancy": {"yes": ["C430", "C860", "D45"], "no": ["C440", "C800"]},
            "metastatic_solid_tumor": {"yes": ["C770", "C790", "C800"]},
            "aids_hiv": {"yes": ["B20", "B22", "B230", "B231", "B232", "B238", "B24"], "no": ["Z21"]},
        }
        for condition, groups in cases.items():
            for expectation, codes in groups.items():
                for code in codes:
                    with self.subTest(condition=condition, code=code):
                        self.assertEqual(calculate_charlson([code], definition="mirai-id-cci")["conditions"][condition]["matched"],
                                         expectation == "yes")
        for code in ("B230", "C860", "D45"):
            self.assertEqual(calculate_charlson([code], definition="quan-2005")["score"], 0)
            self.assertGreater(calculate_charlson([code], definition="mirai-id-cci")["score"], 0)

    def test_resolution_path_and_instance_snapshot(self):
        spec, identity = load_definition("mirai-id-cci")
        self.assertEqual(identity, load_definition("mirai-id-cci", version="1")[1])
        self.assertEqual(calculate_charlson(["B23"], definition="mirai-id-cci"),
                         CharlsonEvaluator(definition="mirai-id-cci").evaluate(["B23"]))
        evaluator = CharlsonEvaluator(definition="mirai-id-cci")
        first = evaluator.evaluate(["B23"])
        first["definition"]["id"] = "modified"
        first["weighting"]["id"] = "modified"
        spec["conditions"]["aids_hiv"]["icd10_prefixes"].clear()
        self.assertEqual(evaluator.evaluate(["B23"])["definition"], identity)
        self.assertEqual(evaluator.evaluate(["B23"])["score"], 6)
        with self.assertRaises(AttributeError):
            evaluator._spec = {}
        with self.assertRaisesRegex(ValueError, "unknown_definition$"):
            load_definition("absent")
        with self.assertRaisesRegex(ValueError, "unknown_definition_version"):
            load_definition("mirai-id-cci", version="2")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "external.json"
            path.write_text(json.dumps(load_definition("mirai-id-cci")[0]), encoding="utf-8")
            external = CharlsonEvaluator(definition=path, version="1")
            path.write_text("{}", encoding="utf-8")
            self.assertEqual(external.evaluate(["B23"])["score"], 6)
            with self.assertRaisesRegex(ValueError, "definition_version_mismatch"):
                load_definition(ROOT / "spec/semantics/mirai-id-cci-v1.json", version="2")


if __name__ == "__main__":
    unittest.main()
