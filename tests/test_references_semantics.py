import unittest
from open_dpc.references import snapshot_mapping, read_classification_csv
from open_dpc.semantics.drugs import annotate_drugs


class ReferenceTests(unittest.TestCase):
    def test_snapshot_is_detached_and_immutable(self):
        rows = {"000000123": {"drug_category": "synthetic"}}
        snapshot = snapshot_mapping(rows, dataset="synthetic-drugs", version="1")
        rows["000000123"]["drug_category"] = "changed"
        detached = snapshot.as_lookup()
        detached["000000123"]["drug_category"] = "changed"
        self.assertEqual(snapshot.rows["000000123"]["drug_category"], "synthetic")
        with self.assertRaises(TypeError):
            snapshot.rows["000000123"]["drug_category"] = "changed"
        self.assertNotEqual(snapshot.sha256, snapshot_mapping(rows, dataset="synthetic-drugs", version="1").sha256)

    def test_statuses_and_input_preservation(self):
        records = [{"receipt_code": "000000123"}, {"receipt_code": "000000124"}, {"receipt_code": "-"}]
        snapshot = snapshot_mapping({"000000123": {"drug_category": "synthetic"}}, dataset="test", version="1")
        result = annotate_drugs(records, reference=snapshot)
        self.assertEqual([r["resolution"]["status"] for r in result], ["matched", "unmapped", "invalid_code"])
        self.assertEqual(records[0], {"receipt_code": "000000123"})
        self.assertEqual(result, annotate_drugs(records, reference=snapshot))
        self.assertEqual(annotate_drugs(records[:1], reference=None)[0]["resolution"]["status"], "reference_missing")
        empty = snapshot_mapping({}, dataset="explicit-empty", version="1")
        self.assertEqual(annotate_drugs(records[:1], reference=empty)[0]["resolution"]["status"], "unmapped")

    def test_nested_reference_attributes_cannot_escape_immutability(self):
        with self.assertRaisesRegex(ValueError, "attributes_must_be_strings"):
            snapshot_mapping({"123": {"mutable": []}}, dataset="invalid", version="1")

    def test_csv_rejects_duplicate_and_invalid_rows(self):
        for data in (b"receipt_code,receipt_code\n1,1\n", b"receipt_code,label\n1,x\n1,y\n", b"receipt_code,label\n1\n", b"receipt_code,label\n-,x\n"):
            with self.assertRaises(ValueError):
                read_classification_csv(data)
        self.assertEqual(read_classification_csv(b"receipt_code,label\n-,x\n", allow_legacy_placeholder=True)["-"]["label"], "x")
