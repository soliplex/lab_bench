# `room-behavior` jig

Measures how a soliplex room's agent behaves, for the
`soliplex-room-behavior` experiment set.

## What it varies

| axis | kind | values |
| --- | --- | --- |
| code | pinned soliplex version | `v077` (0.77.2), `v077skill` (0.77.2 + 0.78.1's `SKILL.md`), `v078` (0.78.1) |
| model | OpenAI-compatible endpoint | `gemma4`, `glimmer` |

Six cells. The task is held constant: one question with a single verifiable
answer, computed from a seeded CSV on the room volume.

`v077` versus `v078` is the `defer_loading` default change. `v077skill`
separates that from the skill-instruction hardening that shipped in the same
release, by holding 0.77.2 with 0.78.1's `SKILL.md` overlaid.

## Running it

```bash
uv sync
uv run python -m room_behavior build  <work>            # install, verify
uv run python -m room_behavior run    <work> --trials 1 # smoke turn
uv run python -m room_behavior verify-assumptions <work>
uv run python -m room_behavior run    <work> --trials 20
uv run python -m room_behavior report <work>
```

`--trials` is a **target**, not a count: `run` tops each cell up to it and
does nothing if the cell is already there. So the smoke turn counts toward N
rather than being discarded, and an interrupted run resumes instead of
restarting.

`<work>` is a disposable directory. `build` is slow -- it installs soliplex
once per arm and syncs each sandbox environment -- and idempotent. Restrict
either step with `--cells v078-gemma4,v078-glimmer`.

`run` shells into each cell's own code-axis environment. That is the whole
point: the software under test is **installed**, never imported from a
checkout, so an arm is reproducible from a version string.

## Why the installation is ours

`jig/installation/` is a complete, minimal soliplex installation: one agent
config, one room, two sandbox environments, no RAG, no filesystem skills, no
OIDC, no completions, no quizzes.

soliplex's own `example/` tree is not an option -- it does not ship in the
wheel, so an installed soliplex has no `example/rooms/` at all. That turns
out to be a benefit: the room under test belongs to the experiment, so a cell
cannot change underneath us because someone edited an example upstream.

Three details in there that took a while to find, and that a future minimal
installation will hit again:

- `oidc_paths`, `completion_paths`, `quizzes_paths` and
  `filesystem_skills_paths` each default to a directory that must exist. A
  single `null` entry is the documented way to have none.
- `haiku_rag_config_file` defaults to `./haiku.rag.yaml` with no null escape,
  and `soliplex-cli audit` opens it. An empty file satisfies it.
- `thread_persistence_dburi` and `authorization_dburi` are **cwd-relative**
  sqlite URIs, unlike every other path, so each cell runs with its own
  working directory.

## Preconditions

Every defect found in this jig so far was **silent**: the run completed and
the table looked plausible. So the assumptions are asserted, not assumed.

`build` verifies each thing as it makes it, and raises:

- a code-axis install must match its own `RECORD`, except where an overlay
  declares otherwise (`verify_install`)
- a sandbox environment must import what it declares, checked through
  `uv --directory` so a *resolution* failure is caught and not merely a
  missing module -- how a uv project named after its own dependency presents

`verify-assumptions` asserts what only a recorded turn can show:

- the room config loads under this soliplex version and a turn completes
- deferral engages or does not, per the arm's `expects_deferral`. It is
  arm-specific: 0.77.x defers the sandbox itself once the room has two
  routing capabilities, while 0.78.x defers only the filesystem skill, which
  this task gives the model no reason to load

`verify-assumptions` never drives a turn; it reads what `run` recorded.

## Metrics

Per cell, over N trials:

| metric | why |
| --- | --- |
| `ok` | did the turn complete |
| `correct` | did the answer contain the expected total |
| `bad tool` | did the model call a tool the room does not have |
| `bad environment_name` | did it guess a sandbox environment |
| `used load_capability` | was a deferred capability actually loaded |

The last one is the one that decides whether an arm exercised the mechanism
under test at all. A cell that never loads a capability cannot say anything
about deferral, and its clean result is not evidence.

## Fixture

`fixtures/orders.py` writes `orders.csv`: seed 1319, 60 rows, 17 of them
`Southeast`, expected Southeast total **40935.89**. It raises rather than
warns if the total ever changes, because every recorded result is scored
against that number.

Committed as a generator rather than a CSV: smaller, self-documenting, and
there is no question about whether the data may be published.
