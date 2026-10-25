# Generate and inspect events

The examples use a new run directory and an explicit random seed. The runner copies mutable inputs and the executable into a staged layout, links runtime tables, and retains both the user XML and the exact main XML. Auxiliary files are supplied under [examples/](examples/). The source installation must contain the matching EOS/iSS/LBT tables and SMASH particle data as required by the selected modules.

## Soft sector only

```bash
python3 scripts/run_simulation.py \
  --source /path/to/JETSCAPE \
  --config examples/soft_AuAu200.xml \
  --run-dir /path/to/new-soft-run \
  --events 1 --seed 261025101 --execute
```

This runs TRENTo, free streaming, MUSIC, iSS and SMASH for Au+Au at 200 GeV, 30–40% centrality. The example disables hydro reuse and requests three iSS samples of each hypersurface. SMASH evolves each sample; the final-state writer concatenates their particles under the framework event ID. It does not preserve sample boundaries in the seven-column file. Sampling and reuse controls are discussed in [the settings guide](examples/README.md).

## Hard-focused events

```bash
python3 scripts/run_simulation.py \
  --source /path/to/JETSCAPE \
  --config examples/hard_AuAu200.xml \
  --run-dir /path/to/new-hard-run \
  --events 3 --seed 261025102 --execute
```

A full installation with iSS and SMASH is suitable: their omission from the XML disables those stages. Alternatively, `--profile hard-focused` avoids installing/linking them. The XML contains neither `SoftParticlization` nor `Afterburner`, so no iSS, SMASH or UrQMD is scheduled. Jet hadronization remains enabled: it converts hard partons into the final hadrons.

With `setReuseHydro=true` and `nReuseHydro=3`, three framework iterations use one medium background. Each hard event receives a distinct writer ID, despite the shared hydro. This runs medium generation followed by Pythia hard production, MATTER+LBT energy loss and colorless jet hadronization. Soft particlization and SMASH are absent. The example selects `20 < pTHat < 30 GeV` at 200 GeV with bias selection disabled. This is a small execution test, not an inclusive hard-event sample or an RAA calculation. For a new energy or hard sampling strategy, update all relevant settings and normalization conventions together.

The runner checks that TRENTo and Pythia energies agree, the hadronization energy is half the collision energy, MATTER and LBT share their switching scale and coupling, and the type-6 coefficients are positive physical values. It does not infer a complete physics tune from those checks.

## Other collision energies

Use `examples/soft_PbPb2760.xml`, `soft_PbPb5020.xml`, `hard_PbPb2760.xml` or `hard_PbPb5020.xml` with the same runner. Their collision, Pythia and hadronization energies are set consistently. See the [configuration table](examples/README.md) for normalizations and hard-scattering bins. The added Pb–Pb XMLs are configuration-checked examples; their event generation has not been run as part of these small Au–Au demonstrations.

## Container and scheduler use

Add `--container /path/to/base.sif` to either command when the executable needs a container environment. The default container command is `apptainer`; use `--container-runtime singularity` when appropriate. The runner uses a clean container environment, explicit source/build/run binds and one numerical thread. The container must provide the executable's compatible libraries; it does not need to contain the resource repository or JETSCAPE source.

For Slurm, set the absolute repository path and supply your site's account:

```bash
export JETSCAPE_RESOURCES=/path/to/jetscape-resources
sbatch --account=YOUR_ACCOUNT examples/run_slurm.sbatch \
  --source /path/to/JETSCAPE \
  --container /path/to/base.sif \
  --config /path/to/jetscape-resources/examples/soft_AuAu200.xml \
  --run-dir /path/to/new-soft-run --events 1 --seed 261025101
```

The example batch script requests one task/CPU, 8 GB and two hours. Review those resources for your system and settings. Run one independent simulation per process; request and record resources for larger campaigns deliberately. `sbatch` acceptance is not evidence that the program completed.

## Outputs and checks

Each attempt retains:

- `run_record.json`: requested controls, resolved command, selected input and
library hashes, table identities, timestamps and structural output checks.
- `stdout.log`, `stderr.log`: the generator's logs, including warnings.
- `runtime/config/user.xml`, `jetscape_main.xml`: actual inputs used.
- `runtime/build/event_final_state_hadrons.dat`: final-state ASCII output.

The runner fails if the generator exits nonzero or the file is missing, truncated, structurally inconsistent, has nonfinite momenta, contains no particles, or has the wrong number of writer blocks. These checks do not prove that a hard module was active or that a spectrum is physically validated; inspect the module logs and compare a sufficient statistical sample for that purpose.

Inspect separately with `scripts/inspect_hadrons.py`. For a simple pT diagnostic, install `requirements-plot.txt`, choose the PID and an explicitly identified status, and run:

```bash
python3 scripts/plot_hadrons.py /path/to/event_final_state_hadrons.dat \
  --pid 211 --status 27 --output /path/to/new-pion-check.png
```

The plot includes all rapidities and normalizes by the sum of writer-block weights and bin width. The bundled soft file combines three hypersurface samples in one writer block; its grouping and hard-event weighting metadata are described in the [hadron-format guide](hadron-format.md#counting-and-weights). It is not a charged-primary experimental spectrum or a cross-section-normalized hard yield. For detailed observables, select a matching JETSCAPE-analysis version/configuration and preserve the event-weight, cross-section, centrality and sampling definitions. ASCII-to-Parquet conversion is a separate step from calculating observables.
