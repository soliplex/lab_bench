"""What this experiment set can vary, and what one experiment does vary.

Declare the axes here, and the values this set can take on each. A
**cell** is one combination of axis values; a **matrix** is one
experiment's choice among them, plus the task and the trial target.

Name a cell for the axes that actually vary in the matrix it came from --
an axis with a single value contributes nothing to a name. When nothing
varies, name everything: a nameless cell is worse than a redundant one.

Nothing here is generic. A different set has different axes, and this is
the file that says so.
"""

from __future__ import annotations

import dataclasses
import hashlib
import pathlib

TASK = "REPLACE ME: the verbatim user prompt this set drives"


def digest(path: pathlib.Path) -> str:
    """Short content hash, for asserting a file is what you think."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


@dataclasses.dataclass(frozen=True, slots=True)
class Cell:
    """One runnable combination of axis values."""

    name: str
    task: str


def jig_root() -> pathlib.Path:
    """The jig directory, found relative to this file."""
    return pathlib.Path(__file__).resolve().parents[2]


def load_cells(work: pathlib.Path) -> list[Cell]:
    """The cells this run covers, read back from the work directory.

    'build' resolves what varies and writes it down; everything else reads
    it back from there, so a run cannot silently disagree with what was
    built.
    """
    raise NotImplementedError
