"""What this experiment set can vary, and what one experiment does vary.

Three axes:

* **code** -- a pinned soliplex version, optionally with a file overlaid
  from another release, which separates two changes that shipped together.
* **prompt** -- the room's ``prompt.txt``. The jig owns the mechanism; an
  experiment owns the texts, which live on its ``exp/`` branch beside the
  results they produced.
* **model** -- an OpenAI-compatible endpoint.

A ``Matrix`` is one experiment's choice of values on those axes, plus the
task and the trial target. ``DEFAULT_MATRIX`` reproduces the set's first
experiment (soliplex/lab_bench#4) exactly, so an experiment that declares
nothing still runs the thing this jig was built for.

Cell names carry only the axes that actually vary in the matrix they come
from: three code arms against two models are ``v077-gemma4`` and friends,
while three prompt styles against two models are ``named-gemma4``. A name
is therefore only meaningful alongside its matrix, which is why ``build``
writes the resolved matrix into the work directory rather than leaving it
to be recomputed.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib
import tomllib

DATA_TASK = "What is the total order value for the Southeast region?"

#: The room the jig drives, and where its prompt lives inside a rendered
#: installation.
ROOM_ID = "workbench"
ROOM_PROMPT = f"rooms/{ROOM_ID}/prompt.txt"

#: Tools the room actually registers. Anything else is a name the model
#: invented -- see 'scoring.invented_tool_name'.
ROOM_TOOLS = frozenset(
    {
        "list_environments",
        "list_volume_files",
        "run",
        "run_python",
        "load_capability",
        "search_tools",
    }
)

#: Environments the sandbox offers. Anything else was guessed.
SANDBOX_ENVIRONMENTS = frozenset({"bare", "pandas-only", None})

#: Sandbox environment -> a module it must be able to import. A uv project
#: sharing a name with one of its dependencies resolves to nothing while
#: 'uv sync' still exits cleanly, so this is checked rather than assumed.
SANDBOX_IMPORTS = {"pandas-only": "pandas"}

#: Where the sandbox skill's instructions live inside an install.
SKILL_MD = "soliplex/skills/bwrap_sandbox/SKILL.md"


class PromptStyleMissing(Exception):
    """A declared prompt style points at a file that is not there.

    Raised while resolving the declaration, before anything is built: a
    style silently falling back to the shipped prompt would collapse two
    arms into one.
    """

    def __init__(self, name: str, path: pathlib.Path):
        self.name = name
        self.path = path
        super().__init__(f"prompt style {name!r}: no such file: {path}")


class MatrixMissing(Exception):
    """A work directory carries no resolved matrix."""

    def __init__(self, work: pathlib.Path):
        self.work = work
        super().__init__(f"no matrix in {work}; run 'build' first")


def digest(path: pathlib.Path) -> str:
    """A short content digest, for telling two arms apart."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


@dataclasses.dataclass(frozen=True, slots=True)
class Model:
    name: str
    base_url: str
    model_id: str

    def as_dict(self) -> dict[str, str]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True, slots=True)
class Arm:
    """One code-axis value: a version, plus any overlay it needs.

    ``expects_deferral`` is about the arm's **policy**, not the model's
    choice:

    * ``True`` -- the sandbox itself is deferred, so a turn cannot proceed
      without ``load_capability``. 0.77.x defers every routing capability
      once a room has more than one.
    * ``None`` -- do not check. 0.78.x leaves the sandbox eager and defers
      only the filesystem skill, so loading it is up to the model: the
      ``reporting`` skill asks to be loaded before a currency figure is
      reported, and this task asks for one. Asserting either way there would
      assert a model choice.
    * ``False`` -- assert that nothing was loaded. No arm here needs it, but
      it stays expressible.
    """

    name: str
    version: str
    overlay_from: str | None = None
    note: str = ""
    expects_deferral: bool | None = None

    def as_dict(self) -> dict[str, object]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True, slots=True)
class PromptStyle:
    """One prompt-axis value: a room ``prompt.txt``, or the jig's own.

    ``prompt`` is ``None`` for the prompt this jig ships, which is a real
    arm and not a missing one: an experiment comparing authored prompts
    against the shipped one needs it as a cell like any other.

    The text itself is deliberately not kept here. It is the treatment
    under test, it changes per experiment, and it belongs beside the
    results it produced -- on the ``exp/`` branch, named by a matrix.
    """

    name: str
    prompt: pathlib.Path | None = None
    note: str = ""

    def source(self) -> pathlib.Path:
        """The file to install, shipped or supplied."""
        if self.prompt is None:
            return jig_root() / "installation" / ROOM_PROMPT
        return self.prompt

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "prompt": None if self.prompt is None else str(self.prompt),
            "note": self.note,
            "digest": digest(self.source()),
        }


#: The prompt the jig ships, as an arm. Named for what it is: an
#: experiment that varies prompts will usually also carry its own copy of
#: this text, so that drift here fails a precondition instead of quietly
#: changing what a recorded arm meant.
SHIPPED_STYLE = PromptStyle(name="jig", note="the prompt the jig ships")


@dataclasses.dataclass(frozen=True, slots=True)
class Cell:
    arm: Arm
    style: PromptStyle
    model: Model
    task: str
    name: str


MODELS = (
    Model(
        name="gemma4",
        base_url="http://bizon:11432",
        model_id="gemma4-26b",
    ),
    Model(
        name="glimmer",
        base_url="http://bizon:11450",
        model_id="Inferact/Muse-Glimmer-30B-NVFP4-W4A4",
    ),
)

ARMS = (
    Arm(
        name="v077",
        version="0.77.2",
        note="defer-all policy",
        expects_deferral=True,
    ),
    Arm(
        name="v077skill",
        version="0.77.2",
        overlay_from="0.78.1",
        note="defer-all policy, hardened SKILL.md",
        expects_deferral=True,
    ),
    Arm(
        name="v078",
        version="0.78.1",
        note="per-skill defer_loading",
        expects_deferral=None,
    ),
)


@dataclasses.dataclass(frozen=True, slots=True)
class Matrix:
    """One experiment's cells: the axis values it crosses.

    Declared by the experiment, resolved by ``build``, and then read back
    from the work directory by everything downstream -- so a results
    directory can be interpreted without the jig revision that produced it.
    """

    arms: tuple[Arm, ...] = ARMS
    styles: tuple[PromptStyle, ...] = (SHIPPED_STYLE,)
    models: tuple[Model, ...] = MODELS
    task: str = DATA_TASK
    trials: int = 20

    def _varying(self) -> tuple[bool, bool, bool]:
        """Which axes earn a place in a cell name.

        An axis with one value says nothing about which cell this is. When
        nothing varies -- a single cell -- everything is named, because a
        nameless cell is worse than a redundant one.
        """
        flags = (
            len(self.arms) > 1,
            len(self.styles) > 1,
            len(self.models) > 1,
        )
        return flags if any(flags) else (True, True, True)

    def name_for(
        self, arm: Arm, style: PromptStyle, model: Model
    ) -> str:
        wanted = self._varying()
        parts = (arm.name, style.name, model.name)
        return "-".join(
            part for part, keep in zip(parts, wanted, strict=True) if keep
        )

    def cells(self) -> list[Cell]:
        return [
            Cell(
                arm=arm,
                style=style,
                model=model,
                task=self.task,
                name=self.name_for(arm, style, model),
            )
            for arm in self.arms
            for style in self.styles
            for model in self.models
        ]

    def by_name(self, name: str) -> Cell:
        for cell in self.cells():
            if cell.name == name:
                return cell
        raise KeyError(name)

    # -- serialization ---------------------------------------------------
    def as_dict(self) -> dict[str, object]:
        return {
            "task": self.task,
            "trials": self.trials,
            "arms": [arm.as_dict() for arm in self.arms],
            "styles": [style.as_dict() for style in self.styles],
            "models": [model.as_dict() for model in self.models],
            "cells": [cell.name for cell in self.cells()],
        }

    def save(self, path: pathlib.Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.as_dict(), indent=2), encoding="utf-8"
        )

    @classmethod
    def from_dict(
        cls, data: dict, base: pathlib.Path | None = None
    ) -> Matrix:
        """Build a matrix from a declaration.

        Prompt paths resolve against ``base`` -- the declaring file's own
        directory -- so an experiment can keep ``matrix.toml`` and its
        ``prompts/`` beside each other and move the pair around.
        """
        arms = tuple(
            Arm(
                name=item["name"],
                version=item["version"],
                overlay_from=item.get("overlay_from"),
                note=item.get("note", ""),
                expects_deferral=item.get("expects_deferral"),
            )
            for item in data.get("arms", ())
        ) or ARMS
        styles = tuple(
            _style_from(item, base) for item in data.get("styles", ())
        ) or (SHIPPED_STYLE,)
        models = tuple(
            Model(
                name=item["name"],
                base_url=item["base_url"],
                model_id=item["model_id"],
            )
            for item in data.get("models", ())
        ) or MODELS
        return cls(
            arms=arms,
            styles=styles,
            models=models,
            task=data.get("task", DATA_TASK),
            trials=int(data.get("trials", 20)),
        )

    @classmethod
    def load(cls, path: pathlib.Path) -> Matrix:
        """Read a declaration -- ``.toml`` or ``.json`` -- from ``path``."""
        raw = path.read_bytes()
        if path.suffix == ".toml":
            data = tomllib.loads(raw.decode("utf-8"))
        else:
            data = json.loads(raw)
        return cls.from_dict(data, base=path.parent.resolve())


def _style_from(
    item: dict, base: pathlib.Path | None
) -> PromptStyle:
    raw = item.get("prompt")
    if raw is None:
        prompt = None
    else:
        prompt = pathlib.Path(raw)
        if not prompt.is_absolute() and base is not None:
            prompt = base / prompt
        prompt = prompt.resolve()
        if not prompt.is_file():
            raise PromptStyleMissing(item["name"], prompt)
    return PromptStyle(
        name=item["name"], prompt=prompt, note=item.get("note", "")
    )


#: The set's first experiment, reproducible without declaring anything.
DEFAULT_MATRIX = Matrix()


def jig_root() -> pathlib.Path:
    """The jig directory, found relative to this file."""
    return pathlib.Path(__file__).resolve().parents[2]


def load_matrix(work: pathlib.Path) -> Matrix:
    """The resolved matrix ``build`` wrote into ``work``."""
    path = work / "matrix.json"
    if not path.is_file():
        raise MatrixMissing(work)
    return Matrix.from_dict(json.loads(path.read_text(encoding="utf-8")))
