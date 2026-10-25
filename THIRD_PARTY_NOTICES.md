# Sources, attribution and licenses

The resource helpers use [GPLv3-or-later](COPYING). Original software, research and datasets retain their own attribution and terms.

## Soft-sector resources

The reference-table and observable-schema metadata derive from [j-f-paquet/js-sims-bayes](https://github.com/j-f-paquet/js-sims-bayes) at revision `9c8ffc63cc0f79ddb34d1d91c208b0e4cac9d39e`, particularly `src/configurations.py` and `src/bins_and_cuts.py`. The original study is credited in the [soft guide](soft/README.md). The downloader caches selected, verified public input files; the original datasets and serialized emulators remain upstream. The included `soft/posterior.npz` is a locally computed full-data Grad posterior rerun by Lipei Du using the study code and saved emulators, with its scientific target and source identities recorded in [posterior_metadata.json](soft/posterior_metadata.json). The MAP comparison credits the paper’s printed Table II separately from this local calculation. The upstream MIT notice is retained below.

```text
The MIT License (MIT)
Copyright (c) 2018 Jonah Bernhard

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

```

## Hard-sector sample data

[hard/MCMCSamples.txt.bz2](hard/MCMCSamples.txt.bz2) contains MCMC samples provided by lead authors of R. Ehlers et al. (JETSCAPE), *Bayesian Inference analysis of jet quenching using inclusive jet and hadron suppression measurements*, Phys. Rev. C **111**, 054913 (2025), [arXiv:2408.08247](https://arxiv.org/abs/2408.08247). Please cite the original study when using these samples. The [hard guide](hard/README.md) describes their use; hashes and column definitions are in [metadata.json](hard/metadata.json). No separate data license is specified in this collection; the helper code’s GPL license does not assign a license to the sample data.

## Simulation examples

The configurations use JETSCAPE and its component interfaces. Source repositories and immutable revisions are listed in [examples/software_versions.json](examples/software_versions.json). The [example guide](examples/README.md) identifies the related studies and distinguishes these short simulation examples from calibration ensembles.
