"""Assert the assumptions a run depends on, before spending the full N.

Every defect found in this jig so far was silent: the run completed and the
table looked plausible. So these are assertions, not notes.

**Nothing in this module drives a turn.** ``verify_smoke_turn`` reads a turn
that ``run`` has already recorded.

Where the checks actually live:

* ``build`` calls ``environs.verify_install`` on each code-axis environment
  as it creates it -- the RECORD comparison. It needs no turn, and living
  there means it cannot be skipped.
* this module holds the two the ``verify`` subcommand runs:
  ``verify_sandbox_imports``, which also needs no turn, and
  ``verify_smoke_turn``, which does need one to have been recorded.

So the split between the two homes is not "needs a turn" -- it is whether
the check can run before any cell exists. ``verify_sandbox_imports`` needs a
built cell, which ``build`` only finishes at its very end.
"""

from __future__ import annotations

import dataclasses
import pathlib

from soliplex_lab_harness import records

from . import cells as cells_module


class PreconditionFailed(Exception):
    """A run would have measured something other than it claims."""

    def __init__(self, failures: list[str]):
        self.failures = failures
        body = "\n".join(f"  - {failure}" for failure in failures)
        super().__init__(f"{len(failures)} precondition(s) failed:\n{body}")


@dataclasses.dataclass(frozen=True, slots=True)
class Check:
    cell: str
    what: str
    ok: bool
    detail: str = ""

    def __str__(self) -> str:
        mark = "ok  " if self.ok else "FAIL"
        tail = f" -- {self.detail}" if self.detail else ""
        return f"  {mark} {self.cell}: {self.what}{tail}"


def verify_sandbox_imports(
    cell: cells_module.Cell, work: pathlib.Path, runner
) -> list[Check]:
    """Each sandbox environment must import what it declares.

    Uses ``uv --directory``, so a *resolution* failure is caught and not
    just a missing module -- which is how a project named after its own
    dependency presents.
    """
    out = []
    root = work / "cells" / cell.name / "environments"
    for name, module in sorted(cells_module.SANDBOX_IMPORTS.items()):
        directory = root / name
        try:
            runner(
                [
                    "uv",
                    "--directory",
                    str(directory),
                    "run",
                    "python",
                    "-c",
                    f"import {module}",
                ],
                None,
            )
        except Exception as exc:  # noqa: BLE001 -- reported, not handled
            out.append(
                Check(
                    cell.name,
                    f"sandbox {name!r} imports {module!r}",
                    False,
                    str(exc).splitlines()[0][:120],
                )
            )
        else:
            out.append(
                Check(
                    cell.name, f"sandbox {name!r} imports {module!r}", True
                )
            )
    return out


def verify_smoke_turn(
    cell: cells_module.Cell, work: pathlib.Path
) -> list[Check]:
    """What only a turn can establish, read from the kept smoke result."""
    path = work / "results" / f"{cell.name}.jsonl"
    if not path.exists():
        return [
            Check(
                cell.name,
                "smoke turn recorded",
                False,
                "no results; run with --trials 1 first",
            )
        ]
    trials = records.read(path)
    if not trials:
        return [
            Check(cell.name, "smoke turn recorded", False, "empty results")
        ]

    first = trials[0]
    out = [
        Check(
            cell.name,
            "room config loads and a turn completes",
            first.ok,
            (first.error or "")[:120],
        )
    ]

    loaded = any(
        "load_capability" in trial.call_names for trial in trials
    )
    expected = cell.arm.expects_deferral
    out.append(
        Check(
            cell.name,
            f"deferral engages (expected: {expected})",
            loaded == expected,
            f"load_capability seen: {loaded}",
        )
    )
    return out


def verify(work: pathlib.Path, chosen, runner) -> list[Check]:
    checks: list[Check] = []
    for cell in chosen:
        checks.extend(verify_sandbox_imports(cell, work, runner))
        checks.extend(verify_smoke_turn(cell, work))
    return checks


def assert_ok(checks: list[Check]) -> None:
    failures = [
        f"{check.cell}: {check.what}"
        + (f" -- {check.detail}" if check.detail else "")
        for check in checks
        if not check.ok
    ]
    if failures:
        raise PreconditionFailed(failures)
