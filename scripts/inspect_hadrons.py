#!/usr/bin/env python3
"""Validate final-state ASCII v2 blocks and summarize their particle contents."""

import argparse
from collections import Counter
import json
import math
from pathlib import Path

from hadron_io import read_events


def inspect(path, expected_events=None, require_particles=False):
    statuses = Counter()
    species = Counter()
    count = 0
    particles = 0
    sum_weight = 0.0
    sum_pt = 0.0
    metadata_keys = set()
    cross_section = {}
    # All statuses and species are retained. This is an I/O diagnostic, not a
    # charged-primary spectrum or a cross-section-normalized observable.
    for event in read_events(path):
        count += 1
        sum_weight += event.metadata["weight"]
        metadata_keys.update(event.metadata)
        for _, pid, status, energy, px, py, pz in event.particles:
            particles += 1
            statuses[status] += 1
            species[pid] += 1
            sum_pt += math.hypot(px, py)
    if expected_events is not None and count != expected_events:
        raise ValueError(f"Expected {expected_events} writer blocks, found {count}")
    if require_particles and particles == 0:
        raise ValueError("No final-state particles found")
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            fields = line.split()
            if len(fields) == 5 and fields[:2] == ["#", "sigmaGen"] and fields[3] == "sigmaErr":
                cross_section = {"sigmaGen_mb": float(fields[2]), "sigmaErr_mb": float(fields[4])}
                if not all(math.isfinite(value) for value in cross_section.values()):
                    raise ValueError("Nonfinite cross-section footer")
    return {
        "status": "passed", "writer_format": "JETSCAPE_FINAL_STATE_v2_seven_columns",
        "writer_blocks": count, "particle_rows": particles,
        "sum_event_weights": sum_weight,
        "mean_particle_pt_GeV_unweighted_all_statuses": sum_pt / particles if particles else None,
        "status_counts": dict(sorted(statuses.items())),
        "pid_counts": dict(sorted(species.items())), "metadata_keys": sorted(metadata_keys),
        "cross_section_footer": cross_section,
        "scope": "Structural I/O check; no independent-hydro count or physics validation inferred.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--expected-events", type=int)
    parser.add_argument("--require-particles", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = inspect(args.input, args.expected_events, args.require_particles)
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        with args.output.open("x") as handle:
            handle.write(text)
    print(text, end="")


if __name__ == "__main__":
    main()
