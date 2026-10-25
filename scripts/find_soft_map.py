#!/usr/bin/env python3
"""Estimate the bounded joint MAP using the supplied SIMS likelihood environment.

Run this with the Python environment that can load the archived SIMS emulators.
Only the output JSON is written; source chains and model inputs are read as-is.
"""
from __future__ import print_function

import argparse
from contextlib import redirect_stdout
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

import numpy as np
from scipy.optimize import minimize


def optimize_map(log_posterior, samples, weights, lower, upper, published, maxiter=500, sample_scores=None):
    """Three bounded starts in affine prior coordinates; retain the best result."""
    widths = upper - lower
    bounds = [(1.e-7, 1. - 1.e-7)] * len(lower)
    scores = np.asarray(log_posterior(samples) if sample_scores is None else sample_scores, dtype=float)
    best_sample = samples[int(np.argmax(scores))]
    starts = [('highest_posterior_sample', best_sample),
              ('published_Grad_MAP', published),
              ('posterior_mean', np.average(samples, axis=0, weights=weights))]
    evaluations = [0]

    def objective_and_gradient(unit):
        # Vectorized bounded central differences; retain the covariance response.
        plus = np.tile(unit, (len(unit), 1))
        minus = plus.copy()
        indices = np.arange(len(unit))
        plus[indices, indices] = np.minimum(unit + 1.e-5, 1. - 1.e-7)
        minus[indices, indices] = np.maximum(unit - 1.e-5, 1.e-7)
        batch = np.vstack([unit, plus, minus])
        values = -np.asarray(log_posterior(lower + batch * widths), dtype=float)
        evaluations[0] += len(batch)
        if not np.isfinite(values).all():
            raise ValueError('Nonfinite posterior inside the declared optimization box')
        gradient = (values[1:1+len(unit)] - values[1+len(unit):]) / (
            plus[indices, indices] - minus[indices, indices])
        return float(values[0]), gradient

    results = []
    for label, start in starts:
        unit = np.clip((start - lower) / widths, 1.e-7, 1. - 1.e-7)
        result = minimize(objective_and_gradient, unit, method='L-BFGS-B', jac=True,
                          bounds=bounds, options={'maxiter': maxiter, 'ftol': 1.e-11,
                                                  'gtol': 2.e-4, 'maxls': 40})
        point = lower + result.x * widths
        results.append({'start': label, 'success': bool(result.success),
                        'message': str(result.message), 'iterations': int(result.nit),
                        'log_posterior': float(-result.fun), 'point': point.tolist()})
        print(label, result.success, result.nit, -result.fun, flush=True)
    best = max(results, key=lambda row: row['log_posterior'])
    return {'method': 'bounded_multistart_L-BFGS-B', 'estimate': 'joint_MAP_estimate',
            'point': best['point'], 'log_posterior': best['log_posterior'],
            'converged': best['success'], 'starts': results,
            'finite_difference_step_in_prior_units': 1.e-5,
            'evaluated_points_during_optimization': evaluations[0],
            'best_saved_sample_log_posterior': float(scores.max()),
            'improvement_over_best_saved_sample': float(best['log_posterior'] - scores.max()),
            'interpretation': 'Best bounded local optimum among the declared starts; global optimality is not established.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sims-source', type=Path, required=True)
    parser.add_argument('--posterior', type=Path, required=True)
    parser.add_argument('--published', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--maxiter', type=int, default=500)
    args = parser.parse_args()
    source, posterior, published, output = [p.resolve() for p in
        [args.sims_source, args.posterior, args.published, args.output]]
    output.parent.mkdir(parents=True, exist_ok=True)
    with np.load(str(posterior), allow_pickle=False) as data:
        samples, weights = data['samples'], data['weights']
        lower, upper = data['prior_min'], data['prior_max']
        columns = data['columns'].tolist()
        stored_scores = data['log_likelihood'] + data['log_prior']
    table = json.loads(published.read_text())
    reference = np.asarray([table['values']['Grad'][name] for name in columns])
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(source / 'src'))
    os.chdir(str(source))
    os.environ['JS_BAYES_INCLUDE_MODEL_DISCREPANCY'] = '0'
    os.environ['JS_BAYES_SUBSET_NAME'] = 'full'
    os.environ['JS_BAYES_SUBSET_CONFIG'] = str(source / 'subset_configs/js_soft_sector_subsets.json')
    with tempfile.TemporaryDirectory(prefix='soft-map-runtime-') as temporary:
        os.environ['MPLCONFIGDIR'] = temporary
        os.environ['MPLBACKEND'] = 'Agg'
        with redirect_stdout(sys.stderr):
            from bayes_mcmc import Chain
            chain = Chain(path=Path(temporary) / 'unused_chain.hdf', include_model_discrepancy=False)
        if chain.ndim != 18 or not np.allclose(lower, chain.min) or not np.allclose(upper, chain.max):
            raise ValueError('The source likelihood does not match the supplied posterior parameter box')
        observations = sum(len(block) for block in chain._expt_y.values())

        def log_posterior(points):
            return chain.log_likelihood(points) + chain.log_prior(points)

        selected = np.argsort(stored_scores)[-5:]
        if not np.allclose(log_posterior(samples[selected]), stored_scores[selected], atol=1.e-6, rtol=0):
            raise ValueError('Source likelihood does not reproduce the stored posterior scores')
        result = optimize_map(log_posterior, samples, weights, lower, upper, reference,
                              args.maxiter, sample_scores=stored_scores)
    result['columns'] = columns
    result['point'] = dict(zip(columns, result['point']))
    for row in result['starts']:
        row['point'] = dict(zip(columns, row['point']))
    result['observable_count'] = observations
    result['include_model_discrepancy'] = False
    result['posterior_sha256'] = hashlib.sha256(posterior.read_bytes()).hexdigest()
    result['published_reference'] = table['source_url']
    output.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
