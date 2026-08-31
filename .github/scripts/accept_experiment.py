"""Create an experiment's branch, holding its 'EXPERIMENT.md'.

Run by the 'experiment accepted' workflow.

An 'exp/' branch cannot be deleted or force-pushed either, so this follows
the same order as the set acceptance: check everything, create the ref,
and only then touch the issue. A failure before the ref exists leaves
nothing behind.

Unlike 'set/', the 'exp/*' ruleset carries no 'pull_request' rule, so a
follow-up push would be allowed. The branch is still born pointing at its
commit: two acceptances of the same shape are worth more than using a
permission this one does not need. Findings are appended to the file
afterwards, by hand, which is the praxis and not a workflow's business.
"""

from __future__ import annotations

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import forge  # noqa: E402
import issue_form  # noqa: E402
import render_experiment as renderer  # noqa: E402

ROUTING = "proposal:exp"


def check(
    repo: str, issue: str, labels: set[str], body: str
) -> tuple[str, str]:
    """Validate everything. Returns (exp_branch, set_branch)."""
    forge.require_proposed(labels)
    try:
        exp_branch = issue_form.line(body, renderer.EXP_BRANCH)
        set_branch = issue_form.line(body, renderer.SET_BRANCH)
        renderer.check_branches(exp_branch, set_branch)
    except (
        issue_form.FieldMissing,
        renderer.InvalidExpBranch,
        renderer.SetMismatch,
    ) as exc:
        raise forge.Refused(str(exc)) from exc

    if not forge.exists(f"repos/{repo}/git/ref/heads/{set_branch}"):
        raise forge.Refused(
            f"`{set_branch}` does not exist. An experiment branches from "
            "its set, so the set has to be there first."
        )
    if forge.exists(f"repos/{repo}/git/ref/heads/{exp_branch}"):
        raise forge.Refused(
            f"`{exp_branch}` already exists, and cannot be replaced: the "
            "ruleset forbids deletion and non-fast-forward."
        )
    return exp_branch, set_branch


def main() -> int:
    repo = os.environ["REPO"]
    issue = os.environ["ISSUE"]
    body = os.environ["BODY"]

    labels = forge.labels_on(repo, issue)
    if forge.not_mine(labels, ROUTING, "experiment"):
        return 0

    try:
        exp_branch, set_branch = check(repo, issue, labels, body)
        # Rendering can still refuse, on a required field left empty. It
        # happens here, before anything irreversible.
        document = renderer.render(body, issue)
    except (forge.Refused, issue_form.FieldMissing) as exc:
        return forge.refuse(repo, issue, exc)

    # Irreversible from here. The branch parents on its *set* branch, not
    # on main: an experiment starts from the jig it will run.
    commit = forge.commit_files(
        repo,
        f"heads/{set_branch}",
        {"EXPERIMENT.md": document},
        f"exp: pre-register {exp_branch}\n\n"
        f"Rendered from #{issue} on acceptance. Findings are appended to "
        "this file as they land.",
    )
    forge.create_ref(repo, f"refs/heads/{exp_branch}", commit)

    # The set's labels normally exist already, minted when the set was
    # created; a set older than that machinery may be missing them.
    set_name = renderer.set_of(exp_branch)
    forge.ensure_set_labels(repo, set_name)
    forge.add_label(repo, issue, f"exp:{set_name}")
    forge.remove_label(repo, issue, forge.PROPOSED)
    forge.remove_label(repo, issue, ROUTING)
    forge.comment(
        repo,
        issue,
        f"**Accepted.** Created `{exp_branch}` at `{commit[:8]}`, holding "
        f"`EXPERIMENT.md` rendered from this issue, and labelled "
        f"`exp:{set_name}`.\n\n"
        "**That file is the record from here.** Findings are appended "
        "there, dated, as they land -- not to this issue. What is written "
        "above was written before the run, on a branch that cannot be "
        "force-pushed, which is what makes it evidence.\n\n"
        "```\n"
        f"git worktree add ../{exp_branch.replace('/', '-')} {exp_branch}\n"
        "```",
    )
    print(f"created {exp_branch} at {commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
