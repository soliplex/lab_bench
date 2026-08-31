"""Drive the experiment set.

    python -m room_behavior build   <work> [--matrix M] [--trials N]
    python -m room_behavior run     <work> [--cells a,b]
    python -m room_behavior verify-assumptions <work> [--cells a,b]
    python -m room_behavior report  <work>

The intended order spends no turn twice:

    build <work>              # installs once, and verifies each install
    run <work> --trials 1     # one turn per cell, kept
    verify <work>             # assert what only a turn can show
    run <work> --trials 20    # tops each cell up to 20

'run' treats the spec's 'trials' as a target and tops up, so the smoke turn
counts toward N and an interrupted run resumes.

'build' is slow and idempotent: it installs soliplex once per arm and syncs
each sandbox environment. 'run' shells into each cell's own code-axis
environment, which is the point -- the software under test is installed, not
imported from a checkout.

**'build' takes the matrix; everything else reads it back.** The experiment
declares which arms, prompt styles and models it crosses; 'build' resolves
that and writes '<work>/matrix.json'. 'run', 'verify-assumptions' and
'report' load it from there rather than recomputing it, so a work directory
can be interpreted without the jig revision that produced it. With no
--matrix, the default reproduces soliplex/lab_bench#4.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

from soliplex_lab_harness import preconditions

from . import build as build_module
from . import cells as cells_module
from . import report as report_module
from . import verify_assumptions
from .fixture import write_fixture


def selected(
    matrix: cells_module.Matrix, names: str | None
) -> list[cells_module.Cell]:
    if not names:
        return matrix.cells()
    wanted = [n.strip() for n in names.split(",") if n.strip()]
    return [matrix.by_name(name) for name in wanted]


def do_build(
    work: pathlib.Path,
    matrix: cells_module.Matrix,
    trials: int,
    names: str | None,
) -> int:
    matrix.save(work / "matrix.json")
    chosen = selected(matrix, names)
    environments: dict[str, object] = {}
    for cell in chosen:
        arm = cell.arm
        if arm.name not in environments:
            print(f"building env {arm.name} (soliplex=={arm.version})")
            environments[arm.name] = build_module.build_environment(
                arm, work
            )
        root = build_module.build_cell(
            cell, environments[arm.name], work, trials
        )
        print(f"  cell {cell.name} -> {root}")
    # Raises unless every prompt-axis arm installed distinct text. Like the
    # RECORD check on an install, this needs nothing but the built tree, so
    # it runs here and cannot be skipped.
    for style, found in sorted(
        build_module.verify_prompt_styles(work, matrix).items()
    ):
        print(f"prompt style {style}: {found}")
    return 0


def do_run(
    work: pathlib.Path, names: str | None, trials: int | None
) -> int:
    matrix = cells_module.load_matrix(work)
    failures = 0
    for cell in selected(matrix, names):
        spec = work / "cells" / cell.name / "spec.json"
        if not spec.exists():
            print(f"skipping {cell.name}: not built", file=sys.stderr)
            failures += 1
            continue
        declared = json.loads(spec.read_text(encoding="utf-8"))
        python = declared["python"]
        script = pathlib.Path(build_module.__file__).with_name("run.py")
        print(f"=== {cell.name} ===", flush=True)
        argv = [python, str(script), str(spec)]
        if trials is not None:
            argv.append(str(trials))
        completed = subprocess.run(  # noqa: S603 -- argv is built
            argv, check=False
        )
        failures += completed.returncode != 0
    return 1 if failures else 0


def do_verify_assumptions(
    work: pathlib.Path, names: str | None
) -> int:
    matrix = cells_module.load_matrix(work)
    results = verify_assumptions.verify_all(work, selected(matrix, names))
    print(preconditions.render(results), flush=True)
    try:
        preconditions.assert_ok(results)
    except preconditions.Failed:
        return 1
    return 0


def do_report(work: pathlib.Path) -> int:
    matrix = cells_module.load_matrix(work)
    expected = write_fixture(work / "expected")
    print(report_module.report(work, matrix, expected))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="room_behavior")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("build", "run", "verify-assumptions", "report"):
        child = sub.add_parser(name)
        child.add_argument("work", type=pathlib.Path)
        if name != "report":
            child.add_argument("--cells", default=None)
        if name in ("build", "run"):
            child.add_argument("--trials", type=int, default=None)
        if name == "build":
            child.add_argument(
                "--matrix",
                type=pathlib.Path,
                default=None,
                help="the experiment's matrix (.toml or .json)",
            )

    args = parser.parse_args(argv)
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)

    if args.command == "build":
        matrix = (
            cells_module.Matrix.load(args.matrix.resolve())
            if args.matrix is not None
            else cells_module.DEFAULT_MATRIX
        )
        return do_build(
            work, matrix, args.trials or matrix.trials, args.cells
        )
    if args.command == "run":
        return do_run(work, args.cells, args.trials)
    if args.command == "verify-assumptions":
        return do_verify_assumptions(work, args.cells)
    return do_report(work)


if __name__ == "__main__":
    raise SystemExit(main())
