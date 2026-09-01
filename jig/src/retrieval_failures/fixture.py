"""Thin wrapper so the fixture generators have one import site.

The generators under 'fixtures/' are loaded by path, not imported: they
have to be loadable from inside a cell's code-axis environment, where
this package is not installed.

There are two fixtures, and they are not independent. 'corpus' builds
the RAG database; 'questions' names, per question, the documents in that
corpus which state its answer. Scoring a question set against a corpus
it was not generated over reports a clean miss on every trial and reads
like a finding, so 'questions.load' checks the pinned corpus hash and
refuses.

Commit the generators and -- for the questions alone, and deliberately --
their output. See 'fixtures/questions.py' for why that one departs from
the usual rule.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

from . import cells as cells_module


class ReportShapeUndecided(Exception):
    """The scaffold wants one expected string; this set has a set of them.

    'report' scores a cell against a single expected value. That fits a
    set whose task is fixed, and this set's task is a question drawn
    from a fixture -- so what a cell expects depends on which question
    it was built with, which is a decision 'cells.py' has not made yet.

    Raised rather than papered over with the first question's answer,
    which would score every cell against one arbitrary expectation and
    still print a plausible table.
    """

    def __init__(self) -> None:
        super().__init__(
            "write_fixture has no single expected value for this set: "
            "the expectation is per question. Decide in 'cells.py' "
            "whether a question is an axis, then have 'build' put the "
            "chosen question's answer in the cell spec."
        )


def _load(name: str):
    """Load one generator from 'fixtures/' by path.

    Two details here are load-bearing, and both were found by running it:

    * The module goes into 'sys.modules' **before** it executes. A
      'dataclass(slots=True)' is rebuilt during class creation, and the
      rebuild looks its own module up by name -- so a generator holding
      one fails to import at all if it is not registered first.
    * It is registered under its plain name, not a private alias, so
      that 'questions' importing 'corpus' as a sibling gets the module
      already loaded here rather than a second copy of it. Two copies
      would each carry their own pinned corpus hash, and the check that
      questions match the corpus would be comparing a value with itself.
    """
    if name in sys.modules:
        return sys.modules[name]
    path = cells_module.jig_root() / "fixtures" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    directory = str(path.parent)
    if directory not in sys.path:
        sys.path.insert(0, directory)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[name]
        raise
    return module


def corpus():
    """The corpus generator module."""
    return _load("corpus")


def questions():
    """The questions generator module."""
    return _load("questions")


def build_corpus(
    destination: pathlib.Path,
    source: str = "docs-skill",
    config_path: pathlib.Path | None = None,
) -> dict[str, object]:
    """Build the RAG database for one cell, and return its manifest.

    The manifest records which documents went in, and the release or
    seed they came from.
    """
    module = corpus()
    if config_path is None:
        config_path = (
            cells_module.jig_root() / "installation" / "haiku.rag.yaml"
        )
    return module.build(source, destination, config_path)


def load_questions() -> list:
    """The committed questions, checked against the pinned corpus.

    Reads a committed file; contacts nothing. A run must not need a
    model to be reachable in order to know what it is asking.
    """
    return questions().load()


def write_fixture(destination: pathlib.Path) -> str:
    """Scaffold hook. Not answerable for this set yet -- see the error."""
    raise ReportShapeUndecided
