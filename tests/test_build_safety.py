import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class BuildSafetyTests(unittest.TestCase):
    def test_existing_distribution_is_never_overwritten(self):
        builder = Path(__file__).resolve().parents[1] / "build_release.py"
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder) / "user-data.txt"
            marker.write_text("synthetic sentinel", encoding="utf-8")
            result = subprocess.run([sys.executable, str(builder), "--output", folder],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(marker.read_text(encoding="utf-8"), "synthetic sentinel")
            self.assertEqual(sorted(p.name for p in Path(folder).iterdir()), [marker.name])
