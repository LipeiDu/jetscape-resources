# Event-generation examples

Six XMLs demonstrate Au–Au at 200 GeV and Pb–Pb at 2.76 and 5.02 TeV in 30–40% centrality. They share the transport coefficients listed below, with system-dependent medium normalizations, and use the source revisions in [software_versions.json](software_versions.json). Start with the [installation guide](../installation.md) and [simulation guide](../simulations.md).

| File | Purpose |
| --- | --- |
| [soft_AuAu200.xml](soft_AuAu200.xml) | TRENTo → free streaming → MUSIC → iSS → SMASH |
| [hard_AuAu200.xml](hard_AuAu200.xml) | TRENTo → free streaming → MUSIC, with Pythia → MATTER/LBT → colorless hadronization |
| [jetscape_main.xml](jetscape_main.xml) | Framework defaults, overridden by the selected user XML |
| [music_input](music_input), [freestream_input](freestream_input), [iSS_parameters.dat](iSS_parameters.dat), [smash_config.yaml](smash_config.yaml) | Auxiliary module inputs staged by the run helper |
| [run_slurm.sbatch](run_slurm.sbatch) | Scheduler template; edit allocation, environment and paths for your site |
| [soft_hadrons.dat](soft_hadrons.dat), [hard_hadrons.dat](hard_hadrons.dat) | Particle-list examples with soft oversampling and hard hydro reuse |
| [sample_metadata.json](sample_metadata.json) | Sample hashes, seeds, particle counts and writer cross sections |

## Collision systems

| System | Soft XML | Hard XML | Medium normalization | Hard pTHat interval |
| --- | --- | --- | ---: | --- |
| Au–Au, 200 GeV | [soft_AuAu200.xml](soft_AuAu200.xml) | [hard_AuAu200.xml](hard_AuAu200.xml) | 5.73 | 20–30 GeV |
| Pb–Pb, 2.76 TeV | [soft_PbPb2760.xml](soft_PbPb2760.xml) | [hard_PbPb2760.xml](hard_PbPb2760.xml) | 14.2 | 50–70 GeV |
| Pb–Pb, 5.02 TeV | [soft_PbPb5020.xml](soft_PbPb5020.xml) | [hard_PbPb5020.xml](hard_PbPb5020.xml) | 18.8 | 100–120 GeV |

The Au–Au and 2.76 TeV normalizations are the published Grad MAP values. The 5.02 TeV normalization follows the [radial-flow companion configuration](https://github.com/LipeiDu/radial-flow-resources/blob/main/configs/PbPb_5020_30_40.xml); that collision energy was not part of the 2021 calibration. The remaining shared soft coefficients use the published Grad reference. The pTHat bins are illustrative run choices, not the complete sampling needed for an inclusive spectrum. The four Pb–Pb XMLs are configuration-checked, without new event-generation validation here.

## Shared medium and soft-only events

The Au–Au example medium uses normalization 5.73, NN cross section 4.2 fm², reduced thickness 0.063, TRENTo gamma shape `k = 1/1.05² = 0.9070294784580498`, nucleon width 1.12 fm, minimum distance `dmin = 2.97^(1/3)` fm, density-dependent free streaming with reference time 1.46 fm/c and exponent 0.031, and switching temperature 0.136 GeV. The XMLs specify the full temperature-dependent transport functions. Related simulation settings are documented with the [radial-flow study](https://arxiv.org/abs/2508.07184) and its [companion resources](https://github.com/LipeiDu/radial-flow-resources).

The numerical baseline is the published Grad MAP in Table II, not the later local MAP estimated in the soft notebook. The [machine-readable audit](parameter_audit.json) maps every applicable soft coordinate and all six hard coordinates to their inputs. `shear_relax_time_factor = 4.65` is set in `music_input`, because this wrapper does not read a corresponding user-XML field.

The soft examples request three hypersurface samples per framework event. SMASH evolves these separately, then the final-state writer saves their particles together under the same event ID. This increases sampling statistics without adding independent hydro backgrounds. The three sample boundaries are not recoverable from the flat ASCII block; see [counting and weights](../hadron-format.md#counting-and-weights).

These settings define the supplied example. They do not identify an exact replay of the [soft Bayesian calibration](https://arxiv.org/abs/2011.01430), whose iS3D sampling chain differs from this iSS/SMASH configuration. When adapting a reference parameter vector, check the fluctuation-coordinate convention and convert a stored $d_{\min}^3$ to a length before setting the minimum distance. The [soft guide](../soft/README.md) describes the original parameter coordinates.

## Hard-focused events

The hard examples omit soft particlization and the afterburner. Either a full installation or the optional `hard-focused` build works. XML module selection disables iSS and SMASH even when they are installed. It also uses no UrQMD. Colorless jet hadronization remains active. The Au–Au example sets the collision and Pythia energy to 200 GeV, the hadronization energy setting to 100 GeV, and the Pythia $\hat p_T$ interval to 20–30 GeV, with bias selection disabled. The medium is the same as in the matching soft example. The hard XMLs reuse one hydro background for three framework events, each with its own writer event ID. This narrow hard-scattering example demonstrates generation and particle I/O; an inclusive $R_{AA}$ calculation requires the appropriate scattering-bin coverage, weights, event ensemble and observable analysis.

The hard vector is the approximate joint KDE reference point in [reference_point.json](../hard/reference_point.json), associated with the [six-parameter posterior example](../hard/README.md). It is estimated in log-coefficient coordinates from retained samples; it is not an official released MAP or a continuously optimized posterior maximum.

| Coordinate | Reference value | XML setting |
| --- | ---: | --- |
| $\alpha_s$ | 0.4112 | MATTER and LBT `alphas` |
| $Q_0$ | 1.65262 GeV | MATTER and LBT `Q0` |
| $\ln c_1$ | −4.51052 | `qhatA = exp(ln_c1)` |
| $\ln c_2$ | −1.31168 | `qhatB = exp(ln_c2)` |
| $\tau_0$ | 0.325466 fm/c | `Eloss/tStart` |
| $\ln c_3$ | 3.67332 | `qhatC = exp(ln_c3)` |

For `QhatParametrizationType=6`, the XML contains the positive coefficients: `qhatA = 0.010992742463249567`, `qhatB = 0.26936713924688244`, and `qhatC = 39.3824387524629`. The selected MATTER implementation reads these XML entries directly. Exponentiate the sample's log coordinates once when preparing the XML. The [hard notebook](../hard/hard_sector.ipynb) demonstrates the conversion and explains how a density mode depends on the parameter coordinates.

## Inspect the sample files

From the repository root:

```bash
python3 scripts/inspect_hadrons.py examples/soft_hadrons.dat --expected-events 1 --require-particles
python3 scripts/inspect_hadrons.py examples/hard_hadrons.dat --expected-events 3 --require-particles
```

The soft sample contains status-27 hadrons after SMASH. Hard samples contain status-0 hadrons and status-−1 hole contributions. The current counts and event grouping are in [sample_metadata.json](sample_metadata.json). Status selection and the hard-event cross-section footer matter for analysis; the [hadron-format guide](../hadron-format.md) explains them. These files illustrate the output format and grouping conventions; they are not samples for a statistical physics comparison.

See the [main reference list](../README.md#references-and-software) for the framework and related studies, and [third-party notices](../THIRD_PARTY_NOTICES.md) for attribution and terms.
