"""Render 'set-template/' into the scaffold for one new experiment set.

Two substitutions, applied to both file contents and path components:

    __SET_NAME__     the set name, e.g. 'soliplex-room-behavior'
    __PACKAGE__      its Python package, e.g. 'room_behavior'
    __HARNESS_TAG__  the harness release to pin, e.g. 'v0.4'

The first two are fields on the proposal form, and they are two fields and
not one. The existing set is
'soliplex-room-behavior' and its package is 'room_behavior': a hyphen is
illegal in an identifier, and mechanical repair would have produced
'soliplex_room_behavior', which is not what the author chose.

Every template file ends '.tmpl', which is stripped on render. The suffix
is load-bearing rather than cosmetic: it is what keeps 'set-template/'
non-importable and non-buildable, which is the whole argument for a
template being allowed on 'main' at all. It also disambiguates
'installation.yaml.in.tmpl', whose '.in' belongs to the rendered jig.

Used by the set-accepted workflow, and runnable on its own:

    python .github/scripts/render_set_scaffold.py <name> <package> <out> \
        [harness-tag]

The harness tag defaults to the latest release, looked up with 'gh'. Pass
it explicitly to render without a network.
"""

from __future__ import annotations

import keyword
import pathlib
import re
import subprocess
import sys

SUFFIX = ".tmpl"
TEMPLATE = "set-template"
HARNESS = "soliplex/lab_harness"

# The name becomes both a branch segment and a label, so it has to be safe
# as both before either is created.
NAME = re.compile(r"\A[a-z0-9]+(-[a-z0-9]+)*\Z")


class InvalidName(Exception):
    """The set name is not safe as a branch segment and a label."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(
            f"set name {name!r} must be lowercase alphanumeric words "
            "joined by single hyphens; it becomes both the 'set/<name>' "
            "branch and the 'set:<name>' label."
        )


class InvalidPackage(Exception):
    """The package name is not a usable Python identifier."""

    def __init__(self, package: str):
        self.package = package
        super().__init__(
            f"package name {package!r} must be a valid, non-keyword "
            "Python identifier; it becomes 'jig/src/<package>/'."
        )


class HarnessTagUnresolved(Exception):
    """The latest harness release could not be looked up."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(
            f"could not resolve the latest {HARNESS} release ({detail}). "
            "A scaffold must pin a real tag: the branch it lands on cannot "
            "be corrected by a later push."
        )


def latest_harness_tag() -> str:
    """The most recent harness release tag, e.g. 'v0.4'."""
    done = subprocess.run(
        ["gh", "api", f"repos/{HARNESS}/releases/latest", "--jq", ".tag_name"],
        capture_output=True,
        text=True,
    )
    tag = done.stdout.strip()
    if done.returncode != 0 or not tag:
        raise HarnessTagUnresolved(
            done.stderr.strip().splitlines()[-1] if done.stderr.strip()
            else "no tag returned"
        )
    return tag


def check_name(name: str) -> None:
    if not NAME.match(name):
        raise InvalidName(name)


def check_package(package: str) -> None:
    if not package.isidentifier() or keyword.iskeyword(package):
        raise InvalidPackage(package)


def substitute(
    text: str, name: str, package: str, harness: str
) -> str:
    return (
        text.replace("__SET_NAME__", name)
        .replace("__PACKAGE__", package)
        .replace("__HARNESS_TAG__", harness)
    )


def render(
    template: pathlib.Path,
    name: str,
    package: str,
    harness: str,
) -> dict[str, str]:
    """Map rendered path -> rendered content. Paths are jig-relative."""
    check_name(name)
    check_package(package)

    out: dict[str, str] = {}
    for source in sorted(template.rglob("*" + SUFFIX)):
        if not source.is_file():
            continue
        relative = source.relative_to(template)
        rendered = substitute(str(relative), name, package, harness)
        out[rendered[: -len(SUFFIX)]] = substitute(
            source.read_text(encoding="utf-8"), name, package, harness
        )
    return out


def main(argv: list[str]) -> int:
    if len(argv) not in (4, 5):
        print(
            f"usage: {argv[0]} <set-name> <package> <destination> "
            "[harness-tag]",
            file=sys.stderr,
        )
        return 2
    name, package, destination = argv[1], argv[2], pathlib.Path(argv[3])
    harness = argv[4] if len(argv) == 5 else latest_harness_tag()
    template = pathlib.Path(__file__).resolve().parents[2] / TEMPLATE
    for relative, content in render(
        template, name, package, harness
    ).items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(relative)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
