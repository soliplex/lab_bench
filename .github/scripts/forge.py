"""The forge calls an acceptance workflow makes, and how it refuses.

Shared by the set and experiment acceptances. Both create something that
**cannot be deleted afterwards**, so both follow the same order: check
everything, create the ref, and only then touch the issue. A failure
before the ref exists must leave nothing behind.
"""

from __future__ import annotations

import json
import subprocess
import sys

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


def exists(path: str) -> bool:
    """Whether a GET on this path succeeds. For 'does X already exist'."""
    done = subprocess.run(
        ["gh", "api", path], capture_output=True, text=True
    )
    return done.returncode == 0


def labels_on(repo: str, issue: str) -> set[str]:
    return {
        item["name"] for item in api(f"repos/{repo}/issues/{issue}/labels")
    }


def add_label(repo: str, issue: str, label: str) -> None:
    """Put one label on an issue.

    Never used for a label a check reads. Adding 'status:proposed' on
    refusal would grant the credential the first check tests for, and the
    next attempt would sail through -- probed, on soliplex/lab_bench#23.
    """
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


# The labels a set needs, mirroring the branch kinds PRAXIS.md names.
# Minted together when the set is created: leaving 'exp:' and 'jig:' to be
# hand-made later is the papercut that motivated automating any of this.
SET_LABELS = (
    ("set:{name}", "5319e7",
     "The {name} set itself, and its scope"),
    ("jig:{name}", "0e8a16",
     "Work on the {name} jig (branch prefix jig/{name}/)"),
    # Dark purple, not red: red reads as danger, and an experiment is
    # ordinary work. It sits beside 'set:' in the same family.
    ("exp:{name}", "4a148c",
     "One experiment in the {name} set (branch prefix exp/{name}/)"),
)


def ensure_label(repo: str, name: str, color: str, description: str) -> None:
    """Create a repository label unless it is already there."""
    if exists(f"repos/{repo}/labels/{name}"):
        return
    api(
        f"repos/{repo}/labels",
        {"name": name, "color": color, "description": description},
        method="POST",
    )


def ensure_set_labels(repo: str, name: str) -> list[str]:
    """Mint every label a set needs. Returns their names."""
    minted = []
    for pattern, color, description in SET_LABELS:
        label = pattern.format(name=name)
        ensure_label(repo, label, color, description.format(name=name))
        minted.append(label)
    return minted


HUB_START = "<!-- set-hub -->"
HUB_END = "<!-- /set-hub -->"


def prepend_block(repo: str, issue: str, block: str) -> None:
    """Put 'block' at the very top of an issue body.

    Above the first heading rather than after the text: a proposal argues
    scope, cost and preconditions, so it tends toward a wall of text, and
    anything appended is below the fold exactly when the set is
    substantial enough to want an index.

    Delimited by markers so a second run replaces its own block instead of
    prepending twice. Nothing else is touched -- the proposal's prose
    belongs to whoever filed it.
    """
    body = api(f"repos/{repo}/issues/{issue}")["body"] or ""
    if HUB_START in body and HUB_END in body:
        head, _, rest = body.partition(HUB_START)
        _, _, tail = rest.partition(HUB_END)
        body = (head + tail).lstrip("\n")
    api(
        f"repos/{repo}/issues/{issue}",
        {"body": f"{HUB_START}\n{block}\n{HUB_END}\n\n{body}"},
        method="PATCH",
    )


def comment(repo: str, issue: str, body: str) -> None:
    api(
        f"repos/{repo}/issues/{issue}/comments",
        {"body": body},
        method="POST",
    )


def refuse(repo: str, issue: str, why: object) -> int:
    """Say why on the issue, drop the trigger, and add nothing."""
    comment(
        repo,
        issue,
        f"**Not accepted.** {why}\n\nNothing was created, and "
        f"`{ACCEPTED}` has been removed. Fix the above and add it again.",
    )
    remove_label(repo, issue, ACCEPTED)
    return 1


def require_proposed(labels: set[str]) -> None:
    if PROPOSED not in labels:
        raise Refused(
            f"this issue does not carry `{PROPOSED}`, so it was never a "
            "proposal awaiting acceptance. Add it deliberately if this "
            "really is one."
        )


def commit_files(
    repo: str, base_ref: str, files: dict[str, str], message: str
) -> str:
    """One commit holding 'files', parented on 'base_ref'. Returns its sha."""
    base = api(f"repos/{repo}/git/ref/{base_ref}")["object"]["sha"]
    base_tree = api(f"repos/{repo}/git/commits/{base}")["tree"]["sha"]
    entries = []
    for path, content in sorted(files.items()):
        blob = api(
            f"repos/{repo}/git/blobs",
            {"content": content, "encoding": "utf-8"},
            method="POST",
        )["sha"]
        entries.append(
            {"path": path, "mode": "100644", "type": "blob", "sha": blob}
        )
    tree = api(
        f"repos/{repo}/git/trees",
        {"base_tree": base_tree, "tree": entries},
        method="POST",
    )["sha"]
    return api(
        f"repos/{repo}/git/commits",
        {"message": message, "tree": tree, "parents": [base]},
        method="POST",
    )["sha"]


def create_ref(repo: str, ref: str, sha: str) -> None:
    """Create a branch already pointing at 'sha'. Irreversible."""
    api(
        f"repos/{repo}/git/refs",
        {"ref": ref, "sha": sha},
        method="POST",
    )

def not_mine(labels: set[str], routing: str, kind: str) -> bool:
    """Whether this issue is some other kind of proposal.

    Routing is by label rather than by anything in the body: the issue
    template applies it, so it survives a collaborator reformatting the
    prose while editing a proposal.

    The workflow guards on the same label, so reaching this means the
    guard and the script disagree. Exit quietly rather than refusing: a
    refusal comments and strips 'status:accepted', which would sabotage
    whichever acceptance the issue really belongs to.
    """
    if routing in labels:
        return False
    print(f"not a {kind} proposal; leaving it alone", file=sys.stderr)
    return True
