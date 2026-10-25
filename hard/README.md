# Hard-sector posterior resources

[hard_sector.ipynb](hard_sector.ipynb) plots the supplied six-parameter MCMC samples, summarizes marginal intervals, converts an approximate reference point into JETSCAPE coefficients, and demonstrates bounded joint KDE mode estimation. The related JETSCAPE study is [*Bayesian Inference analysis of jet quenching using inclusive jet and hadron suppression measurements*](https://arxiv.org/abs/2408.08247), Phys. Rev. C 111, 054913 (2025).

## Run and inputs

Use the [inference environment](../README.md#explore-the-inference-resources), then open the notebook. No download is required for this example.

| File | Purpose |
| --- | --- |
| [hard_sector.ipynb](hard_sector.ipynb) | Posterior plots, reference-point conversion and bounded joint KDE estimate |
| [MCMCSamples.txt.bz2](MCMCSamples.txt.bz2) | 250,000 rows × 6 coordinates; 6.94 MiB compressed |
| [metadata.json](metadata.json) | Column order, units and compressed/uncompressed checksums |
| [reference_point.json](reference_point.json) | Supplied approximate joint KDE reference and its density coordinates |

The MCMC samples were provided by lead authors of the study cited above; please cite that paper when using them. The archive decompresses to a whitespace-delimited text array without a header. This walkthrough uses the supplied samples; it does not rerun the published inference. The flattened file does not retain walker boundaries or all original calibration/preprocessing settings. All rows, including repeats, are retained, with no additional burn-in removal, thinning or prior cuts. See the metadata for the available dataset information.

| Column | Coordinate | Unit |
| --- | --- | --- |
| 0 | $\alpha_s$ (`AlphaS`) | dimensionless |
| 1 | $Q_0$ (`Q0`) | GeV |
| 2 | $\ln c_1$ (`ln_c1`) | dimensionless |
| 3 | $\ln c_2$ (`ln_c2`) | dimensionless |
| 4 | $\tau_0$ (`Tau0`) | fm/$c$ |
| 5 | $\ln c_3$ (`ln_c3`) | dimensionless |

A plotting subset is used for speed; summaries use the complete array. A flattened sample file alone does not establish chain convergence or effective sample size. Sample minima and maxima should not be interpreted as prior limits.

## Reference point and MAP conventions

The supplied reference is approximately $(0.4112,1.65262,-4.51052,-1.31168,0.325466,3.67332)$ in the listed coordinates. It was estimated from posterior samples with a joint KDE; it is not a MAP vector quoted from a published table. This distinction concerns how the reference point was estimated. The exact likelihood and matching emulator needed for continuous posterior optimization are not bundled here. The notebook's bounded estimate uses 4,000 fit rows and 1,500 candidate rows with a declared seed; bandwidth, boundary bias and candidate coverage affect the result.

For the supplied point, $c_i=\exp(\ln c_i)$ gives `qhatA = 0.010992742463249567`, `qhatB = 0.26936713924688244` and `qhatC = 39.3824387524629`. The [hard simulation XML](../examples/hard_AuAu200.xml) uses those positive physical coefficients. `hard_point_to_xml` requires explicit log-coordinate names. Apply the conversion once when preparing simulation coefficients.

Marginal medians, marginal modes, a joint KDE mode and a highest-posterior retained sample are distinct summaries. A density mode also depends on coordinates: changing from $\ln c_i$ to $c_i$ introduces the factor $1/(c_1c_2c_3)$. Converting one point does not optimize the density in the new coordinates. The shared [posterior helpers](../scripts/inference_tools.py) retain each method and coordinate declaration; selecting a highest-posterior sample requires aligned scores.

The hard reference values are illustrative settings, not a universal tune. Review collision energy, medium, sampling and normalization before using them in a physics calculation. Data attribution and terms are described in [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
