#!/usr/bin/env python3
"""Configure and build an existing JETSCAPE checkout in a fresh directory."""

import argparse
import datetime
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys


def git_identity(source):
    def read(*args):
        result = subprocess.run(
            ["git", "--no-optional-locks", "-C", str(source), *args],
            capture_output=True, text=True, check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else None

    if shutil.which("git") is None:
        return {"commit": None, "status": None}
    top = read("rev-parse", "--show-toplevel")
    if top is None or Path(top).resolve() != source:
        return {"commit": None, "status": None}
    return {
        "commit": read("rev-parse", "HEAD"),
        "status": read("status", "--porcelain", "--untracked-files=normal"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--build-dir", required=True, type=Path)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--profile", choices=("default", "legacy-soft", "hard-focused"), default="default")
    parser.add_argument("--cmake-arg", action="append", default=[],
                        help="Additional -D cache setting; use --cmake-arg=-DNAME=VALUE")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    build = args.build_dir.expanduser().resolve()
    if not (source / "CMakeLists.txt").is_file():
        parser.error("--source must contain CMakeLists.txt")
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    if build == source or build in source.parents:
        parser.error("--build-dir must differ from the source and its parents")
    if build.exists() and (not build.is_dir() or any(build.iterdir())):
        parser.error("--build-dir must be absent or empty; existing builds are preserved")
    if any(not value.startswith("-D") or "=" not in value for value in args.cmake_arg):
        parser.error("--cmake-arg accepts only -DNAME=VALUE cache settings")
    settings = []
    environment = os.environ.copy()
    overrides = {}
    if args.profile == "legacy-soft":
        settings = ["-DUSE_ROOT=OFF", "-DUSE_MUSIC=ON", "-DUSE_ISS=ON",
                    "-DUSE_FREESTREAM=ON", "-DUSE_SMASH=ON"]
        overrides["SMASH_DIR"] = str(source / "external_packages/smash/smash_code")
        environment.update(overrides)
    if args.profile == "hard-focused":
        settings = ["-DUSE_ROOT=OFF", "-DUSE_MUSIC=ON", "-DUSE_FREESTREAM=ON",
                    "-DUSE_ISS=OFF", "-DUSE_SMASH=OFF"]
    commands = [
        ["cmake", "-S", str(source), "-B", str(build), *settings, *args.cmake_arg],
        ["cmake", "--build", str(build), "--parallel", str(args.jobs)],
    ]
    for command in commands:
        prefix = " ".join(f"{key}={shlex.quote(value)}" for key, value in overrides.items())
        print((prefix + " " if prefix else "") + shlex.join(command), flush=True)
    if args.dry_run:
        return 0
    if shutil.which("cmake") is None:
        parser.error("cmake is unavailable; activate the intended build environment first")
    record = {
        "started_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source": str(source), "build_dir": str(build), "profile": args.profile,
        "source_git": git_identity(source), "commands": commands,
        "environment_overrides": overrides, "status": "started",
        "scope": "Observed source identity and build commands; not a dependency lock or physics validation.",
    }
    build.mkdir(parents=True, exist_ok=True)
    manifest = build / "build_record.json"
    manifest.write_text(json.dumps(record, indent=2) + "\n")
    exit_code = 0
    try:
        for command in commands:
            result = subprocess.run(command, env=environment, check=False)
            if result.returncode:
                exit_code = result.returncode
                record["failed_command"] = command
                break
        record["status"] = "completed" if exit_code == 0 else "failed"
    except (OSError, KeyboardInterrupt) as error:
        record["status"] = "failed"
        record["error"] = str(error)
        exit_code = 130 if isinstance(error, KeyboardInterrupt) else 1
    record["exit_code"] = exit_code
    record["finished_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    manifest.write_text(json.dumps(record, indent=2) + "\n")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
