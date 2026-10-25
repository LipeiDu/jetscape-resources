"""Strict streaming reader for JETSCAPE final-state ASCII v2 (seven columns)."""

from dataclasses import dataclass
import math


@dataclass
class Event:
    number: int
    metadata: dict
    particles: list


def read_events(path):
    """Yield writer blocks. A block need not equal one independent hydro event."""
    with open(path, encoding="utf-8") as handle:
        version = None
        current = None
        expected = None
        seen = set()
        for lineno, line in enumerate(handle, 1):
            fields = line.split()
            if not fields:
                continue
            if fields[0] == "#":
                if "JETSCAPE_FINAL_STATE" in fields:
                    index = fields.index("JETSCAPE_FINAL_STATE")
                    version = fields[index + 1]
                    if version != "v2":
                        raise ValueError("Only the documented v2 writer is supported")
                elif len(fields) > 2 and fields[1] == "Event":
                    if version != "v2":
                        raise ValueError("Missing v2 format header")
                    if current is not None:
                        if len(current.particles) != expected:
                            raise ValueError(f"Event {current.number}: particle count mismatch")
                        yield current
                    number = int(fields[2])
                    if number in seen:
                        raise ValueError(f"Duplicate event number {number}")
                    seen.add(number)
                    # Header metadata appears as named key/value pairs; column
                    # labels following a | delimiter are not metadata.
                    tail = fields[3:fields.index("|")] if "|" in fields else fields[3:]
                    if len(tail) % 2:
                        raise ValueError(f"Line {lineno}: malformed header metadata")
                    metadata = {}
                    for key, raw in zip(tail[::2], tail[1::2]):
                        value = float(raw)
                        if not math.isfinite(value):
                            raise ValueError(f"Line {lineno}: nonfinite {key}")
                        metadata[key] = value
                    counts = [metadata[key] for key in ("N_hadrons", "N_partons") if key in metadata]
                    if len(counts) != 1 or counts[0] < 0 or not counts[0].is_integer():
                        raise ValueError(f"Line {lineno}: missing/invalid particle count")
                    if "weight" not in metadata:
                        raise ValueError(f"Line {lineno}: missing event weight")
                    expected = int(counts[0])
                    current = Event(number, metadata, [])
                # Cross-section footer and other comments are retained in the
                # original file; they do not introduce a new event.
                continue
            if current is None or len(fields) != 7:
                raise ValueError(f"Line {lineno}: expected seven-column particle record inside an event")
            index, pid, status = (int(value) for value in fields[:3])
            values = tuple(float(value) for value in fields[3:])
            if index != len(current.particles) or not all(math.isfinite(x) for x in values):
                raise ValueError(f"Line {lineno}: invalid particle index or nonfinite momentum")
            current.particles.append((index, pid, status, *values))
            if len(current.particles) > expected:
                raise ValueError(f"Event {current.number}: too many particles")
        if current is None:
            raise ValueError("No complete event header found")
        if len(current.particles) != expected:
            raise ValueError(f"Event {current.number}: truncated particle block")
        yield current
