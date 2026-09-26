"""Source-byte identity is not inferred from a name, mtime or parsed mapping."""
import csv
import hashlib
import io
import os
from pathlib import Path
import tempfile
import unittest

from open_dpc.references.disease import load_disease_master_with_snapshot


def synthetic_master(name):
    row = [""] * 46
    row[0], row[1], row[2], row[5], row[15] = "0", "B", "0000001", name, "I21.0"
    buffer = io.StringIO(newline="")
    csv.writer(buffer).writerow(row)
    return buffer.getvalue().encode("cp932")


class DiseaseSnapshotTests(unittest.TestCase):
    def test_same_size_same_mtime_replacement_changes_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "b_20250101.txt"
            original = synthetic_master("合成甲")
            changed = synthetic_master("合成乙")
            self.assertEqual(len(original), len(changed))
            path.write_bytes(original)
            stat = path.stat()
            master, snapshot = load_disease_master_with_snapshot(root)
            self.assertEqual(snapshot.sha256, hashlib.sha256(original).hexdigest())
            self.assertEqual(master.resolve("0000001").master_disease_name, "合成甲")
            master.entries.clear()
            fresh, _ = load_disease_master_with_snapshot(root)
            self.assertEqual(len(fresh.entries), 1)
            path.write_bytes(changed)
            os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            newer, updated = load_disease_master_with_snapshot(root)
            self.assertNotEqual(snapshot.sha256, updated.sha256)
            self.assertEqual(updated.sha256, hashlib.sha256(changed).hexdigest())
            self.assertEqual(newer.resolve("0000001").master_disease_name, "合成乙")

    def test_missing_reference_has_no_claimed_byte_snapshot(self):
        master, snapshot = load_disease_master_with_snapshot(None)
        self.assertEqual(master.status, "missing")
        self.assertIsNone(snapshot)
