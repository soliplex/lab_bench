"""Drive the experiment set.

    python -m room_behavior build   <work> [--trials N]
    python -m room_behavior run     <work> [--cells a,b]
    python -m room_behavior verify  <work> [--cells a,b]
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
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

from . import build as build_module
from . import cells as cells_module
from . import report as report_module
from . import verify as verify_module
from .fixture import write_fixture


def selected(names: str | None) -> list[cells_module.Cell]:
    if not names:
        return cells_module.cells()
    wanted = [n.strip() for n in names.split(",") if n.strip()]
    return [cells_module.by_name(name) for name in wanted]


def do_build(work: pathlib.Path, trials: int, names: str | None) -> int:
    chosen = selected(names)
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
    return 0


def do_run(
    work: pathlib.Path, names: str | None, trials: int | None
) -> int:
    failures = 0
    for cell in selected(names):
        spec = work / "cells" / cell.name / "spec.json"
        if not spec.exists():
            print(f"skipping {cell.name}: not built", file=sys.stderr)
            failures += 1
            continue
        python = work / "envs" / cell.arm.name / "bin" / "python"
        script = pathlib.Path(build_module.__file__).with_name("run.py")
        print(f"=== {cell.name} ===", flush=True)
        argv = [str(python), str(script), str(spec)]
        if trials is not None:
            argv.append(str(trials))
        completed = subprocess.run(  # noqa: S603 -- argv is built
            argv, check=False
        )
        failures += completed.returncode != 0
    return 1 if failures else 0


def do_verify(work: pathlib.Path, names: str | None) -> int:
    checks = verify_module.verify(work, selected(names))
    for check in checks:
        print(check)
    failed = [check for check in checks if not check.ok]
    if failed:
        print(f"\n{len(failed)} precondition(s) failed", flush=True)
        return 1
    print(f"\nall {len(checks)} preconditions hold", flush=True)
    return 0


def do_report(work: pathlib.Path) -> int:
    expected = write_fixture(work / "expected")
    print(report_module.report(work, expected))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="room_behavior")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("build", "run", "verify", "report"):
        child = sub.add_parser(name)
        child.add_argument("work", type=pathlib.Path)
        if name != "report":
            child.add_argument("--cells", default=None)
        if name in ("build", "run"):
            child.add_argument("--trials", type=int, default=None)

    args = parser.parse_args(argv)
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)

    if args.command == "build":
        return do_build(work, args.trials or 20, args.cells)
    if args.command == "run":
        return do_run(work, args.cells, args.trials)
    if args.command == "verify":
        return do_verify(work, args.cells)
    return do_report(work)


if __name__ == "__main__":
    raise SystemExit(main())
