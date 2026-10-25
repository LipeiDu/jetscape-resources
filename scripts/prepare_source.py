#!/usr/bin/env python3
"""Prepare pinned JETSCAPE sources and copy supplied LBT tables to a new directory."""

import argparse
import datetime
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
import shutil
import subprocess


def run(command):
    subprocess.run(command, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--versions", type=Path, default=Path(__file__).resolve().parents[1] / "examples/software_versions.json")
    parser.add_argument("--lbt-tables", type=Path, required=True)
    parser.add_argument("--reference-source", type=Path, help="Clone pinned commits from a local source tree instead of the network")
    parser.add_argument("--profile", choices=("legacy-soft", "hard-focused"), default="legacy-soft")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    destination = args.destination.expanduser().resolve()
    tables = args.lbt_tables.expanduser().resolve()
    if destination.exists():
        parser.error("Destination already exists; previous attempts are preserved")
    if not tables.is_dir() or not any(tables.iterdir()):
        parser.error("--lbt-tables must name a nonempty table directory")
    if destination == tables or tables in destination.parents:
        parser.error("Destination must be outside the table source directory")
    if args.reference_source:
        reference = args.reference_source.expanduser().resolve()
        if destination == reference or reference in destination.parents:
            parser.error("Destination must be outside the reference source checkout")
    version_bytes = args.versions.read_bytes()
    spec = json.loads(version_bytes)
    commands = []
    for item in spec["repositories"]:
        if args.profile == "hard-focused" and item["path"] in (
                "external_packages/iSS", "external_packages/smash/smash_code"):
            continue
        if not re.fullmatch(r"[0-9a-f]{40}", item["commit"]):
            parser.error("Each source revision must be a full 40-character Git commit")
        rel = PurePosixPath(item["path"])
        if rel.is_absolute() or ".." in rel.parts:
            parser.error("Invalid repository destination in version manifest")
        source = item["url"]
        if args.reference_source:
            local = args.reference_source.expanduser().resolve() / str(rel)
            top = subprocess.check_output(["git", "-C", str(local), "rev-parse", "--show-toplevel"], text=True).strip()
            if Path(top).resolve() != local:
                parser.error(f"Reference component has no independent Git history: {local}")
            subprocess.run(["git", "-C", str(local), "cat-file", "-e", item["commit"] + "^{commit}"], check=True)
            source = str(local)
        target = destination / str(rel)
        commands.extend([
            ["git", "clone", "--no-hardlinks", "--no-checkout", source, str(target)],
            ["git", "-C", str(target), "checkout", "--detach", item["commit"]],
        ])
    report = {"status": "preview", "profile": args.profile, "commands": commands,
              "versions_sha256": hashlib.sha256(version_bytes).hexdigest(),
              "lbt_tables_source": str(tables), "destination": str(destination)}
    if not args.execute:
        print(json.dumps(report, indent=2))
        return 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    report["started_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    # Keep the record beside the new source so it can describe a partial clone.
    record = destination.parent / (destination.name + "_preparation.json")
    if record.exists():
        parser.error("Preparation record already exists; choose a fresh destination")
    record.write_text(json.dumps(report, indent=2) + "\n")
    code = 0
    try:
        for command in commands:
            run(command)
        target = destination / "external_packages/LBT-tables"
        shutil.copytree(tables, target)
        hashes = {}
        for path in sorted(target.rglob("*")):
            if path.is_file():
                hashes[str(path.relative_to(target))] = hashlib.sha256(path.read_bytes()).hexdigest()
        report["lbt_tables_sha256"] = hashes
        report["status"] = "prepared"
    except (OSError, subprocess.CalledProcessError) as error:
        report["status"] = "failed"
        report["error"] = str(error)
        code = 1
    report["finished_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    record.write_text(json.dumps(report, indent=2) + "\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
