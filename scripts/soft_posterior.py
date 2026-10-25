"""Readers and corner plots for the supplied full-data soft posterior."""
from pathlib import Path
import numpy as np


def load_posterior(path):
    with np.load(Path(path), allow_pickle=False) as archive:
        data = {key: archive[key] for key in archive.files}
    samples, weights = data['samples'], data['weights']
    names = data['columns'].tolist()
    if samples.ndim != 2 or samples.shape[1] != len(names) or len(set(names)) != len(names):
        raise ValueError('Require a sample matrix with one unique name per coordinate')
    if len(samples) < 2 or not np.isfinite(samples).all():
        raise ValueError('Require at least two finite posterior samples')
    if weights.shape != (len(samples),) or not np.isfinite(weights).all() or (weights < 0).any() or weights.sum() <= 0:
        raise ValueError('Require aligned finite, nonnegative importance weights')
    for name in ['log_likelihood', 'log_prior']:
        if data[name].shape != weights.shape or not np.isfinite(data[name]).all():
            raise ValueError('Require aligned finite posterior score components')
    if data['prior_min'].shape != (len(names),) or data['prior_max'].shape != (len(names),):
        raise ValueError('Require complete prior bounds')
    if (data['prior_min'] >= data['prior_max']).any():
        raise ValueError('Prior intervals must have positive width')
    if ((samples < data['prior_min']) | (samples > data['prior_max'])).any():
        raise ValueError('Samples outside declared prior bounds')
    data['weights'] = weights / weights.sum()
    data['columns'] = names
    return data


def weighted_quantile(values, weights, probabilities):
    order = np.argsort(values)
    return np.interp(probabilities, np.cumsum(weights[order]) / weights.sum(), np.asarray(values)[order])


def corner_plot(data, indices, labels, local_map, published_map):
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.ticker import MaxNLocator
    from scipy.ndimage import gaussian_filter

    samples, weights = data['samples'][:, indices], data['weights']
    names = [data['columns'][i] for i in indices]
    lower, upper = data['prior_min'][indices], data['prior_max'][indices]
    count = len(indices)
    scale = 1.35 if count > 10 else 1.8
    figure, axes = plt.subplots(count, count, figsize=(scale*count, scale*count), squeeze=False)
    for i in range(count):
        for j in range(count):
            axis = axes[i, j]
            if j > i:
                axis.set_visible(False)
                continue
            if i == j:
                axis.hist(samples[:, i], bins=40, weights=weights, density=True,
                          histtype='stepfilled', color='#4b80a6', alpha=.6,
                          range=(lower[i], upper[i]))
                axis.set_yticks([])
            else:
                histogram, xe, ye = np.histogram2d(samples[:, j], samples[:, i], bins=40,
                    weights=weights, range=[(lower[j], upper[j]), (lower[i], upper[i])])
                density = gaussian_filter(histogram.T, .8, mode='constant')
                ordered = np.sort(density.ravel())[::-1]
                cumulative = np.cumsum(ordered) / ordered.sum()
                levels = np.unique([ordered[min(np.searchsorted(cumulative, mass), len(ordered)-1)] for mass in [.95, .68]])
                x, y = (xe[1:]+xe[:-1])/2, (ye[1:]+ye[:-1])/2
                axis.contourf(x, y, density, levels=[*levels, density.max()*1.001],
                              colors=['#d8e7f2', '#89b4d2'][-len(levels):])
                axis.contour(x, y, density, levels=levels, colors='#326c96', linewidths=.65)
                axis.set_ylim(lower[i], upper[i])
            axis.axvline(published_map[names[j]], color='#333333', ls='--', lw=.8)
            axis.axvline(local_map[names[j]], color='#bd523c', lw=.9)
            if i != j:
                axis.axhline(published_map[names[i]], color='#333333', ls='--', lw=.8)
                axis.axhline(local_map[names[i]], color='#bd523c', lw=.9)
            axis.set_xlim(lower[j], upper[j])
            axis.xaxis.set_major_locator(MaxNLocator(3))
            if i != j:
                axis.yaxis.set_major_locator(MaxNLocator(3))
            axis.tick_params(labelsize=6 if count > 10 else 8, direction='in', top=True, right=True)
            if i == count-1:
                axis.set_xlabel(labels[j], fontsize=9 if count > 10 else 11)
            else:
                axis.tick_params(labelbottom=False)
            if j == 0 and i != j:
                axis.set_ylabel(labels[i], fontsize=9 if count > 10 else 11)
            elif j:
                axis.tick_params(labelleft=False)
    figure.suptitle('Soft-sector Grad posterior: local RHIC + LHC rerun', fontsize=14, y=.995)
    figure.legend(handles=[Line2D([], [], color='#bd523c', label='Local bounded MAP estimate'),
                           Line2D([], [], color='#333333', ls='--', label='Published Grad MAP (Table II)')],
                  loc='upper right', bbox_to_anchor=(.96, .96), frameon=False, fontsize=11)
    figure.subplots_adjust(left=.06, bottom=.06, right=.99, top=.965, hspace=.08, wspace=.18)
    return figure
