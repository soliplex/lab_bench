"""Score every cell that has results."""

from __future__ import annotations

import pathlib

from soliplex_lab_harness import records
from soliplex_lab_harness import scoring

from . import cells as cells_module


def checks(expected: str) -> list[scoring.Check]:
    return [
        scoring.succeeded(),
        scoring.response_contains(expected),
        scoring.invented_tool_name(cells_module.ROOM_TOOLS),
        scoring.invalid_argument(
            "environment_name", cells_module.SANDBOX_ENVIRONMENTS
        ),
        scoring.called_tool("load_capability"),
    ]


def report(work: pathlib.Path, expected: str) -> str:
    active = checks(expected)
    tallies = []
    shapes: dict[str, dict[str, int]] = {}
    for cell in cells_module.cells():
        path = work / "results" / f"{cell.name}.jsonl"
        if not path.exists():
            continue
        trials = records.read(path)
        tallies.append(scoring.tally(cell.name, trials, active))
        found = scoring.bad_name_shapes(trials, cells_module.ROOM_TOOLS)
        if found:
            shapes[cell.name] = found

    if not tallies:
        return "no results yet"

    lines = [scoring.render(tallies, active)]
    lines.append("")
    if shapes:
        lines.append("Invented tool names, by shape:")
        for name, found in shapes.items():
            lines.append(f"  {name}: {found}")
    else:
        lines.append("Invented tool names: none")
    return "\n".join(lines)
