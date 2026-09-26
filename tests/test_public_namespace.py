import unittest


class PublicNamespace(unittest.TestCase):
    def test_primary_imports_share_implementation(self):
        import open_dpc_jp
        from open_dpc_jp.parsing import parse_ef, parse_ff1
        from open_dpc_jp.schemas import resolve_schema
        from open_dpc_jp.semantics.comorbidity import calculate_charlson
        from open_dpc.parsing import parse_ef as legacy_parse_ef

        self.assertEqual(open_dpc_jp.__version__, "0.1.0")
        self.assertIs(parse_ef, legacy_parse_ef)
        self.assertTrue(callable(parse_ff1))
        self.assertEqual(resolve_schema(schema_id="dpc-2025-20250530").schema_id, "dpc-2025-20250530")
        self.assertEqual(calculate_charlson(["I21.0", "C78.0", "C34.9"], definition="quan-2005")["score"], 7)


if __name__ == "__main__":
    unittest.main()
