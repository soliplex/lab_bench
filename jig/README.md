# `room-behavior` jig

Measures how a soliplex room's agent behaves, for the
`soliplex-room-behavior` experiment set.

## What it varies

| axis | kind | values |
| --- | --- | --- |
| code | pinned soliplex version | `v077` (0.77.2), `v077skill` (0.77.2 + 0.78.1's `SKILL.md`), `v078` (0.78.1) |
| prompt | the room's `prompt.txt` | the shipped one, plus whatever an experiment declares |
| model | OpenAI-compatible endpoint | `gemma4`, `glimmer` |

The task is held constant by default: one question with a single verifiable
answer, computed from a seeded CSV on the room volume.

`v077` versus `v078` is the `defer_loading` default change. `v077skill`
separates that from the skill-instruction hardening that shipped in the same
release, by holding 0.77.2 with 0.78.1's `SKILL.md` overlaid.

### The experiment declares its matrix

The jig owns the *mechanism* -- a cell may vary the room prompt. An
experiment owns the *content*: the prompt texts are the treatment under
test, they change per experiment, and they belong beside the results they
produced, on the `exp/` branch.

```toml
# experiment/matrix.toml, with its texts in experiment/prompts/
task = "What is the total order value for the Southeast region?"
trials = 30

[[arms]]
name = "v078"
version = "0.78.1"

[[styles]]
name = "named"
prompt = "prompts/named.txt"   # relative to this file

[[styles]]
name = "tools"                 # no prompt: the one the jig ships

[[models]]
name = "gemma4"
base_url = "http://bizon:11432"
model_id = "gemma4-26b"
```

`build --matrix experiment/matrix.toml` resolves that and writes
`<work>/matrix.json`; `run`, `verify-assumptions` and `report` read it back
from there. So a results directory can be interpreted without the jig
revision that produced it -- and with no `--matrix` at all, the default
reproduces [#4](https://github.com/soliplex/lab_bench/issues/4).

**A cell is named for the axes that actually vary.** Three code arms across
two models are `v077-gemma4` and friends; three prompt styles across two
models are `named-gemma4`. An axis with one value says nothing about which
cell you are looking at, so it stays out of the name -- which is another
reason the matrix is written down rather than recomputed.

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

`build` refuses to finish if two prompt-axis arms installed identical text.
That is the shape of the defect that once collapsed `v077skill` into `v077`
([lab_harness#5](https://github.com/soliplex/lab_harness/issues/5)): the run
completes, the table looks plausible, and the comparison measured nothing.

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
- every prompt-axis arm must have installed **distinct** text, digested
  from what is on disk rather than from what was declared. Two arms that
  install the same prompt are one arm wearing two names, and any difference
  the report shows between them is noise

`verify-assumptions` asserts what only a recorded turn can show:

- the room config loads under this soliplex version and a turn completes
- deferral engages where the arm's `expects_deferral` says it must. That
  is about policy, not the model's choice: 0.77.x defers the sandbox itself
  once the room has two routing capabilities, so a turn cannot proceed
  without `load_capability`. 0.78.x leaves the sandbox eager and defers only
  the filesystem skill, so loading it is up to the model -- `expects_deferral`
  is `None` there and nothing is asserted

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
| `retry` | did any call come back as a `ModelRetry` |
| `list_environments x2+` | was a tool called repeatedly |

`used load_capability` decides whether an arm exercised the mechanism under
test at all. A cell that never loads a capability cannot say anything about
deferral, and its clean result is not evidence.

`ok` and `correct` sit at the ceiling in a room that works -- 95-100% across
every cell of #4 -- so **`retry` is the error signal with room to move**: it
counts what a run had to recover from on the way, which the run's success
hides. Alongside the rates, `report` prints a distribution table (mean, sd,
median, min, max) for turns, seconds and retries, and seconds-per-turn,
which separates "more round-trips" from "slower round-trips". #4's finding
was a standard deviation collapsing from 8.6 to 1.5 while the median barely
moved; that table had to be computed by hand at the time.

A record written before harness v0.3 carries no outcomes and reports `-`
for retries rather than a clean sheet.

## Fixture

`fixtures/orders.py` writes `orders.csv`: seed 1319, 60 rows, 17 of them
`Southeast`, expected Southeast total **40935.89**. It raises rather than
warns if the total ever changes, because every recorded result is scored
against that number.

Committed as a generator rather than a CSV: smaller, self-documenting, and
there is no question about whether the data may be published.
