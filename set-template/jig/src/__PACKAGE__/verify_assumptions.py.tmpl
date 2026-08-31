"""Assert what only a recorded turn can establish.

**This file exists by default because the praxis requires it.** Trials
are not spent until the preconditions the hypothesis depends on have been
printed and confirmed. A cell that structurally cannot exhibit the
behaviour under test yields a null that reads as a real result, and that
has already cost this bench twice.

Nothing here drives a turn: these read what 'run' already recorded. The
plumbing -- the result record, the renderer, the refusal -- lives in
'soliplex_lab_harness.preconditions'. What is worth asserting is
particular to this set, and that is what belongs here.
"""

from __future__ import annotations

import pathlib

from soliplex_lab_harness import preconditions
from soliplex_lab_harness import records

from . import cells as cells_module


def verify_cell(
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
    first = trials[0]
    return [
        preconditions.Result(
            cell.name,
            "a turn completes",
            first.ok,
            (first.error or "")[:120],
        ),
        # REPLACE ME: assert the state this set's hypothesis depends on.
    ]


def verify_all(
    work: pathlib.Path, chosen
) -> list[preconditions.Result]:
    results: list[preconditions.Result] = []
    for cell in chosen:
        results.extend(verify_cell(cell, work))
    return results
