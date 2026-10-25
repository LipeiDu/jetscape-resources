#!/usr/bin/env python3
"""Prepare and build pinned JETSCAPE sources for a soft or hard-focused workflow in a new prefix."""

import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--lbt-tables", type=Path, required=True)
    parser.add_argument("--reference-source", type=Path)
    parser.add_argument("--pythia-config", type=Path)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--profile", choices=("legacy-soft", "hard-focused"), default="legacy-soft")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    prefix = args.prefix.expanduser().resolve()
    if prefix.exists() or args.jobs < 1:
        parser.error("Require a new prefix and a positive job count")
    pythia = args.pythia_config
    if pythia is None and os.environ.get("PYTHIA8DIR"):
        pythia = Path(os.environ["PYTHIA8DIR"]) / "bin/pythia8-config"
    if pythia is None and shutil.which("pythia8-config"):
        pythia = Path(shutil.which("pythia8-config"))
    if pythia is None or not pythia.is_file():
        parser.error("Activate the build environment or provide --pythia-config")
    source = prefix / "source"
    smash = source / "external_packages/smash/smash_code"
    scripts = Path(__file__).resolve().parent
    prepare = [sys.executable, str(scripts / "prepare_source.py"), "--destination", str(source),
               "--lbt-tables", str(args.lbt_tables.expanduser().resolve()), "--profile", args.profile, "--execute"]
    if args.reference_source:
        prepare += ["--reference-source", str(args.reference_source.expanduser().resolve())]
    commands = [prepare]
    if args.profile == "legacy-soft":
        commands += [
            ["cmake", "-S", str(smash), "-B", str(smash / "build"), "-DPythia_CONFIG_EXECUTABLE=" + str(pythia.resolve())],
            ["cmake", "--build", str(smash / "build"), "--target", "smash_shared", "--parallel", str(args.jobs)],
        ]
    commands += [
        [sys.executable, str(scripts / "build_jetscape.py"), "--source", str(source),
         "--build-dir", str(source / "build"), "--profile", args.profile, "--jobs", str(args.jobs)],
    ]
    record = {"status": "preview", "profile": args.profile, "prefix": str(prefix), "commands": commands,
              "pythia_config": str(pythia.resolve()),
              "scope": "Pinned source build; host libraries and input tables require separate provenance."}
    if not args.execute:
        print(json.dumps(record, indent=2))
        return 0
    prefix.mkdir(parents=True, exist_ok=False)
    record["started_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    record["slurm_job_id"] = os.environ.get("SLURM_JOB_ID")
    record["status"] = "running"
    manifest = prefix / "installation.json"
    code = 0
    try:
        for i, command in enumerate(commands):
            record["phase"] = i
            manifest.write_text(json.dumps(record, indent=2) + "\n")
            with (prefix / (f"phase_{i}.log")).open("w") as log:
                result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=False)
            if result.returncode:
                record["failed_command"] = command
                code = result.returncode
                break
        record["status"] = "built" if code == 0 else "failed"
    except (OSError, KeyboardInterrupt) as error:
        record["status"] = "failed"
        record["error"] = str(error)
        code = 130 if isinstance(error, KeyboardInterrupt) else 1
    record["exit_code"] = code
    record["finished_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    manifest.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"status": record["status"], "record": str(manifest)}, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
