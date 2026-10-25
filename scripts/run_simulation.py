#!/usr/bin/env python3
"""Stage and run JETSCAPE in a fresh directory; preview unless --execute is given."""

import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

from inspect_hadrons import inspect
from build_jetscape import git_identity


def sha256(path):
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def validate_config(root):
    if root.tag != "jetscape" or root.find("nEvents") is None or root.find("Random/seed") is None:
        raise ValueError("Require a jetscape root, nEvents and Random/seed")
    physics = root.find("IS/Trento/PhysicsInputs")
    if physics is None:
        raise ValueError("This runner's examples require TRENTo PhysicsInputs")
    energy = float(physics.attrib["sqrts"])
    hard = root.find("Hard/PythiaGun")
    if hard is not None:
        if float(hard.findtext("eCM")) != energy:
            raise ValueError("Pythia eCM differs from TRENTo sqrts")
        if float(root.findtext("JetHadronization/eCMforHadronization")) != energy / 2:
            raise ValueError("Hadronization energy must be sqrts/2 for this example")
        matter = root.find("Eloss/Matter")
        lbt = root.find("Eloss/Lbt")
        if matter is None or lbt is None:
            raise ValueError("Hard example requires both MATTER and LBT")
        for key in ("Q0", "alphas"):
            if float(matter.findtext(key)) != float(lbt.findtext(key)):
                raise ValueError(f"MATTER/LBT {key} mismatch")
        if int(matter.findtext("QhatParametrizationType")) == 6:
            for key in ("qhatA", "qhatB", "qhatC"):
                value = float(matter.findtext(key))
                if not math.isfinite(value) or value <= 0:
                    raise ValueError("Type-6 coefficients must be positive physical values, not log coordinates")
    if root.findtext("JetScapeWriterFinalStateHadronsAscii", "off").strip().lower() != "on":
        raise ValueError("Final-state hadron ASCII writer must be enabled")
    if root.findtext("outputFilename", "").strip() != "event":
        raise ValueError("Examples require the relative output basename 'event'")
    return energy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--build-dir", type=Path, help="Defaults to SOURCE/build")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--input-dir", type=Path, default=Path(__file__).resolve().parents[1] / "examples")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--events", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--container", type=Path)
    parser.add_argument("--container-runtime", default="apptainer")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    build = (args.build_dir or source / "build").expanduser().resolve()
    inputs = args.input_dir.expanduser().resolve()
    destination = args.run_dir.expanduser().resolve()
    if args.events < 1 or not 0 < args.seed < 900000000:
        parser.error("Require positive events and an explicit seed in 1..899999999")
    if destination.exists():
        parser.error("Run directory already exists; choose a new attempt")
    config = args.config.expanduser().resolve()
    root = ET.parse(config).getroot()
    try:
        energy = validate_config(root)
    except (ValueError, TypeError, KeyError) as error:
        parser.error(str(error))
    root.find("nEvents").text = str(args.events)
    root.find("Random/seed").text = str(args.seed)
    required = {
        "runJetscape": build / "runJetscape",
        "jetscape_main.xml": inputs / "jetscape_main.xml",
        "freestream_input": inputs / "freestream_input",
        "music_input": inputs / "music_input",
    }
    assets = {"EOS": build / "EOS", "LBT-tables": build / "LBT-tables"}
    if root.find("SoftParticlization") is not None:
        required["iSS_parameters.dat"] = inputs / "iSS_parameters.dat"
        assets["iSS_tables"] = build / "iSS_tables"
    if root.find("Afterburner") is not None:
        required["smash_config.yaml"] = inputs / "smash_config.yaml"
        for name in ("particles.txt", "decaymodes.txt"):
            required[name] = source / "external_packages/smash/smash_code/input" / name
    for path in [*required.values(), *assets.values()]:
        if not path.exists():
            parser.error(f"Missing required runtime input: {path}")
    if not os.access(required["runJetscape"], os.X_OK):
        parser.error("runJetscape is not executable")
    work = destination / "runtime/build"
    command = [str(work / "runJetscape"), "../config/user.xml", "../config/jetscape_main.xml"]
    if args.container:
        image = args.container.expanduser().resolve()
        if not image.is_file() or shutil.which(args.container_runtime) is None:
            parser.error("Container image or runtime is unavailable")
        command = [args.container_runtime, "exec", "--cleanenv", "--no-home",
                   "--bind", f"{source}:{source}:ro", "--bind", f"{destination}:{destination}",
                   "--bind", f"{build}:{build}:ro",
                   "--pwd", str(work), "--env", "OMP_NUM_THREADS=1,MKL_NUM_THREADS=1,OPENBLAS_NUM_THREADS=1",
                   str(image), *command]
    record = {
        "schema_version": 1, "status": "preview", "command": command,
        "run_directory": str(destination), "energy_GeV": energy,
        "framework_events_requested": args.events, "seed": args.seed,
        "hydro_reuse": root.findtext("setReuseHydro"), "n_reuse_hydro": root.findtext("nReuseHydro"),
        "iss_repeated_sampling": root.findtext("SoftParticlization/iSS/number_of_repeated_sampling"),
        "config_sha256": sha256(config),
        "source_git": git_identity(source),
        "required_files": {key: {"path": str(value), "sha256": sha256(value)} for key, value in required.items()},
        "asset_directories": {key: str(value.resolve()) for key, value in assets.items()},
        "threads": 1,
    }
    if not args.execute:
        print(json.dumps(record, indent=2))
        return 0
    destination.mkdir(parents=True, exist_ok=False)
    work.mkdir(parents=True)
    config_dir = destination / "runtime/config"
    config_dir.mkdir()
    ET.indent(root)
    ET.ElementTree(root).write(config_dir / "user.xml", encoding="utf-8", xml_declaration=True)
    for name in ("jetscape_main.xml",):
        shutil.copy2(required[name], config_dir / name)
    for name in ("runJetscape", "freestream_input", "music_input", "iSS_parameters.dat", "smash_config.yaml"):
        if name in required:
            shutil.copy2(required[name], work / name)
    for name, path in assets.items():
        (work / name).symlink_to(path.resolve(), target_is_directory=True)
    if "particles.txt" in required:
        smash = destination / "runtime/external_packages/smash"
        data = smash / "smash_code/input"
        data.mkdir(parents=True)
        for name in ("particles.txt", "decaymodes.txt"):
            (data / name).symlink_to(required[name].resolve())
        shutil.copy2(required["smash_config.yaml"], smash / "smash_config.yaml")
    record["effective_config_sha256"] = sha256(config_dir / "user.xml")
    record["asset_files_sha256"] = {
        f"{label}/{item.relative_to(path)}": sha256(item)
        for label, path in assets.items() for item in sorted(path.rglob("*")) if item.is_file()
    }
    libraries = sorted(set(build.rglob("*.so")))
    smash_library = source / "external_packages/smash/smash_code/build/src/libsmash.so"
    if smash_library.is_file():
        libraries.append(smash_library)
    record["build_libraries_sha256"] = {str(path): sha256(path) for path in libraries if path.is_file()}
    if args.container:
        record["container_sha256"] = sha256(image)
    record["started_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    record["slurm_job_id"] = os.environ.get("SLURM_JOB_ID")
    record["status"] = "running"
    manifest = destination / "run_record.json"
    manifest.write_text(json.dumps(record, indent=2) + "\n")
    environment = os.environ.copy()
    environment.update(OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    code = 1
    try:
        with (destination / "stdout.log").open("w") as stdout, (destination / "stderr.log").open("w") as stderr:
            result = subprocess.run(command, cwd=work, env=environment, stdout=stdout, stderr=stderr, check=False)
        code = result.returncode
        record["simulation_exit_code"] = code
        if code == 0:
            output = work / "event_final_state_hadrons.dat"
            record["output_check"] = inspect(output, args.events, require_particles=True)
            if root.find("Hard") is not None:
                cross_section = record["output_check"]["cross_section_footer"]
                if not cross_section or cross_section["sigmaGen_mb"] <= 0 or cross_section["sigmaErr_mb"] < 0:
                    raise ValueError("Hard event output lacks valid positive cross-section metadata")
            record["output_sha256"] = sha256(output)
            record["output_bytes"] = output.stat().st_size
            changed = []
            for name, item in record["required_files"].items():
                if sha256(Path(item["path"])) != item["sha256"]:
                    changed.append(name)
            for name, expected in record["build_libraries_sha256"].items():
                if sha256(Path(name)) != expected:
                    changed.append(name)
            for name, expected in record["asset_files_sha256"].items():
                label, rel = name.split("/", 1)
                if sha256(assets[label] / rel) != expected:
                    changed.append(name)
            record["referenced_inputs_unchanged"] = not changed
            if changed:
                raise ValueError("Referenced runtime/input files changed during execution: " + ", ".join(changed[:10]))
        record["status"] = "passed" if code == 0 else "failed"
    except (OSError, ValueError, KeyboardInterrupt) as error:
        code = 130 if isinstance(error, KeyboardInterrupt) else 1
        record["status"] = "failed"
        record["error"] = str(error)
    record["finished_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    manifest.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"status": record["status"], "record": str(manifest)}, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
