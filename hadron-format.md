# Final-state hadron ASCII format

The reader in this repository supports the seven-column `JETSCAPE_FINAL_STATE v2` format used by the tested examples. It deliberately rejects another declared format version. Binary output, full shower-history ASCII, HepMC, ROOT and converted Parquet require their own readers.

The [JETSCAPE 3.7.1 writer source](https://github.com/JETSCAPE/JETSCAPE/blob/3546d357141f54056af87f6f535467ed26a1289a/src/framework/JetScapeWriterFinalStateStream.cc) defines the original records. The example's main/user XMLs select header v2, ASCII output and the requested particle-status filter.

```text
# JETSCAPE_FINAL_STATE v2 | N pid status E Px Py Pz
# Event 1 weight 1 EPangle 0 N_hadrons 2 centrality 35 pt_hat 25
0 211 27 1.2 0.3 0.4 1.0
1 -211 27 1.4 -0.2 0.1 -1.3
# sigmaGen 0.01 sigmaErr 0.001
```

This is an illustrative schema example, not a generated physical event. Actual files use tabs/spaces and may omit optional named metadata. The file-level header gives the format and columns. Each event header starts a new writer block and declares the number of following particle rows, including zero. The final footer may carry Pythia cross-section information.

| Field | Meaning |
| --- | --- |
| `N` | Zero-based row index within this block, after writer filtering |
| `pid` | PDG particle identifier |
| `status` | JETSCAPE particle/source status; its interpretation depends on the producing module |
| `E` | Energy in GeV |
| `Px`, `Py`, `Pz` | Cartesian momentum components in GeV |

Event metadata include the one-based event number, event weight, event-plane angle and `N_hadrons`; centrality and `pt_hat` appear when enabled. Parse metadata by name rather than fixed token positions. Negative/sentinel metadata should not be interpreted as measured values. In particular, `pt_hat` has no hard-scatter meaning in a soft-only run.

The native writer records momenta, not positions, pseudorapidity or rapidity. Compute transverse momentum as `sqrt(Px**2 + Py**2)` and compute rapidity or pseudorapidity with the appropriate formula and acceptance convention. They are different quantities, particularly for massive particles at low momentum.

## Particle status and holes

These are JETSCAPE statuses (`pstat`), not Pythia’s internal status numbering and not the sign of the PDG ID. Their meaning depends on the producer. For the supplied workflows:

| Status | Meaning |
| --- | --- |
| `11` | Hadrons sampled by the iSS wrapper, before an afterburner. |
| `27` | Hadrons returned by SMASH. |
| `0` | Positive-sector hadrons from colorless jet hadronization. With recoil enabled, this sector includes hadronized shower and recoil contributions. |
| `-1` | Negative-sector hadrons obtained by hadronizing the thermal-hole contribution; they represent subtraction of the medium particles associated with recoil production. |

At the parton level, this colorless-hadronization path accepts status `0` shower partons and status `1` recoil partons into the positive sector; status `-1` partons enter the negative sector. The resulting positive and negative **hadron** statuses are `0` and `-1`, respectively. See the [pinned colorless-hadronization source](https://github.com/JETSCAPE/JETSCAPE/blob/3546d357141f54056af87f6f535467ed26a1289a/src/hadronization/ColorlessHadronization.cc).

A hole represents a subtraction contribution; its stored four-momentum is read normally, without an extra sign change. The particle status identifies this contribution separately from the generator event weight. Its treatment in a spectrum or jet observable belongs to the chosen analysis. Negative-PDG antiparticles remain ordinary particles and are not identified as holes by their PDG sign.

`statusToSkip` controls which statuses reach the file. The examples preserve both `0` and `-1`. The inspection script reports all observed codes without imposing a physics selection. The simple `plot_hadrons.py --status ...` command selects one status for a diagnostic plot; it does not implement the combined signed hard spectrum or a jet analysis.

## Counting and weights

A writer block is a framework iteration. The [bundled samples](examples/sample_metadata.json) illustrate two different layouts:

- **Soft hypersurface oversampling:** `number_of_repeated_sampling=3`, hydro reuse off. iSS produces three samples of the same surface and SMASH evolves each sample. The final-state writer concatenates their particles in **one writer block with one event ID**. This seven-column format does not save the individual sample boundaries or IDs. One block therefore represents one hydro background and three sampling/afterburner realizations, not three independent collisions.
- **Hard hydro reuse:** `setReuseHydro=true`, `nReuseHydro=3`, three framework iterations. The three hard events have **different writer IDs (1, 2, 3)** but share one hydro background. The final-state headers do not contain a hydro-group ID; retain the reuse mapping alongside the output.

`N_hadrons` counts all saved particle rows in that writer block, including all concatenated soft samples; it is not the multiplicity of an individual hypersurface sample. Individual-sample correlations and fluctuations cannot be recovered from this flat file alone once sample boundaries have been lost. Retain a format or sidecar with those boundaries when they are needed. For hard reuse, retain the event-to-hydro mapping and the actual run controls/logs; the writer ID alone does not identify independent hydro backgrounds.

File rows, writer blocks, sampler repetitions and independent hydro backgrounds are separate counts. Events sharing a hydro background are not independent medium realizations. The example statistics and grouping are recorded in [sample_metadata.json](examples/sample_metadata.json).

## Hard-event weights and cross sections

Hard production may be generated in separate $\hat p_T$ intervals or with biased sampling to populate rare high-momentum events. Such samples generally require generator-aware reweighting and cross-section normalization when forming inclusive observables or combining bins. The hadron list preserves the following information:

| Field | Where stored | Meaning |
| --- | --- | --- |
| `weight` | Each event header | Dimensionless generator event weight. For the pinned PythiaGun this is Pythia's `info.weight()`, including the generator's sampling-weight convention. It is not a cross section or a hydro oversampling factor. |
| `pt_hat` | Each event header, when enabled | Pythia's hard-scattering scale in GeV for that event. It is not a final hadron or jet transverse momentum, and does not specify the configured generation-bin boundaries. |
| `sigmaGen` | File footer | Pythia's generated cross-section estimate for the run, in mb, with the configured process and generation cuts. It is a run quantity, not a separate cross section for every particle. |
| `sigmaErr` | File footer | Pythia's statistical uncertainty on that generated cross-section estimate, in mb. |

The [pinned PythiaGun interface](https://github.com/JETSCAPE/JETSCAPE/blob/3546d357141f54056af87f6f535467ed26a1289a/src/initialstate/PythiaGun.h) supplies these generator quantities through the [hard-process header](https://github.com/JETSCAPE/JETSCAPE/blob/3546d357141f54056af87f6f535467ed26a1289a/src/framework/HardProcess.cc). `sigmaGen` is the hard-process cross section; it is distinct from the inelastic NN cross-section input used by TRENTo to generate the medium.

Retain the headers and footer together with each original file's identity, configured pTHat interval, bias settings and generator bookkeeping (generated/accepted counts and weight sums, when available in the generator output). The seven-column rows do not carry that run information themselves. If files are merged or converted, preserve each run's cross-section metadata and event-to-run association. Hydro reuse and soft oversampling counts are separate from Pythia's hard-sampling weights.

The supplied hard example uses one pTHat interval with bias selection disabled and event weights equal to one. Unit weights do not provide the relative cross-section normalization between different generation bins. The soft-only example has `sigmaGen = sigmaErr = -1`, indicating unavailable hard-process cross-section metadata.

This guide describes the stored information and grouping conventions. Observable definitions, acceptance cuts, bin combination, reweighting/normalization formulas and uncertainty estimation are left to the user's analysis. The simple plotting helper is an I/O diagnostic rather than an inclusive hard-sector observable calculation.

JETSCAPE-analysis conversion may change storage and chunking while preserving the underlying particle information. Record its version, selected reader, conversion command and treatment of empty events, weights and footers. Do not assume that a `.parquet` filename alone specifies the schema or event grouping.
