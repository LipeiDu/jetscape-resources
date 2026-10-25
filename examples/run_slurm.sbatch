#!/usr/bin/env bash
#SBATCH --job-name=jetscape-example
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --output=jetscape-%j.out
#SBATCH --error=jetscape-%j.err

set -euo pipefail
: "${JETSCAPE_RESOURCES:?Set JETSCAPE_RESOURCES to this repository's absolute path}"
# Pass the run_simulation.py arguments after the sbatch filename.
python3 "${JETSCAPE_RESOURCES}/scripts/run_simulation.py" "$@" --execute
