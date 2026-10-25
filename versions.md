# JETSCAPE releases after 3.7

Checked against the [official release notes](https://github.com/JETSCAPE/JETSCAPE/releases) on 25 October 2026. The latest listed release is **4.0.2**. This repository keeps its tested 3.7.1 source baseline; the following notes help assess an upgrade.

| Release | Date | Selected changes relevant to these workflows |
| --- | --- | --- |
| [3.7.1](https://github.com/JETSCAPE/JETSCAPE/releases/tag/v3.7.1) | 20 May 2025 | Final-state C++ reader and binary output; Qn-vector output improvements. |
| [3.7.2](https://github.com/JETSCAPE/JETSCAPE/releases/tag/v3.7.2) | 1 October 2025 | Hydro-memory flag and TRENTo epsilon fixes; hybrid-hadronization option ordering and build diagnostics. |
| [4.0](https://github.com/JETSCAPE/JETSCAPE/releases/tag/v4.0) | 26 January 2026 | Parallel surface finding, OpenMP thermal sampling and counter-based RNG work; initialization, macOS build and framework documentation changes; modified-medium MATTER/LBT capability. |
| [4.0.1](https://github.com/JETSCAPE/JETSCAPE/releases/tag/v4.0.1) | 2 February 2026 | SMASH 3.2.2 and Pythia 8.315 dependency updates; external-hydro header fix. |
| [4.0.2](https://github.com/JETSCAPE/JETSCAPE/releases/tag/v4.0.2) | 11 February 2026 | Alma Linux base Docker image and ARM64 build testing. |

The broad multistage workflow remains recognizable, but these changes are material for build environments, event sampling and numerical reproducibility. Release notes do not establish that spectra or posterior predictions are unchanged. Keep the pinned version for comparisons with a completed study. Evaluate a newer release in a separate installation, checking the effective XML/auxiliary inputs, required dependencies, output schema and a representative physics comparison before adopting it.

See [installation.md](installation.md) for the supported source revisions. The new-version summary is informational; this resource collection has not been validated against 4.0.2.
