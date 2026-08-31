"""Drive the experiment set.

    build              <work>              materialize environments and cells
    run                <work> --trials N   drive trials, topping up to N
    verify-assumptions <work>              assert the preconditions
    report             <work>              score what has been recorded

The intended order spends no turn twice:

    build <work>
    run   <work> --trials 1        one smoke turn
    verify-assumptions <work>      before spending the rest
    run   <work> --trials 20       tops up; the smoke turn counts
    report <work>

**'build' takes the matrix; everything else reads it back** from the work
directory, so a run cannot silently disagree with what was built.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

from soliplex_lab_harness import preconditions

from . import cells as cells_module
from . import report as report_module
from . import verify_assumptions
from .fixture import write_fixture


def do_report(work: pathlib.Path) -> int:
    chosen = cells_module.load_cells(work)
    # The scorer checks for the value the generator says it produced, so
    # the fixture and the expectation cannot drift apart.
    expected = write_fixture(work / "expected")
    print(report_module.report(work, chosen, expected))
    return 0


def do_verify_assumptions(work: pathlib.Path) -> int:
    chosen = cells_module.load_cells(work)
    results = verify_assumptions.verify_all(work, chosen)
    print(preconditions.render(results), flush=True)
    try:
        preconditions.assert_ok(results)
    except preconditions.Failed:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="retrieval_failures")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "run", "verify-assumptions", "report"):
        child = sub.add_parser(name)
        child.add_argument("work", type=pathlib.Path)
        if name in ("build", "run"):
            child.add_argument("--trials", type=int, default=None)
    args = parser.parse_args(argv)
    args.work.mkdir(parents=True, exist_ok=True)

    if args.command == "verify-assumptions":
        return do_verify_assumptions(args.work)
    if args.command == "report":
        return do_report(args.work)
    raise NotImplementedError(args.command)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
