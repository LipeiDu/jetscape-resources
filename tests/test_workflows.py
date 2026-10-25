import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from hadron_io import read_events
from inspect_hadrons import inspect
from run_simulation import validate_config

HEADER = "# JETSCAPE_FINAL_STATE v2 | N pid status E Px Py Pz\n"
EVENT = "# Event 1 weight 2 EPangle 0 N_hadrons 1 centrality 35 pt_hat 25\n0 211 0 2 1 0 0\n"


class HadronReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "hadrons.dat"

    def test_reads_empty_and_nonempty_blocks_with_metadata(self):
        self.path.write_text(HEADER + EVENT + "# Event 2 weight 1 EPangle 0 N_hadrons 0\n# sigmaGen 0.3 sigmaErr 0.01\n")
        result = inspect(self.path, 2, True)
        self.assertEqual(result["writer_blocks"], 2)
        self.assertEqual(result["particle_rows"], 1)
        self.assertEqual(result["sum_event_weights"], 3)
        self.assertEqual(result["mean_particle_pt_GeV_unweighted_all_statuses"], 1)
        self.assertEqual(result["cross_section_footer"]["sigmaGen_mb"], 0.3)

    def test_rejects_truncated_file(self):
        self.path.write_text(HEADER + "# Event 1 weight 1 N_hadrons 2\n0 211 0 2 1 0 0\n")
        with self.assertRaisesRegex(ValueError, "truncated"):
            list(read_events(self.path))

    def test_rejects_nonfinite_particle(self):
        self.path.write_text(HEADER + EVENT.replace("2 1 0 0", "nan 1 0 0"))
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            list(read_events(self.path))

    def test_rejects_wrong_version_and_duplicate_event_ids(self):
        for text in [(HEADER + EVENT).replace("v2", "v3"), HEADER + EVENT + EVENT]:
            self.path.write_text(text)
            with self.assertRaises(ValueError):
                list(read_events(self.path))


class ConfigTests(unittest.TestCase):
    def test_examples_and_hard_log_coordinate_conversion(self):
        for name in ("soft_AuAu200.xml", "hard_AuAu200.xml"):
            self.assertEqual(validate_config(ET.parse(ROOT / "examples" / name).getroot()), 200)
        import math
        data = json.loads((ROOT / "hard/reference_point.json").read_text())
        hard = ET.parse(ROOT / "examples/hard_AuAu200.xml").getroot()
        for tag, key in [("qhatA", "ln_c1"), ("qhatB", "ln_c2"), ("qhatC", "ln_c3")]:
            self.assertAlmostEqual(float(hard.findtext("Eloss/Matter/" + tag)), math.exp(data["point"][key]))
        self.assertIsNone(hard.find("SoftParticlization"))
        self.assertIsNone(hard.find("Afterburner"))

    def test_rejects_energy_and_negative_coefficient_errors(self):
        for path, value in [("Hard/PythiaGun/eCM", "2760"), ("Eloss/Matter/qhatA", "-4.51052")]:
            root = ET.parse(ROOT / "examples/hard_AuAu200.xml").getroot()
            root.find(path).text = value
            with self.assertRaises(ValueError):
                validate_config(root)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="resource check ")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base / "source with spaces"
        self.build = self.source / "build"
        self.build.mkdir(parents=True)
        for name in ("EOS", "LBT-tables", "iSS_tables"):
            (self.build / name).mkdir()
            (self.build / name / "sample_table").write_text("table\n")
        data = self.source / "external_packages/smash/smash_code/input"
        data.mkdir(parents=True)
        for name in ("particles.txt", "decaymodes.txt"):
            (data / name).write_text("fixture\n")
        self.exe = self.build / "runJetscape"
        self.exe.write_text("#!" + sys.executable + "\nfrom pathlib import Path\nPath('event_final_state_hadrons.dat').write_text(" + repr(HEADER + EVENT) + ")\n")
        self.exe.chmod(0o755)
        self.destination = self.base / "new run"

    def run_runner(self, *extra):
        return subprocess.run([sys.executable, str(ROOT / "scripts/run_simulation.py"),
                               "--source", str(self.source), "--config", str(ROOT / "examples/soft_AuAu200.xml"),
                               "--run-dir", str(self.destination), "--events", "1", "--seed", "123", *extra],
                              capture_output=True, text=True)

    def test_preview_no_writes_then_execution_and_overwrite_refusal(self):
        self.assertEqual(self.run_runner().returncode, 0)
        self.assertFalse(self.destination.exists())
        result = self.run_runner("--execute")
        self.assertEqual(result.returncode, 0, result.stderr)
        record = self.destination / "run_record.json"
        saved = record.read_bytes()
        data = json.loads(saved)
        self.assertEqual(data["status"], "passed")
        self.assertEqual(data["output_check"]["particle_rows"], 1)
        self.assertNotEqual(self.run_runner("--execute").returncode, 0)
        self.assertEqual(record.read_bytes(), saved)

    def test_zero_exit_without_valid_output_is_failure(self):
        self.exe.write_text("#!" + sys.executable + "\n")
        result = self.run_runner("--execute")
        self.assertNotEqual(result.returncode, 0)
        data = json.loads((self.destination / "run_record.json").read_text())
        self.assertEqual(data["simulation_exit_code"], 0)
        self.assertEqual(data["status"], "failed")

    def test_hard_run_without_iss_or_smash_installation(self):
        import shutil
        shutil.rmtree(self.build / "iSS_tables")
        shutil.rmtree(self.source / "external_packages/smash")
        self.exe.write_text("#!" + sys.executable + "\nfrom pathlib import Path\nPath('event_final_state_hadrons.dat').write_text(" + repr(HEADER + EVENT + "# sigmaGen 0.3 sigmaErr 0.01\n") + ")\n")
        result = self.run_runner("--config", str(ROOT / "examples/hard_AuAu200.xml"), "--execute")
        self.assertEqual(result.returncode, 0, result.stderr)
        saved = json.loads((self.destination / "run_record.json").read_text())
        self.assertNotIn("iSS_tables", saved["asset_directories"])
        self.assertNotIn("particles.txt", saved["required_files"])

    def test_hard_run_requires_cross_section_footer(self):
        result = self.run_runner("--config", str(ROOT / "examples/hard_AuAu200.xml"), "--execute")
        self.assertNotEqual(result.returncode, 0)
        data = json.loads((self.destination / "run_record.json").read_text())
        self.assertIn("cross-section", data["error"])


if __name__ == "__main__":
    unittest.main()
