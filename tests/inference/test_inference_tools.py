import sys
import unittest
import tempfile
import json
import bz2
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from inference_tools import (load_samples, load_hdf_chain, summarize, shortest_interval,
                             highest_posterior_sample, approximate_joint_mode, hard_point_to_xml, sha256)
from soft_inputs import read_model, observable_dtype

class InferenceToolsTests(unittest.TestCase):
    def test_hard_archive_identity_and_declared_coordinates(self):
        p = ROOT/'hard'
        metadata = json.loads((p/'metadata.json').read_text())
        archive = p/'MCMCSamples.txt.bz2'
        self.assertEqual(sha256(archive), metadata['archive_sha256'])
        import hashlib
        self.assertEqual(hashlib.sha256(bz2.decompress(archive.read_bytes())).hexdigest(), metadata['uncompressed_sha256'])
        samples = load_samples(archive, metadata['columns'])
        self.assertEqual(list(samples.shape), metadata['shape'])
        self.assertEqual((samples[:, 2] < -5).sum(), 10363)
        self.assertEqual((samples[:, 3] < -5).sum(), 8793)

    def test_coordinate_conversion_and_double_conversion_rejection(self):
        p = ROOT/'hard'
        ref = json.loads((p/'reference_point.json').read_text())
        xml = hard_point_to_xml(ref['point'], input_coordinates=ref['density_coordinates'])
        np.testing.assert_allclose([xml[k] for k in ['qhatA','qhatB','qhatC']], [.010992742463249567,.26936713924688244,39.3824387524629])
        with self.assertRaises(ValueError):
            hard_point_to_xml(xml, input_coordinates=list(xml))
        underflow = dict(ref['point'], ln_c1=-1000.)
        with self.assertRaises(FloatingPointError):
            hard_point_to_xml(underflow, input_coordinates=ref['density_coordinates'])

    def test_highest_posterior_is_a_joint_sample_not_marginal_medians(self):
        x = np.array([[0,10],[1,11],[10,0],[11,1]], dtype=float)
        result = highest_posterior_sample(x, [-3,-1,-2,-4], ['a','b'])
        self.assertEqual(result['point'], {'a':1.,'b':11.})
        self.assertNotEqual(result['point'], {k:v['median'] for k,v in summarize(x,['a','b']).items()})
        with self.assertRaises(ValueError): highest_posterior_sample(x,[0],['a','b'])

    def test_hdf_burn_and_thin_use_declared_step_axis(self):
        import h5py
        x = np.arange(2*7*3).reshape(2,7,3)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'chain.hdf'
            with h5py.File(path,'w') as f:f['chain']=x
            got=load_hdf_chain(path,['a','b','c'],step_axis=1,burn_steps=2,thin=2)
            np.testing.assert_array_equal(got,x[:,2::2,:].reshape(-1,3))
            with self.assertRaises(ValueError):load_hdf_chain(path,['a','b','c'],step_axis=2)

    def test_kde_candidate_is_invariant_under_affine_unit_change(self):
        x=np.random.default_rng(44).multivariate_normal([1,-3],[[1,.7],[.7,2]],600)
        a=approximate_joint_mode(x,['a','b'],fit_size=400,candidates=300,seed=7)
        b=approximate_joint_mode(x*[1e5,.03]+[20,100],['a','b'],fit_size=400,candidates=300,seed=7)
        self.assertEqual(a['sample_index'],b['sample_index'])
        self.assertEqual(a['fit_samples'],400)
        with self.assertRaises(ValueError):approximate_joint_mode(np.ones((20,2)),['a','b'])

    def test_shortest_interval_count_and_full_mass(self):
        self.assertEqual(shortest_interval([0,1,2,100],.75),(0.,2.))
        self.assertEqual(shortest_interval([0,1,2,100],1),(0.,100.))

    def test_model_reader_rejects_partial_records_and_nonzero_padding(self):
        schema=json.loads((ROOT/'soft/observable_schema.json').read_text())
        dtype=observable_dtype(schema,['Pb-Pb-2760','Au-Au-200'])
        x=np.zeros(1,dtype=dtype)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'map.dat';path.write_bytes(x.tobytes())
            self.assertEqual(read_model(path,schema,'Pb-Pb-2760',map_record=True).shape,(1,4))
            path.write_bytes(x.tobytes()+b'!')
            with self.assertRaises(ValueError):read_model(path,schema,'Pb-Pb-2760',map_record=True)
            x['Au-Au-200']['dN_dy_pion']['mean'][0,0,0]=1;path.write_bytes(x.tobytes())
            with self.assertRaises(ValueError):read_model(path,schema,'Pb-Pb-2760',map_record=True)

if __name__ == '__main__':unittest.main()
