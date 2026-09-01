"""Create a set's container: its branch, its scaffold, and its label.

Run by the 'set accepted' workflow.

Refuses loudly rather than creating anything it could not remove. A 'set/'
branch cannot be deleted without disabling the ruleset, so every
precondition is checked before the ref is created, and nothing about the
issue is touched until the ref exists.

**The proposal becomes the set's tracking issue**, and its fields are
rendered into 'SET.md' on the set's branch. The issue is the hub and the
place to discuss; the file is the record, because a branch that cannot be
force-pushed keeps what was argued and a tracker does not. Opening a
second issue would put the discussion outside its own set's label query.

The shared plumbing -- forge calls, refusal, form reading -- is in
'forge' and 'issue_form', and is used by the experiment acceptance too.
"""

from __future__ import annotations

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import forge  # noqa: E402
import issue_form  # noqa: E402
import render_set  # noqa: E402
import render_set_scaffold  # noqa: E402

ROUTING = "proposal:set"
SET_NAME = "Set name"
PACKAGE = "Jig package name"


def hub_line(repo: str, name: str) -> str:
    """The set's branch and its three label indexes, as one line.

    The label links are **bare URLs on purpose**: GitHub renders an
    unadorned label URL as the label chip -- its colour, its description
    as a hover tooltip, and its name taken from the label rather than
    typed, so the text cannot drift from what it names. Wrapping one in
    '[text](url)' suppresses all of that.

    The branch is a markdown link because a bare tree URL gets no such
    treatment; commits, issues and labels do, branches do not.

    A label link lands on open issues, as clicking that label does
    anywhere in GitHub. That hides closed work -- an experiment's issue
    closes when its findings are recorded, and a jig issue when its pull
    request merges -- so the index is what is in flight, not the set's
    whole history. Consistency with every other label in the interface is
    worth more than completeness here, and dropping the filter is one
    click for a reader who wants everything.
    """
    base = f"https://github.com/{repo}"
    return (
        f"[`set/{name}`]({base}/tree/set/{name})"
        f" · {base}/labels/docs%3A{name}"
        f" · {base}/labels/jig%3A{name}"
        f" · {base}/labels/exp%3A{name}"
    )


def check(
    repo: str, issue: str, labels: set[str], name: str, package: str
) -> str:
    """Validate everything, and return the harness tag to pin."""
    forge.require_proposed(labels)
    try:
        render_set_scaffold.check_name(name)
        render_set_scaffold.check_package(package)
    except (
        render_set_scaffold.InvalidName,
        render_set_scaffold.InvalidPackage,
    ) as exc:
        raise forge.Refused(str(exc)) from exc
    if forge.exists(f"repos/{repo}/git/ref/heads/set/{name}"):
        raise forge.Refused(
            f"`set/{name}` already exists, and cannot be replaced: the "
            "ruleset forbids deletion and non-fast-forward."
        )
    # Resolved here rather than mid-flight: the scaffold has to pin a real
    # tag, and the branch it lands on cannot be corrected by a later push.
    try:
        return render_set_scaffold.latest_harness_tag()
    except render_set_scaffold.HarnessTagUnresolved as exc:
        raise forge.Refused(str(exc)) from exc


def main() -> int:
    repo = os.environ["REPO"]
    issue = os.environ["ISSUE"]
    body = os.environ["BODY"]

    labels = forge.labels_on(repo, issue)
    if forge.not_mine(labels, ROUTING, "set"):
        return 0

    try:
        name = issue_form.line(body, SET_NAME)
        package = issue_form.line(body, PACKAGE)
        harness = check(repo, issue, labels, name, package)
        # Rendered before anything irreversible: a proposal missing a
        # required field must be refused, not answered with a branch
        # that cannot be deleted and a charter that is half a file.
        charter = render_set.render(body, issue, name, package)
    except (forge.Refused, issue_form.FieldMissing) as exc:
        return forge.refuse(repo, issue, exc)

    # Irreversible from here.
    root = pathlib.Path(__file__).resolve().parents[2]
    rendered = render_set_scaffold.render(
        root / render_set_scaffold.TEMPLATE, name, package, harness
    )
    rendered["SET.md"] = charter
    commit = forge.commit_files(
        repo,
        "heads/main",
        rendered,
        f"set:{name}: scaffold\n\n"
        f"Created on acceptance of #{issue}. The jig arrives by pull "
        f"request from jig/{name}/initial; these are placeholders.",
    )
    forge.create_ref(repo, f"refs/heads/set/{name}", commit)

    minted = forge.ensure_set_labels(repo, name)
    # This issue is now the set's, so it carries the set's label and stops
    # being a pending proposal.
    forge.add_label(repo, issue, f"set:{name}")
    forge.prepend_block(repo, issue, hub_line(repo, name))
    forge.remove_label(repo, issue, forge.PROPOSED)
    forge.remove_label(repo, issue, ROUTING)
    forge.comment(
        repo,
        issue,
        f"**Accepted.** Created `set/{name}`, scaffolded at "
        f"`{commit[:8]}`, and its labels: "
        + ", ".join(f"`{label}`" for label in minted)
        + ".\n\n"
        "This issue is now the set's hub. Its scope was rendered into "
        "`SET.md` on the branch, which is where scope is recorded from "
        f"here; amend it by pull request from `docs/{name}/<topic>`.\n\n"
        f"- branch: `set/{name}`\n"
        f"- jig package: `{package}`\n"
        f"- harness pinned at `{harness}`, the latest release when this "
        "was scaffolded; bump it deliberately\n\n"
        "The scaffold is placeholders. The jig arrives by pull request "
        f"from `jig/{name}/initial` into `set/{name}`, and is reviewed "
        "there.\n\n"
        "```\n"
        f"git worktree add ../set-{name} set/{name}\n"
        f"git worktree add ../jig-{name}-initial "
        f"-b jig/{name}/initial set/{name}\n"
        "```",
    )
    print(f"created set/{name} at {commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
