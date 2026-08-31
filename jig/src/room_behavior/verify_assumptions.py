"""Assert what only a recorded turn can establish.

Every defect found in this jig so far was silent: the run completed and the
table looked plausible. So these are assertions, not notes.

**Nothing here drives a turn.** ``verify_smoke_turn`` reads a turn that
``run`` has already recorded.

The checks that need no turn live with whatever they check, on the principle
of make-the-thing-then-verify-the-thing:

* ``build_environment`` compares each code-axis install against its own
  RECORD (``environs.verify_install``)
* ``build_sandbox_environments`` checks each sandbox environment can import
  what it declares

Both raise during ``build``, so they cannot be skipped and cannot be
mistaken for a measurement failure.
"""

from __future__ import annotations

import pathlib

from soliplex_lab_harness import preconditions
from soliplex_lab_harness import records

from . import cells as cells_module


def verify_smoke_turn(
    cell: cells_module.Cell, work: pathlib.Path
) -> list[preconditions.Result]:
    """What only a turn can establish, read from the kept smoke result."""
    path = work / "results" / f"{cell.name}.jsonl"
    if not path.exists():
        return [
            preconditions.Result(
                cell.name,
                "smoke turn recorded",
                False,
                "no results; run with --trials 1 first",
            )
        ]
    trials = records.read(path)
    if not trials:
        return [
            preconditions.Result(
                cell.name, "smoke turn recorded", False, "empty results"
            )
        ]

    first = trials[0]
    out = [
        preconditions.Result(
            cell.name,
            "room config loads and a turn completes",
            first.ok,
            (first.error or "")[:120],
        )
    ]

    expected = cell.arm.expects_deferral
    if expected is None:
        # Nothing to assert: on this arm loading a deferred capability is
        # the model's choice, not the arm's policy.
        return out

    loaded = any(
        "load_capability" in trial.call_names for trial in trials
    )
    out.append(
        preconditions.Result(
            cell.name,
            f"deferral engages (expected: {expected})",
            loaded == expected,
            f"load_capability seen: {loaded}",
        )
    )
    return out


def verify_all(
    work: pathlib.Path, chosen
) -> list[preconditions.Result]:
    results: list[preconditions.Result] = []
    for cell in chosen:
        results.extend(verify_smoke_turn(cell, work))
    return results
