"""Create a set's container: its branch, its scaffold, and its label.

Run by the 'set accepted' workflow.

Refuses loudly rather than creating anything it could not remove. A 'set/'
branch cannot be deleted without disabling the ruleset, so every
precondition is checked before the ref is created, and nothing about the
issue is touched until the ref exists. A failure visible only in the
Actions tab would be a guardrail that reads as present and is not, so a
refusal comments on the issue saying which precondition failed.

**The proposal becomes the set's tracking issue.** It already holds the
scope, the cost, and the preconditions, which is exactly what
'set:<name>' is for; opening a second issue would put the reasoning
outside its own set's label query and leave two things to keep in step.
So acceptance adds 'set:<name>' here and drops 'status:proposed'.

**Nothing this workflow adds is ever read by a check.** 'status:accepted'
is already present -- a person added it, and that is the trigger -- and
'status:proposed' is never added back. Restoring it on refusal would be a
no-op when the issue had it and would *grant* it when the issue did not,
handing out the very credential the first check tests for. Probed; see
soliplex/lab_bench#23.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import parse_set_proposal  # noqa: E402
import render_set_scaffold  # noqa: E402

PROPOSED = "status:proposed"
ACCEPTED = "status:accepted"


class Refused(Exception):
    """A precondition failed, so nothing was created."""


def api(path: str, payload: object = None, method: str = "GET") -> object:
    argv = ["gh", "api", "-X", method, path]
    text = None
    if payload is not None:
        argv += ["--input", "-"]
        text = json.dumps(payload)
    done = subprocess.run(
        argv, input=text, capture_output=True, text=True, check=True
    )
    return json.loads(done.stdout) if done.stdout.strip() else None


def add_label(repo: str, issue: str, label: str) -> None:
    """Put one label on an issue. Never used for a label a check reads."""
    api(
        f"repos/{repo}/issues/{issue}/labels",
        {"labels": [label]},
        method="POST",
    )


def remove_label(repo: str, issue: str, label: str) -> None:
    """Drop one label. Absent is success, so this is safe to repeat."""
    subprocess.run(
        ["gh", "api", "-X", "DELETE",
         f"repos/{repo}/issues/{issue}/labels/{label}"],
        capture_output=True,
    )


def exists(path: str) -> bool:
    done = subprocess.run(
        ["gh", "api", path], capture_output=True, text=True
    )
    return done.returncode == 0


def check(repo: str, issue: str, name: str, package: str) -> str:
    """Validate everything, and return the harness tag to pin."""
    labels = {item["name"] for item in api(f"repos/{repo}/issues/{issue}/labels")}
    if PROPOSED not in labels:
        raise Refused(
            f"this issue does not carry `{PROPOSED}`, so it was never a "
            "proposal awaiting acceptance. Add it deliberately if this "
            "really is one."
        )
    try:
        render_set_scaffold.check_name(name)
        render_set_scaffold.check_package(package)
    except (
        render_set_scaffold.InvalidName,
        render_set_scaffold.InvalidPackage,
    ) as exc:
        raise Refused(str(exc)) from exc
    if exists(f"repos/{repo}/git/ref/heads/set/{name}"):
        raise Refused(
            f"`set/{name}` already exists, and cannot be replaced: the "
            "ruleset forbids deletion and non-fast-forward."
        )
    if exists(f"repos/{repo}/labels/set:{name}"):
        raise Refused(f"label `set:{name}` already exists.")
    # Resolved here rather than mid-flight: the scaffold has to pin a real
    # tag, and the branch it lands on cannot be corrected by a later push.
    try:
        return render_set_scaffold.latest_harness_tag()
    except render_set_scaffold.HarnessTagUnresolved as exc:
        raise Refused(str(exc)) from exc


def scaffold_commit(
    repo: str, name: str, package: str, harness: str
) -> str:
    """One commit holding the rendered scaffold, parented on `main`."""
    root = pathlib.Path(__file__).resolve().parents[2]
    rendered = render_set_scaffold.render(
        root / render_set_scaffold.TEMPLATE, name, package, harness
    )
    base = api(f"repos/{repo}/git/ref/heads/main")["object"]["sha"]
    base_tree = api(f"repos/{repo}/git/commits/{base}")["tree"]["sha"]

    entries = []
    for relative, content in sorted(rendered.items()):
        blob = api(
            f"repos/{repo}/git/blobs",
            {"content": content, "encoding": "utf-8"},
            method="POST",
        )["sha"]
        entries.append(
            {
                "path": relative,
                "mode": "100644",
                "type": "blob",
                "sha": blob,
            }
        )
    tree = api(
        f"repos/{repo}/git/trees",
        {"base_tree": base_tree, "tree": entries},
        method="POST",
    )["sha"]
    return api(
        f"repos/{repo}/git/commits",
        {
            "message": (
                f"set:{name}: scaffold\n\n"
                f"Created on acceptance of #{os.environ['ISSUE']}. The jig "
                "arrives by pull request from "
                f"jig/{name}/initial; these are placeholders."
            ),
            "tree": tree,
            "parents": [base],
        },
        method="POST",
    )["sha"]


def comment(repo: str, issue: str, body: str) -> None:
    api(
        f"repos/{repo}/issues/{issue}/comments",
        {"body": body},
        method="POST",
    )


def main() -> int:
    repo = os.environ["REPO"]
    issue = os.environ["ISSUE"]
    body = os.environ["BODY"]

    try:
        fields = {
            "name": parse_set_proposal.field(
                body, parse_set_proposal.SET_NAME
            ),
            "package": parse_set_proposal.field(
                body, parse_set_proposal.PACKAGE
            ),
        }
        name, package = fields["name"], fields["package"]
        harness = check(repo, issue, name, package)
    except (Refused, parse_set_proposal.FieldMissing) as exc:
        comment(
            repo,
            issue,
            f"**Not accepted.** {exc}\n\nNothing was created, and "
            f"`{ACCEPTED}` has been removed. Fix the above and add it "
            "again.",
        )
        remove_label(repo, issue, ACCEPTED)
        print(f"refused: {exc}", file=sys.stderr)
        return 1

    # Irreversible from here. Nothing about the issue is touched until the
    # ref is confirmed, so a failure in between destroys nothing.
    commit = scaffold_commit(repo, name, package, harness)
    api(
        f"repos/{repo}/git/refs",
        {"ref": f"refs/heads/set/{name}", "sha": commit},
        method="POST",
    )

    api(
        f"repos/{repo}/labels",
        {
            "name": f"set:{name}",
            "color": "5319e7",
            "description": f"The {name} set itself -- its scope, its retirement",
        },
        method="POST",
    )
    # This issue is now the set's, so it carries the set's label and stops
    # being a pending proposal.
    add_label(repo, issue, f"set:{name}")
    remove_label(repo, issue, PROPOSED)
    comment(
        repo,
        issue,
        f"**Accepted.** Created `set/{name}`, scaffolded at "
        f"`{commit[:8]}`, and the `set:{name}` label.\n\n"
        "This issue is now the set's: its scope, and eventually its "
        "retirement.\n\n"
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
