"""Render an issue filed from the experiment form into 'EXPERIMENT.md'.

The file is the experiment's whole record: what was going to be measured,
written before the run and committed to a branch that cannot be
force-pushed, then findings appended as they land. That is the point --
the same text in the tracker can be edited silently after results are in,
so it is not evidence of pre-registration; a commit is.

Nothing here is generated afterwards. Findings are appended by hand,
dated, with earlier entries left standing so a superseded reading stays
visible.
"""

from __future__ import annotations

import datetime
import re
import sys

import issue_form

# heading in the form -> heading in the file. Order is the file's order.
SETUP = (
    ("Hypothesis", "Hypothesis"),
    ("Axes and cells", "Axes and cells"),
    ("N per cell", "N per cell"),
    ("Refs under test", "Refs under test"),
    ("Model endpoints and ids", "Model endpoints and ids"),
    ("Fixture", "Fixture"),
    ("Jig / harness version", "Jig and harness"),
    ("Preconditions", "Preconditions, before spending trials"),
    ("Notes", "Notes"),
)
REQUIRED = ("Hypothesis", "Axes and cells", "N per cell")

SET_BRANCH = "Experiment set branch"
EXP_BRANCH = "Experiment branch"
TASK = "Task prompt (verbatim)"

EXP_REF = re.compile(r"\Aexp/([a-z0-9]+(?:-[a-z0-9]+)*)/[a-z0-9-]+\Z")


class InvalidExpBranch(Exception):
    """The experiment branch is not 'exp/<set>/<slug>'."""

    def __init__(self, branch: str):
        self.branch = branch
        super().__init__(
            f"experiment branch {branch!r} must read 'exp/<set>/<slug>', "
            "lowercase words joined by single hyphens in each segment."
        )


class SetMismatch(Exception):
    """The experiment branch names a different set than the set branch."""

    def __init__(self, exp_branch: str, set_branch: str):
        super().__init__(
            f"{exp_branch!r} is not an experiment of {set_branch!r}; its "
            "second segment must be that set's name. An experiment "
            "branches from its set, and this one names another."
        )


def set_of(exp_branch: str) -> str:
    found = EXP_REF.match(exp_branch)
    if not found:
        raise InvalidExpBranch(exp_branch)
    return found.group(1)


def check_branches(exp_branch: str, set_branch: str) -> str:
    """Validate the pair, and return the set name they agree on."""
    name = set_of(exp_branch)
    if set_branch != f"set/{name}":
        raise SetMismatch(exp_branch, set_branch)
    return name


def render(body: str, issue: str, today: str | None = None) -> str:
    """The initial 'EXPERIMENT.md' for an issue filed from the form."""
    for label in REQUIRED:
        issue_form.value(body, label)          # raises FieldMissing

    exp_branch = issue_form.line(body, EXP_BRANCH)
    set_branch = issue_form.line(body, SET_BRANCH)
    check_branches(exp_branch, set_branch)
    stamped = today or datetime.date.today().isoformat()

    out = [
        f"# {exp_branch}",
        "",
        f"Proposed on #{issue}, accepted {stamped}. **This file is the "
        "record.**",
        "",
        "Everything above the findings was written *before* the run. It is "
        "on a branch that cannot be force-pushed, which is what makes it "
        "pre-registration rather than a claim about one.",
        "",
        f"- set branch: `{set_branch}`",
        f"- this branch: `{exp_branch}`",
        "",
        "## Task prompt (verbatim)",
        "",
        "```text",
        issue_form.value(body, TASK),
        "```",
    ]
    for label, heading in SETUP:
        got = issue_form.optional(body, label)
        if got:
            out += ["", f"## {heading}", "", got]
    out += [
        "",
        "## Findings",
        "",
        "Appended as they land, each entry dated. Earlier entries are left "
        "standing: a reading that a later run supersedes is part of the "
        "record, not a mistake to tidy away.",
        "",
        "State N. \"Did not reproduce\" is a finding; it is not \"fixed\", "
        "and it is not \"no effect\".",
        "",
        "<!-- ## YYYY-MM-DD -->",
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
    print(render(body, argv[2]), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
