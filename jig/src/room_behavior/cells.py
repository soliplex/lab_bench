"""What this experiment set varies.

Two axes:

* **code** -- a pinned soliplex version. This is the 'defer_loading'
  comparison: v0.77.2 defers every routing capability when a room has more
  than one, v0.78.1 defers per skill config. The 'v077skill' arm holds
  v0.77.2 with v0.78.1's 'SKILL.md' overlaid, which separates that change
  from the skill-instruction hardening that shipped alongside it.
* **model** -- an OpenAI-compatible endpoint.

The task is held constant.
"""

from __future__ import annotations

import dataclasses
import pathlib

DATA_TASK = "What is the total order value for the Southeast region?"

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


@dataclasses.dataclass(frozen=True, slots=True)
class Model:
    name: str
    base_url: str
    model_id: str


@dataclasses.dataclass(frozen=True, slots=True)
class Arm:
    """One code-axis value: a version, plus any overlay it needs.

    ``expects_deferral`` says whether a turn on this arm must call
    ``load_capability``. It is arm-specific, not a blanket rule: 0.77.x
    defers every routing capability once a room has more than one, so the
    sandbox itself is deferred there, while 0.78.x defers only the
    filesystem skill -- which this task gives the model no reason to load.
    Verification asserts against this, so the 0.78 behavior is not reported
    as a failure.
    """

    name: str
    version: str
    overlay_from: str | None = None
    note: str = ""
    expects_deferral: bool = False


@dataclasses.dataclass(frozen=True, slots=True)
class Cell:
    arm: Arm
    model: Model
    task: str = DATA_TASK

    @property
    def name(self) -> str:
        return f"{self.arm.name}-{self.model.name}"


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
        expects_deferral=False,
    ),
)

#: Where the sandbox skill's instructions live inside an install.
SKILL_MD = "soliplex/skills/bwrap_sandbox/SKILL.md"


def cells() -> list[Cell]:
    return [Cell(arm=arm, model=model) for arm in ARMS for model in MODELS]


def by_name(name: str) -> Cell:
    for cell in cells():
        if cell.name == name:
            return cell
    raise KeyError(name)


def jig_root() -> pathlib.Path:
    """The jig directory, found relative to this file."""
    return pathlib.Path(__file__).resolve().parents[2]
