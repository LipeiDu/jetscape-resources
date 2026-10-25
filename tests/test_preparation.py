import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("git"), "Git required for source preparation checks")
class SourcePreparationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pinned source check ")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.reference = self.base / "reference"
        self.reference.mkdir()
        def git(*args):
            return subprocess.check_output(["git", "-C", str(self.reference), *args], text=True, stderr=subprocess.DEVNULL).strip()
        git("init")
        (self.reference / "revision.txt").write_text("selected revision\n")
        git("add", "revision.txt")
        git("-c", "user.name=Test Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "selected")
        self.pinned = git("rev-parse", "HEAD")
        (self.reference / "revision.txt").write_text("newer revision\n")
        git("add", "revision.txt")
        git("-c", "user.name=Test Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "newer")
        self.tables = self.base / "tables"
        self.tables.mkdir()
        (self.tables / "table.dat").write_text("reference table\n")
        self.versions = self.base / "versions.json"
        self.versions.write_text(json.dumps({"repositories": [{"path": ".", "url": "unused-in-local-test", "commit": self.pinned}]}))
        self.destination = self.base / "new source"

    def prepare(self, *extra):
        return subprocess.run([sys.executable, str(ROOT / "scripts/prepare_source.py"),
                               "--destination", str(self.destination), "--reference-source", str(self.reference),
                               "--versions", str(self.versions), "--lbt-tables", str(self.tables), *extra],
                              capture_output=True, text=True)

    def test_preview_and_local_clone_pin_without_mutating_reference(self):
        self.assertEqual(self.prepare().returncode, 0)
        self.assertFalse(self.destination.exists())
        result = self.prepare("--execute")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.destination / "revision.txt").read_text(), "selected revision\n")
        self.assertEqual((self.reference / "revision.txt").read_text(), "newer revision\n")
        self.assertEqual((self.destination / "external_packages/LBT-tables/table.dat").read_text(), "reference table\n")
        self.assertNotEqual(self.prepare("--execute").returncode, 0)

    def test_hard_profile_skips_unavailable_soft_component_repositories(self):
        spec = json.loads(self.versions.read_text())
        for component in ["external_packages/iSS", "external_packages/smash/smash_code"]:
            spec["repositories"].append({"path": component, "url": "unavailable", "commit": self.pinned})
        self.versions.write_text(json.dumps(spec))
        result = self.prepare("--profile", "hard-focused", "--execute")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.destination / "external_packages/iSS").exists())
        self.assertFalse((self.destination / "external_packages/smash").exists())

    def test_rejects_manifest_path_escape_before_creating_destination(self):
        spec = json.loads(self.versions.read_text())
        spec["repositories"][0]["path"] = "../escape"
        self.versions.write_text(json.dumps(spec))
        self.assertNotEqual(self.prepare("--execute").returncode, 0)
        self.assertFalse(self.destination.exists())


if __name__ == "__main__":
    unittest.main()
