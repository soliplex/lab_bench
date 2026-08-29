"""Score every cell that has results.

Rates first, then distributions. The set's first experiment
(soliplex/lab_bench#4) found its result in a standard deviation collapsing
from 8.6 to 1.5 while the median barely moved, and had to compute that by
hand; harness v0.3 does it here.

Retries are reported because ``ok`` and ``correct`` sit at the ceiling in a
room that works -- what a run had to recover from on the way is the signal
with room to move. A record written before harness v0.3 cannot answer that
and shows ``-`` rather than a clean sheet.
"""

from __future__ import annotations

import pathlib

from soliplex_lab_harness import records
from soliplex_lab_harness import scoring

from . import cells as cells_module

DISTRIBUTIONS = ("turns", "secs", "retries")


def checks(expected: str) -> list[scoring.Check]:
    return [
        scoring.succeeded(),
        scoring.response_contains(expected),
        scoring.invented_tool_name(cells_module.ROOM_TOOLS),
        scoring.invalid_argument(
            "environment_name", cells_module.SANDBOX_ENVIRONMENTS
        ),
        scoring.called_tool("load_capability"),
        scoring.retried(),
        # A room prompt that re-describes a tool the capability already
        # documents has been measured driving spurious calls; this is the
        # cheapest place that would show up.
        scoring.called_repeatedly("list_environments"),
    ]


def report(
    work: pathlib.Path, matrix: cells_module.Matrix, expected: str
) -> str:
    active = checks(expected)
    tallies = []
    shapes: dict[str, dict[str, int]] = {}
    outcomes: dict[str, dict[str, int]] = {}
    for cell in matrix.cells():
        path = work / "results" / f"{cell.name}.jsonl"
        if not path.exists():
            continue
        trials = records.read(path)
        tallies.append(scoring.tally(cell.name, trials, active))
        found = scoring.bad_name_shapes(trials, cells_module.ROOM_TOOLS)
        if found:
            shapes[cell.name] = found
        seen = scoring.result_shapes(trials)
        if seen:
            outcomes[cell.name] = seen

    if not tallies:
        return "no results yet"

    lines = [scoring.render(tallies, active), ""]
    for field in DISTRIBUTIONS:
        lines.append(scoring.render_distributions(tallies, field))
        lines.append("")

    lines.append("Seconds per turn:")
    for item in tallies:
        value = item.secs_per_turn
        lines.append(f"  {item.cell}: {'-' if value is None else value}")
    lines.append("")

    if shapes:
        lines.append("Invented tool names, by shape:")
        for name, found in shapes.items():
            lines.append(f"  {name}: {found}")
    else:
        lines.append("Invented tool names: none")

    lines.append("")
    if outcomes:
        lines.append("Tool outcomes other than ok:")
        for name, seen in outcomes.items():
            lines.append(f"  {name}: {seen}")
    else:
        lines.append("Tool outcomes other than ok: none recorded")
    return "\n".join(lines)
