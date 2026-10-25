"""Exercise command execution and preservation guarantees using real CMake."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(shutil.which("cmake"), "CMake required for integration checks")
class BuildHelperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="jetscape build check ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source with spaces"
        self.source.mkdir()
        (self.source / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.16)\nproject(HelperSmoke NONE)\n"
        )
        self.build = self.root / "new build"
        self.helper = Path(__file__).resolve().parents[1] / "scripts/build_jetscape.py"

    def run_helper(self, *extra):
        return subprocess.run(
            [sys.executable, str(self.helper), "--source", str(self.source),
             "--build-dir", str(self.build), *extra],
            capture_output=True, text=True,
        )

    def test_dry_run_preserves_source_and_creates_nothing(self):
        before = (self.source / "CMakeLists.txt").read_bytes()
        result = self.run_helper("--profile", "legacy-soft", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.build.exists())
        self.assertEqual((self.source / "CMakeLists.txt").read_bytes(), before)
        self.assertIn("-DUSE_SMASH=ON", result.stdout)
        self.assertIn("SMASH_DIR=", result.stdout)

    def test_real_configure_build_and_refusal_to_overwrite(self):
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        record = self.build / "build_record.json"
        saved = record.read_bytes()
        self.assertEqual(json.loads(saved)["status"], "completed")
        self.assertIsNone(json.loads(saved)["source_git"]["commit"])
        self.assertNotEqual(self.run_helper().returncode, 0)
        self.assertEqual(record.read_bytes(), saved)

    def test_configure_failure_is_reported(self):
        with (self.source / "CMakeLists.txt").open("a") as handle:
            handle.write('message(FATAL_ERROR "deliberate configuration failure")\n')
        result = self.run_helper()
        self.assertNotEqual(result.returncode, 0)
        record = json.loads((self.build / "build_record.json").read_text())
        self.assertEqual(record["status"], "failed")
        self.assertNotEqual(record["exit_code"], 0)
        self.assertIn("-S", record["failed_command"])

    def test_rejects_source_as_build_directory(self):
        result = self.run_helper("--build-dir", str(self.source), "--dry-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.source.iterdir()), [self.source / "CMakeLists.txt"])

    def test_rejects_invalid_arguments_without_creating_build(self):
        for extra in [("--jobs", "0"), ("--cmake-arg=--build",)]:
            with self.subTest(extra=extra):
                self.assertNotEqual(self.run_helper(*extra).returncode, 0)
                self.assertFalse(self.build.exists())


if __name__ == "__main__":
    unittest.main()
