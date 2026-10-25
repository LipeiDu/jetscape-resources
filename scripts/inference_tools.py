"""Small equal-weight posterior utilities with explicit coordinate conventions."""
from pathlib import Path
import hashlib
import numpy as np


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def validate_samples(samples, names):
    values = np.asarray(samples, dtype=float)
    if values.ndim != 2 or values.shape[0] < 2 or values.shape[1] != len(names):
        raise ValueError('Expected at least two samples with one column per named coordinate')
    if len(set(names)) != len(names) or not np.isfinite(values).all():
        raise ValueError('Names must be unique and all sample values finite')
    return values


def load_samples(path, names):
    """Load a flat, equal-weight array; no inferred burn-in, thinning or deduplication."""
    path = Path(path)
    values = np.load(path, allow_pickle=False) if path.suffix == '.npy' else np.loadtxt(path, ndmin=2)
    return validate_samples(values, names)


def load_hdf_chain(path, names, *, dataset='chain', step_axis, burn_steps=0, thin=1):
    """Caller declares step axis; final axis must contain parameters. Flatten after selection."""
    import h5py
    if thin < 1 or burn_steps < 0:
        raise ValueError('Require thin>=1 and burn_steps>=0')
    with h5py.File(path, 'r') as handle:
        source = handle[dataset]
        if source.ndim not in (2, 3) or source.shape[-1] != len(names):
            raise ValueError('Expected (steps,parameters) or a three-axis chain')
        if step_axis not in range(source.ndim - 1) or burn_steps >= source.shape[step_axis]:
            raise ValueError('Invalid step axis or burn-in removes entire chain')
        selection = [slice(None)] * source.ndim
        selection[step_axis] = slice(burn_steps, None, thin)
        values = np.asarray(source[tuple(selection)])
    return validate_samples(values.reshape(-1, len(names)), names)


def summarize(samples, names, mass=0.68):
    values = validate_samples(samples, names)
    if not 0 < mass < 1:
        raise ValueError('mass must be between zero and one')
    q = np.quantile(values, [(1-mass)/2, .5, (1+mass)/2], axis=0)
    return {name: {'median': float(q[1, i]), 'equal_tail_low': float(q[0, i]),
                   'equal_tail_high': float(q[2, i])} for i, name in enumerate(names)}


def shortest_interval(values, mass=.68):
    """Shortest contiguous interval containing ceil(mass*n) samples; not a disjoint HPD set."""
    values = np.sort(np.asarray(values, dtype=float))
    if values.ndim != 1 or not values.size or not np.isfinite(values).all() or not 0 < mass <= 1:
        raise ValueError('Require finite one-dimensional data and 0<mass<=1')
    count = max(1, int(np.ceil(mass * len(values))))
    widths = values[count-1:] - values[:len(values)-count+1]
    start = int(np.argmin(widths))
    return float(values[start]), float(values[start+count-1])


def highest_posterior_sample(samples, log_posterior, names):
    """Best retained sample under supplied scores; not continuous optimization."""
    values = validate_samples(samples, names)
    scores = np.asarray(log_posterior, dtype=float)
    if scores.shape != (len(values),) or np.isnan(scores).any() or np.isposinf(scores).any() or not np.isfinite(scores).any():
        raise ValueError('Require aligned posterior scores, with at least one finite value')
    index = int(np.argmax(scores))
    return {'method': 'highest_posterior_retained_sample', 'sample_index': index,
            'log_posterior': float(scores[index]), 'point': dict(zip(names, values[index].tolist()))}


def approximate_joint_mode(samples, names, *, fit_size=4000, candidates=1500, seed=123, bandwidth='scott'):
    """KDE maximum over candidate samples in the explicitly named input coordinates.

    The affine standardization has constant Jacobian and preserves the input-coordinate
    maximizer. Nonlinear transformations require a different density/Jacobian.
    Cost is capped by fit_size*candidates; this is not the original posterior MAP.
    """
    from scipy.stats import gaussian_kde
    values = validate_samples(samples, names)
    if fit_size <= len(names) or candidates < 1:
        raise ValueError('Need more fit samples than dimensions and at least one candidate')
    rng = np.random.default_rng(seed)
    fi = rng.choice(len(values), min(fit_size, len(values)), replace=False)
    ci = rng.choice(len(values), min(candidates, len(values)), replace=False)
    fit = values[fi]
    center, scale = fit.mean(axis=0), fit.std(axis=0, ddof=1)
    if (scale <= 0).any():
        raise ValueError('KDE cannot fit a fixed coordinate')
    kde = gaussian_kde(((fit-center)/scale).T, bw_method=bandwidth)
    scores = kde.logpdf(((values[ci]-center)/scale).T) - np.log(scale).sum()
    index = int(ci[np.argmax(scores)])
    return {'method': 'candidate_sample_joint_KDE_mode', 'density_coordinates': list(names),
            'fit_samples': len(fi), 'candidate_samples': len(ci), 'seed': seed,
            'bandwidth': bandwidth, 'sample_index': index, 'log_kde_density': float(scores.max()),
            'point': dict(zip(names, values[index].tolist())),
            'interpretation': 'Approximation in the input coordinates; not continuous MAP or convergence evidence'}


def hard_point_to_xml(point, *, input_coordinates):
    """Convert one log-coordinate point once; does not optimize a physical-coordinate density."""
    expected = ['AlphaS', 'Q0', 'ln_c1', 'ln_c2', 'Tau0', 'ln_c3']
    if list(input_coordinates) != expected or set(point) != set(expected):
        raise ValueError('Explicit six log-coordinate names are required; physical inputs are not accepted')
    x = np.asarray([point[k] for k in expected], dtype=float)
    if not np.isfinite(x).all():
        raise ValueError('Nonfinite reference point')
    with np.errstate(over='raise', under='raise'):
        a, b, c = np.exp(x[[2, 3, 5]])
    return {'alphas': float(x[0]), 'Q0': float(x[1]), 'tStart': float(x[4]),
            'qhatA': float(a), 'qhatB': float(b), 'qhatC': float(c)}


def corner_plot(samples, names, *, labels=None, reference=None, max_points=20000, seed=123, title='Posterior samples'):
    import matplotlib.pyplot as plt
    values = validate_samples(samples, names)
    if max_points < 2:
        raise ValueError('max_points must be at least two')
    if len(values) > max_points:
        values = values[np.random.default_rng(seed).choice(len(values), max_points, replace=False)]
    labels = list(names) if labels is None else list(labels)
    if len(labels) != len(names):
        raise ValueError('One plot label per coordinate is required')
    d = len(names)
    fig, axes = plt.subplots(d, d, figsize=(2.15*d, 2.15*d), squeeze=False)
    for i in range(d):
        for j in range(d):
            ax = axes[i, j]
            if j > i:
                ax.set_visible(False)
                continue
            if i == j:
                ax.hist(values[:, i], bins=45, density=True, color='#327b91', alpha=.8)
            else:
                ax.hexbin(values[:, j], values[:, i], gridsize=35, mincnt=1, cmap='Blues')
            if reference is not None:
                ax.axvline(reference[names[j]], color='#c24b32', lw=1)
                if i != j:
                    ax.axhline(reference[names[i]], color='#c24b32', lw=1)
            if i == d-1: ax.set_xlabel(labels[j])
            else: ax.tick_params(labelbottom=False)
            if j == 0 and i != j: ax.set_ylabel(labels[i])
            elif j: ax.tick_params(labelleft=False)
    fig.suptitle(title)
    fig.tight_layout(rect=(0, 0, 1, .97))
    return fig
