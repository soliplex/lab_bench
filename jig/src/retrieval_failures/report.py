"""Score every cell that has results.

Compute nothing here. 'soliplex_lab_harness.scoring' owns rates,
dispersion, and the failure taxonomy, and it owns the habits that go with
them: rates rather than outcomes, N reported beside every rate, and
'None' rather than zero when a trial cannot answer.

What belongs here is the *choice* of checks -- which questions this set
asks of a trial -- and the order the sections are printed in.
"""

from __future__ import annotations

import pathlib

from soliplex_lab_harness import records
from soliplex_lab_harness import scoring

from .fixtures import ExpectedType


def checks(expected: ExpectedType) -> list[scoring.Check]:
    """The questions this set asks of one trial.

    'expected' is whatever 'do_report' got from this set's fixtures.
    Required rather than defaulted: a scorer that silently checks
    against nothing still prints a plausible table.
    """
    return [
        scoring.succeeded(),
        # REPLACE ME: the checks particular to this set. Not
        # 'scoring.response_contains(expected)' -- this set's
        # expectation is per question, and a search returns a ranked
        # list rather than a response to match against.
    ]


def report(work: pathlib.Path, chosen, expected: ExpectedType) -> str:
    active = checks(expected)
    tallies = []
    for cell in chosen:
        path = work / "results" / f"{cell.name}.jsonl"
        if not path.exists():
            continue
        tallies.append(
            scoring.tally(cell.name, records.read(path), active)
        )
    if not tallies:
        return "no results yet"
    return "\n\n".join(
        [
            scoring.render(tallies, active),
            scoring.render_distributions(tallies, "turns"),
        ]
    )
