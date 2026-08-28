"""Materialize an environment and a cell directory for each cell.

A cell directory is self-contained and disposable:

    <work>/cells/<cell>/
        installation/   rendered installation.yaml, room, haiku.rag.yaml
        environments/   sandbox environments, each with its own .venv
        uploads/        the room-volume fixture
        workdirs/  transcripts/  db/
        spec.json       what 'run.py' needs to drive this cell

Code-axis environments live under '<work>/envs/<arm>' and are shared by the
cells that use them.
"""

from __future__ import annotations

import json
import pathlib
import shutil

from soliplex_lab_harness import environs

from . import cells as cells_module

HARNESS_PIN = (
    "soliplex-lab-harness @ "
    "git+https://github.com/soliplex/lab_harness@v0.2"
)
PYTHON = "3.13"


def render_installation(
    source: pathlib.Path, destination: pathlib.Path, cell: cells_module.Cell
) -> None:
    shutil.copytree(source, destination)
    template = destination / "installation.yaml.in"
    rendered = (
        template.read_text(encoding="utf-8")
        .replace("@@BASE_URL@@", cell.model.base_url)
        .replace("@@MODEL@@", cell.model.model_id)
    )
    (destination / "installation.yaml").write_text(
        rendered, encoding="utf-8"
    )
    template.unlink()
    # The sandbox environments are a sibling of the installation, not part
    # of it; 'installation.yaml' points at '../environments'.
    shutil.rmtree(destination / "environments")


def build_sandbox_environments(
    source: pathlib.Path,
    destination: pathlib.Path,
    runner: environs.Runner = environs.run,
) -> list[str]:
    """Copy each sandbox environment and 'uv sync' it.

    Verifies afterwards that the environment is not empty of its own
    dependencies: a uv project sharing a name with one of its dependencies
    resolves to nothing while still exiting cleanly.
    """
    shutil.copytree(source, destination)
    built = []
    for directory in sorted(p for p in destination.iterdir() if p.is_dir()):
        runner(["uv", "sync"], directory)
        built.append(directory.name)
    return built


def overlay_for(
    arm: cells_module.Arm, work: pathlib.Path, runner=environs.run
) -> list[environs.Overlay]:
    """Extract 'SKILL.md' from another release, for an overlay arm.

    The file comes out of a throwaway install of that version, so the arm
    is defined entirely by versions -- no checkout, and nothing to keep in
    sync by hand.
    """
    if arm.overlay_from is None:
        return []
    kept = work / "overlays" / arm.name / "SKILL.md"
    if not kept.is_file():
        # Installing a whole extra soliplex to copy one file out is slow, so
        # the extracted file is cached and the donor built only once.
        donor = environs.build(
            environs.Pin(
                name=f"donor-{arm.overlay_from}",
                version=arm.overlay_from,
            ),
            work / "donors" / arm.overlay_from,
            python=PYTHON,
            recreate=True,
            runner=runner,
        )
        kept.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            donor.site_packages() / cells_module.SKILL_MD, kept
        )
    return [
        environs.Overlay(
            source=kept,
            destination=cells_module.SKILL_MD,
            note=f"SKILL.md from soliplex {arm.overlay_from}",
        )
    ]


def build_environment(
    arm: cells_module.Arm,
    work: pathlib.Path,
    runner: environs.Runner = environs.run,
) -> environs.Environment:
    environment = environs.build(
        environs.Pin(name=arm.name, version=arm.version),
        work / "envs" / arm.name,
        extra_requirements=(HARNESS_PIN,),
        overlays=overlay_for(arm, work, runner),
        python=PYTHON,
        recreate=True,
        runner=runner,
    )
    # Raises unless the install matches its own RECORD except where an
    # overlay says otherwise -- so an arm cannot silently be the wrong arm.
    # Needs no trials, so it belongs here where it cannot be skipped.
    environs.verify_install(environment)
    return environment


def build_cell(
    cell: cells_module.Cell,
    environment: environs.Environment,
    work: pathlib.Path,
    trials: int,
) -> pathlib.Path:
    from .fixture import write_fixture

    root = work / "cells" / cell.name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    for name in ("workdirs", "transcripts", "db", "uploads/threads"):
        (root / name).mkdir(parents=True)

    template = cells_module.jig_root() / "installation"
    render_installation(template, root / "installation", cell)
    build_sandbox_environments(
        template / "environments", root / "environments"
    )
    expected = write_fixture(root / "uploads" / "rooms" / "workbench")

    spec = {
        "cell": cell.name,
        "installation": str(root / "installation" / "installation.yaml"),
        "cwd": str(root),
        "room_id": "workbench",
        "task": cell.task,
        "trials": trials,
        "expected": expected,
        "results": str(work / "results" / f"{cell.name}.jsonl"),
        "metadata": {
            **environment.metadata(),
            "model": cell.model.model_id,
            "endpoint": cell.model.base_url,
            "arm_note": cell.arm.note,
        },
    }
    (root / "spec.json").write_text(
        json.dumps(spec, indent=2), encoding="utf-8"
    )
    return root
