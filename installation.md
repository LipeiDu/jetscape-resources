# Installation and build guide

The first supported source configuration is recorded in [software_versions.json](examples/software_versions.json):

| Component | Revision |
| --- | --- |
| JETSCAPE 3.7.1 | `3546d357141f54056af87f6f535467ed26a1289a` |
| MUSIC | `132448235467999067f1c01f340736139499ce16` |
| iSS | `db176d4cfaf804c9963f6927577d540f5f8be530` |
| Free-streaming | `e0a21feb48a922b4b4541ab0e4d745c65594bb5f` |
| SMASH 3.0 | `7eae4eb47f266f3234887aaec992c1715f494862` |

These identify the source setup used by the examples, rather than the latest available releases. Start from the [JETSCAPE instructions for that revision](https://github.com/JETSCAPE/JETSCAPE/blob/3546d357141f54056af87f6f535467ed26a1289a/README.md) when preparing the build environment. Native builds need a C++17 compiler, CMake, Boost, GSL, HDF5, Pythia8 and zlib. A compatible container may supply these dependencies. This repository does not distribute a base container or system libraries; source commits alone do not lock their identities.

## Prepare tables and the environment

Obtain the LBT data tables required by the chosen JETSCAPE revision. Its [get_lbtTab.sh](https://github.com/JETSCAPE/JETSCAPE/blob/3546d357141f54056af87f6f535467ed26a1289a/external_packages/get_lbtTab.sh) identifies the upstream archive. Extract them in a data directory or use a previously verified `LBT-tables` directory. The preparation script copies and hashes every supplied table; retain that record with the installation. This checks the supplied bytes, not whether an arbitrary archive matches the study. The [reference table checksums](examples/lbt_tables_sha256.json) identify the nine LBT files used in the execution checks.

Activate the intended build environment. Ensure that `git`, `cmake`, the compiler and Pythia's `pythia8-config` are available. The installer also accepts `--pythia-config /path/to/pythia8-config`, or discovers it through `PYTHIA8DIR/bin/pythia8-config`. Review the configure logs if a dependency is missing; avoid mixing libraries from unrelated host and container environments.

## Select a workflow

The default `legacy-soft` profile builds the complete iSS/SMASH soft chain. For hard-focused events, either profile works. A full installation can keep iSS and SMASH compiled while the hard XML omits them. To avoid those optional dependencies entirely, choose `--profile hard-focused`: source preparation omits iSS and SMASH, the installer skips SMASH configuration/compilation, and JETSCAPE uses `USE_MUSIC=ON`, `USE_FREESTREAM=ON`, `USE_ISS=OFF`, `USE_SMASH=OFF` and `USE_ROOT=OFF`. The supplied hard XML also includes no UrQMD module. Pythia and the other common dependencies are still required.

```bash
python3 scripts/install_jetscape.py \
  --prefix /path/to/new-hard-installation \
  --lbt-tables /path/to/LBT-tables \
  --profile hard-focused --jobs 4
```

Add `--execute` after checking the preview. If preparing source separately, pass `--profile hard-focused` to `prepare_source.py` too. For an existing prepared tree, pass the same profile to `build_jetscape.py`. A binary previously linked against SMASH still needs that library at runtime even if its XML disables the module; use a separate build directory with the hard profile to remove that dependency.

The full-stack installation and its small soft/hard runs were tested. The hard profile's command selection, module exclusions and runtime staging are tested locally; a fresh full native build and event run with this profile remain untested.

## Install into a new prefix

Preview the commands:

```bash
python3 scripts/install_jetscape.py \
  --prefix /path/to/new-installation \
  --lbt-tables /path/to/LBT-tables \
  --jobs 4
```

Add `--execute` to clone the pinned sources, copy the tables, build SMASH's `smash_shared` target and build JETSCAPE. The resulting source/build tree is `/path/to/new-installation/source`, with the executable in `source/build/`. Existing prefixes are refused. A failed attempt and its logs remain available; use another prefix for a new attempt.

The `legacy-soft` build profile enables MUSIC, free streaming, iSS and SMASH, with ROOT disabled. MATTER and LBT are part of this JETSCAPE source build. ROOT writers need a separately configured build; the included examples use ASCII.

For a site without network access on compute nodes, use `scripts/prepare_source.py --help` to prepare sources on an allowed node first, or give the installer `--reference-source /path/to/existing/JETSCAPE`. Reference mode clones the exact pinned commits from separate local Git repositories for JETSCAPE and each component. It does not reuse their build directories, copy uncommitted source changes, or modify the reference checkout. All requested commits must exist locally. This mode supports source preparation when direct network access is unavailable.

Inside an Apptainer environment, bind both the new installation's parent and any local reference source/table directories at their absolute paths. Build on an allocated compute node. Set `--jobs` no higher than the allocated CPU count.

## Build already prepared sources

```bash
python3 scripts/build_jetscape.py \
  --source /path/to/JETSCAPE \
  --build-dir /path/to/new-build \
  --profile legacy-soft --jobs 4 --dry-run
```

Remove `--dry-run` to configure/build. The new directory must be absent or empty. This helper expects the external packages for the selected profile to be prepared already (including the SMASH shared library for `legacy-soft`); the full installer handles those stages. Extra CMake cache settings use `--cmake-arg=-DNAME=VALUE`.

Retain `installation.json`, phase logs, `source_preparation.json` and `build_record.json`. They describe commands, source identity, copied tables and outcomes. Also retain compiler and library versions or a container checksum. The configuration and particle checks described in [the simulation guide](simulations.md) are required after building; a successful compilation alone does not validate the generated physics.
