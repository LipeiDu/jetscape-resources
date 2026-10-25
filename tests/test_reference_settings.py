import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

class ReferenceSettingsTests(unittest.TestCase):
    def test_both_xmls_match_published_grad_with_coordinate_conversions(self):
        audit=json.loads((ROOT/'examples/parameter_audit.json').read_text())
        paper=json.loads((ROOT/'soft/published_map.json').read_text())['values']['Grad']
        for name in ['soft_AuAu200.xml','hard_AuAu200.xml']:
            root=ET.parse(ROOT/'examples'/name).getroot()
            for row in audit['soft_parameter_mappings']:
                key=row['parameter']
                expected=1/paper[key]**2 if key=='sigma_k' else paper[key]**(1/3) if key=='dmin3' else paper[key]
                if 'auxiliary_input' in row:
                    value=float(next(line.split()[1] for line in (ROOT/'examples/music_input').read_text().splitlines() if line.startswith('shear_relax_time_factor ')))
                else:
                    node=root.find(row['xml_path'])
                    value=float(node.get(row['attribute']) if 'attribute' in row else node.text)
                self.assertAlmostEqual(value,expected,places=12,msg=name+': '+key)
        hard=ET.parse(ROOT/'examples/hard_AuAu200.xml').getroot()
        ref=json.loads((ROOT/'hard/reference_point.json').read_text())['point']
        for module in ['Matter','Lbt']:
            self.assertAlmostEqual(float(hard.findtext('Eloss/'+module+'/alphas')),ref['AlphaS'])
            self.assertAlmostEqual(float(hard.findtext('Eloss/'+module+'/Q0')),ref['Q0'])
        self.assertAlmostEqual(float(hard.findtext('Eloss/tStart')),ref['Tau0'])
        self.assertIsNone(hard.find('SoftParticlization'))
        self.assertIsNone(hard.find('Afterburner'))

    def test_all_collision_energy_examples_and_sampling_controls(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        from run_simulation import validate_config
        for sector in ["soft", "hard"]:
            for system, energy, norm in [("AuAu200", 200, 5.73), ("PbPb2760", 2760, 14.2), ("PbPb5020", 5020, 18.8)]:
                root = ET.parse(ROOT / "examples" / (sector + "_" + system + ".xml")).getroot()
                self.assertEqual(validate_config(root), energy)
                self.assertAlmostEqual(float(root.find("IS/Trento/PhysicsInputs").get("normalization")), norm)
                if sector == "soft":
                    self.assertEqual(root.findtext("SoftParticlization/iSS/number_of_repeated_sampling"), "3")
                    self.assertEqual(root.findtext("setReuseHydro"), "false")
                else:
                    self.assertEqual(root.findtext("setReuseHydro"), "true")
                    self.assertEqual(root.findtext("nReuseHydro"), "3")
                    self.assertIsNone(root.find("SoftParticlization"))
                    self.assertIsNone(root.find("Afterburner"))

    def test_hard_install_preview_has_no_smash_build_or_soft_source_requirements(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);pythia=base/'pythia8-config';pythia.touch()
            result=subprocess.run([sys.executable,str(ROOT/'scripts/install_jetscape.py'),'--prefix',str(base/'new'),'--lbt-tables',str(base/'tables'),'--pythia-config',str(pythia),'--profile','hard-focused'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            data=json.loads(result.stdout)
            self.assertEqual(len(data['commands']),2)
            self.assertIn('hard-focused',data['commands'][0])
            self.assertNotIn('smash_shared',result.stdout)
            self.assertFalse((base/'new').exists())
            source=base/'source';source.mkdir();(source/'CMakeLists.txt').touch()
            result=subprocess.run([sys.executable,str(ROOT/'scripts/build_jetscape.py'),'--source',str(source),'--build-dir',str(base/'build'),'--profile','hard-focused','--dry-run'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('-DUSE_ISS=OFF',result.stdout)
            self.assertIn('-DUSE_SMASH=OFF',result.stdout)
            self.assertNotIn('SMASH_DIR=',result.stdout)
