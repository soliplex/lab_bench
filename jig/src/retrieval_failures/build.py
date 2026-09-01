"""Materialize an environment and a cell directory for each cell.

A cell directory is self-contained and disposable. Code-axis
environments are shared by the cells that use them, and are built by
'soliplex_lab_harness.environs' -- this file should not reimplement venv
creation, pin resolution, overlays, or RECORD verification.

Verify what you can here, on the principle of make-the-thing-then-verify-
the-thing: a check that needs only the built environment belongs beside
the code that built it, where it cannot be skipped. Checks that need a
recorded turn belong in 'verify_assumptions'.
"""

from __future__ import annotations

import pathlib
import tomllib

from soliplex_lab_harness import environs

from . import cells as cells_module

PYTHON = "3.13"


class HarnessPinMissing(Exception):
    """The jig declares no harness dependency to give a cell."""

    def __init__(self, path: pathlib.Path):
        self.path = path
        super().__init__(
            f"{path} declares no 'soliplex-lab-harness' dependency; a cell "
            "environment needs the same harness the jig itself was built "
            "against, because a cell records and scores in process."
        )


def harness_pin() -> str:
    """The harness requirement to install into every cell environment.

    Read from 'pyproject.toml' rather than restated here: two copies of a
    pin drift, and a cell built against a different harness than the jig
    imports is the kind of difference that does not announce itself.
    """
    path = cells_module.jig_root() / "pyproject.toml"
    declared = tomllib.loads(path.read_text(encoding="utf-8"))
    for requirement in declared["project"]["dependencies"]:
        if requirement.split(maxsplit=1)[0] == "soliplex-lab-harness":
            return requirement
    raise HarnessPinMissing(path)


def build_environment(
    pin: environs.Pin,
    root: pathlib.Path,
    runner: environs.Runner = environs.run,
) -> environs.Environment:
    """One virtualenv for one code-axis value.

    The harness does the work. What this adds is the check that must not
    be skipped: 'verify_install' raises unless the install still matches
    its own RECORD, except where an overlay says otherwise -- so an arm
    cannot quietly be the wrong arm.
    """
    environment = environs.build(
        pin,
        root,
        extra_requirements=(harness_pin(),),
        python=PYTHON,
        recreate=True,
        runner=runner,
    )
    environs.verify_install(environment)
    return environment


def build_cell(cell: cells_module.Cell, work: pathlib.Path) -> pathlib.Path:
    """Materialize one cell, and write the spec that drives it.

    The spec should carry the interpreter to drive this cell with --
    'environs.Environment.python' -- so nothing downstream has to rebuild
    that path or know what the code axis is called.
    """
    raise NotImplementedError
