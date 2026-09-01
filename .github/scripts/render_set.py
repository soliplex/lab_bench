"""Render an issue filed from the set-proposal form into 'SET.md'.

The file is the set's charter: what phenomenon it exists to measure, why
it needs apparatus of its own, and what it would cost, committed to a
branch that cannot be deleted or force-pushed. The same argument in the
tracker can be edited silently afterwards, so the issue is the index and
the place to discuss; the file is the record.

Nothing here is generated afterwards. Scope decisions are appended by
hand under 'Amendments', dated, with earlier entries left standing so a
superseded reading stays visible.

The same shape as 'render_experiment', deliberately: a reader who knows
one file knows the other.
"""

from __future__ import annotations

import datetime
import sys

import issue_form

# heading in the form -> heading in the file. Order is the file's order.
SECTIONS = (
    ("The phenomenon", "The phenomenon"),
    ("Why it deserves apparatus of its own",
     "Why it deserves apparatus of its own"),
    ("What it would cost", "What it would cost"),
    ("Preconditions, before any trials", "Preconditions, before any trials"),
    ("Publishability", "Publishability"),
    ("Notes", "Notes"),
)

#: Every field the form marks required. 'Notes' is not one.
REQUIRED = tuple(
    label for label, _ in SECTIONS if label != "Notes"
)

SET_NAME = "Set name"
PACKAGE = "Jig package name"


def render(
    body: str,
    issue: str,
    name: str,
    package: str,
    today: str | None = None,
) -> str:
    """The initial 'SET.md' for a proposal filed from the form."""
    for label in REQUIRED:
        issue_form.value(body, label)          # raises FieldMissing

    stamped = today or datetime.date.today().isoformat()

    out = [
        f"# set/{name}",
        "",
        f"Proposed on #{issue}, accepted {stamped}. **This file is the "
        "record.**",
        "",
        "The issue stays the set's hub and the place to discuss. This file "
        "is on a branch that cannot be deleted or force-pushed, which is "
        "what makes it the record rather than a claim about one.",
        "",
        f"- set branch: `set/{name}`",
        f"- jig package: `{package}`",
    ]
    for label, heading in SECTIONS:
        got = issue_form.optional(body, label)
        if got:
            out += ["", f"## {heading}", "", got]
    out += [
        "",
        "## Amendments",
        "",
        "Appended as they land, each entry dated. Earlier entries are "
        "left standing: a scope that a later decision supersedes is part "
        "of the record, not a mistake to tidy away.",
        "",
        "A change here arrives by pull request, like any other change to "
        "the branch, so the reasoning is reviewed rather than edited in "
        "place.",
        "",
        "<!-- ### YYYY-MM-DD -->",
        "",
    ]
    return "\n".join(out)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(f"usage: {argv[0]} <issue-body-file> <issue-number>",
              file=sys.stderr)
        return 2
    import pathlib

    body = pathlib.Path(argv[1]).read_text(encoding="utf-8")
    name = issue_form.line(body, SET_NAME)
    package = issue_form.line(body, PACKAGE)
    print(render(body, argv[2], name, package), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
