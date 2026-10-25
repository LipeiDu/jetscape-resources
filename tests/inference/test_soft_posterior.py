import sys
import unittest
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from soft_posterior import load_posterior, weighted_quantile
from find_soft_map import optimize_map


class SoftPosteriorTests(unittest.TestCase):
    def test_supplied_posterior_has_declared_18d_box_and_aligned_scores(self):
        data = load_posterior(ROOT/'soft/posterior.npz')
        self.assertEqual(data['samples'].shape, (9127, 18))
        self.assertNotIn('sigma_M', data['columns'])
        self.assertAlmostEqual(data['weights'].sum(), 1)
        self.assertGreater(1/np.sum(data['weights']**2), 8400)

    def test_weighted_quantiles_use_probability_weights(self):
        got = weighted_quantile(np.array([10., 0., 20.]), np.array([.8, .1, .1]), [.5])
        self.assertAlmostEqual(got[0], 5.)
        self.assertNotEqual(got[0], np.median([10., 0., 20.]))

    def test_bounded_map_optimizes_joint_density_between_retained_points(self):
        target = np.array([.7, -.4])
        precision = np.array([[3., 1.], [1., 4.]])
        def posterior(points):
            delta = np.asarray(points) - target
            return -.5*np.einsum('ni,ij,nj->n', delta, precision, delta)
        samples = np.array([[-1., 0.], [0., 1.], [1., -1.]])
        result = optimize_map(posterior, samples, np.ones(3)/3,
                              np.array([-2., -2.]), np.array([2., 2.]), np.zeros(2))
        self.assertTrue(result['converged'])
        np.testing.assert_allclose(result['point'], target, atol=1.e-5)
        self.assertGreater(result['improvement_over_best_saved_sample'], 0)


if __name__ == '__main__':
    unittest.main()
