"""Read the set name and package out of a rendered set-proposal issue.

GitHub renders an issue form as markdown: each field becomes a '### '
heading carrying the field's *label*, followed by its value. There is no
machine-readable copy, so the labels are the contract -- change one in
'set-proposal.yml' and this must change with it.

Kept separate from rendering so both can be tested without a forge.
"""

from __future__ import annotations

import json
import pathlib
import sys

SET_NAME = "Set name"
PACKAGE = "Jig package name"


class FieldMissing(Exception):
    """The issue body carries no value for a required field."""

    def __init__(self, label: str):
        self.label = label
        super().__init__(
            f"the issue body has no '### {label}' section with a value; "
            "it was probably not filed from the set-proposal form."
        )


def sections(body: str) -> dict[str, str]:
    """Map heading -> first non-empty line beneath it."""
    found: dict[str, str] = {}
    heading: str | None = None
    for raw in body.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if line.startswith("### "):
            heading = line[4:].strip()
        elif heading and line and heading not in found:
            found[heading] = line
    return found


def field(body: str, label: str) -> str:
    value = sections(body).get(label, "")
    # GitHub writes '_No response_' for an empty optional field.
    if not value or value == "_No response_":
        raise FieldMissing(label)
    return value


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <issue-body-file>", file=sys.stderr)
        return 2
    body = pathlib.Path(argv[1]).read_text(encoding="utf-8")
    print(
        json.dumps(
            {
                "name": field(body, SET_NAME),
                "package": field(body, PACKAGE),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
