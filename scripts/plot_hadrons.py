#!/usr/bin/env python3
"""Plot a named PID/status pT distribution as an event-weighted I/O diagnostic."""

import argparse
from pathlib import Path

from hadron_io import read_events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--pid", type=int, default=211, help="Exact PDG ID, default pi+")
    parser.add_argument("--status", type=int, required=True, help="Select one documented particle status")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pt-max", type=float, default=5.0)
    parser.add_argument("--bins", type=int, default=50)
    args = parser.parse_args()
    if args.output.exists() or args.pt_max <= 0 or args.bins < 1:
        parser.error("Choose a new output file, positive pT limit and positive bin count")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import math
    counts = [0.0] * args.bins
    sum_weights = 0.0
    for event in read_events(args.input):
        sum_weights += event.metadata["weight"]
        for _, pid, status, energy, px, py, pz in event.particles:
            if pid == args.pid and status == args.status:
                pt = math.hypot(px, py)
                if pt < args.pt_max:
                    counts[int(pt / args.pt_max * args.bins)] += event.metadata["weight"]
    if sum_weights <= 0:
        raise ValueError("Nonpositive total event weight; inspect weight conventions first")
    width = args.pt_max / args.bins
    x = [(i + 0.5) * width for i in range(args.bins)]
    y = [value / sum_weights / width for value in counts]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.step(x, y, where="mid")
    ax.set(xlabel=r"$p_T$ [GeV]", ylabel=r"Weighted particles / writer block / GeV",
           title=f"PID {args.pid}, status {args.status}; all rapidities")
    ax.text(0.98, 0.95, "I/O diagnostic", transform=ax.transAxes, ha="right", va="top")
    fig.tight_layout()
    fig.savefig(args.output)
    plt.close(fig)


if __name__ == "__main__":
    main()
