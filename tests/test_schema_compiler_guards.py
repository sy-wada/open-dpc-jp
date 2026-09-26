"""Guard the failure modes found in the annual source audit."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
module_spec = importlib.util.spec_from_file_location("compile_schemas", ROOT / "tools/compile_schemas.py")
compiler = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(compiler)


class SchemaCompilerGuards(unittest.TestCase):
    def setUp(self):
        self.schema = compiler.load_json(ROOT / "spec/dpc/base/2025.json")
        self.source_ids = {"dpc-2025-20250530"}

    def test_future_code_and_missing_page_fail(self):
        schema = deepcopy(self.schema)
        schema["ff1"]["codes"]["FIM0020"]["version"] = "20260601"
        with self.assertRaisesRegex(ValueError, "future_ff1_code_version"):
            compiler.validate_schema(schema, self.source_ids)
        schema = deepcopy(self.schema)
        del schema["source_coverage"]["ff1_payload_pdf_pages"]["FIM0020"]
        with self.assertRaisesRegex(ValueError, "missing_ff1_source_page"):
            compiler.validate_schema(schema, self.source_ids)

    def test_ef17_reserved_position_and_evidence_fail(self):
        schema = deepcopy(self.schema)
        schema["ef"]["efn_ef17"]["positions"]["6"] = {"name": "wrong", "reserved": True}
        with self.assertRaisesRegex(ValueError, "ambiguous_ef17_position"):
            compiler.validate_schema(schema, self.source_ids)
        schema = deepcopy(self.schema)
        del schema["ef"]["efg_ef17"]["positions"]["12"]
        with self.assertRaisesRegex(ValueError, "incomplete_ef17_positions"):
            compiler.validate_schema(schema, self.source_ids)

    def test_inference_cycle_fails(self):
        a = {"definition_evidence": {"ff1": {"inferred_from": ["b"]}}}
        b = {"definition_evidence": {"ff1": {"inferred_from": ["a"]}}}
        with self.assertRaisesRegex(ValueError, "cyclic_inference_reference"):
            compiler.validate_inference_graph({"a": a, "b": b})


if __name__ == "__main__":
    unittest.main()
