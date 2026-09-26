"""Independent compact transcription of Quan 2005, Table 1, printed p1133.

Ranges here follow the printed table; runtime JSON expands them explicitly.
Checking both representations detects missing, added and mistyped prefixes.
"""
import unittest
from open_dpc.semantics.comorbidity import calculate_charlson, load_definition

TABLE = {
    "myocardial_infarction": "I21 I22 I252",
    "congestive_heart_failure": "I099 I110 I130 I132 I255 I420 I425-I429 I43 I50 P290",
    "peripheral_vascular_disease": "I70 I71 I731 I738 I739 I771 I790 I792 K551 K558 K559 Z958 Z959",
    "cerebrovascular_disease": "G45 G46 H340 I60-I69",
    "dementia": "F00-F03 F051 G30 G311",
    "chronic_pulmonary_disease": "I278 I279 J40-J47 J60-J67 J684 J701 J703",
    "rheumatic_disease": "M05 M06 M315 M32-M34 M351 M353 M360",
    "peptic_ulcer_disease": "K25-K28",
    "mild_liver_disease": "B18 K700-K703 K709 K713-K715 K717 K73 K74 K760 K762-K764 K768 K769 Z944",
    "diabetes_without_complication": "E100 E101 E106 E108 E109 E110 E111 E116 E118 E119 E120 E121 E126 E128 E129 E130 E131 E136 E138 E139 E140 E141 E146 E148 E149",
    "diabetes_with_complication": "E102-E105 E107 E112-E115 E117 E122-E125 E127 E132-E135 E137 E142-E145 E147",
    "hemiplegia_paraplegia": "G041 G114 G801 G802 G81 G82 G830-G834 G839",
    "renal_disease": "I120 I131 N032-N037 N052-N057 N18 N19 N250 Z490-Z492 Z940 Z992",
    "malignancy": "C00-C26 C30-C34 C37-C41 C43 C45-C58 C60-C76 C81-C85 C88 C90-C97",
    "moderate_severe_liver_disease": "I850 I859 I864 I982 K704 K711 K721 K729 K765-K767",
    "metastatic_solid_tumor": "C77-C80",
    "aids_hiv": "B20-B22 B24",
}


def expand(expression):
    result = set()
    for token in expression.split():
        if "-" not in token:
            result.add(token)
        else:
            low, high = token.split("-")
            assert low[0] == high[0] and len(low) == len(high)
            result.update(low[0] + str(n).zfill(len(low)-1)
                          for n in range(int(low[1:]), int(high[1:])+1))
    return result


class QuanTableTests(unittest.TestCase):
    def test_every_printed_prefix_and_no_extra_prefixes(self):
        spec, _ = load_definition()
        self.assertEqual(set(spec["conditions"]), set(TABLE))
        for name, expression in TABLE.items():
            expected = expand(expression)
            self.assertEqual(set(spec["conditions"][name]["icd10_prefixes"]), expected, name)
            for code in expected:
                with self.subTest(condition=name, code=code):
                    result = calculate_charlson([code])
                    self.assertTrue(result["conditions"][name]["matched"])
                    self.assertEqual(result, calculate_charlson([code]))
