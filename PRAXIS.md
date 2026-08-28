# Praxis

How we run and preserve measurement experiments. This file, and only files
like it, are what a pull request against `main` may change.

## Why this exists

Changes to prompts, skill instructions, room configuration, and model choice
are *behavioral* changes to a stochastic system. A plausible mechanism plus
one trace is not evidence. The motivating case: a detailed analysis built on
a single trace, which 320 measured runs then failed to reproduce -- while the
same runs incidentally showed that an upgrade nobody had measured moved one
room from 70% to 100% correct.

An unmeasured change is fine **when labeled as such**. The point is not to
measure everything; it is to stop confusing a measurement with a hunch.

## Vocabulary

- **axis** -- one dimension of variation (a release, a model, a prompt, a
  task).
- **cell** -- one combination of axis values: a runnable installation plus
  the code that runs it. The unit that executes.
- **trial** -- one run of one cell. N trials per cell, because these effects
  are rates, not outcomes.
- **metric** -- something extracted per trial from the run's message history
  and its response.
- **jig** -- the code that builds cells, runs trials, and scores results for
  one experiment set.

## Axis kinds

Only the first needs separate worktrees. Conflating it with the others makes
a jig more complicated than it needs to be.

1. **Code axis** -- the hypothesis is about the software itself (a release
   comparison, a branch against its base). Each value is a **git ref** and
   needs its own worktree with its own built environment.
2. **Configuration axis** -- same code, patched installation: a room prompt,
   `model_name` / `provider_base_url`, model parameters, which skills a room
   mounts, `defer_loading`, whether a given tool is present in a room, how
   many sandbox environments exist.
3. **Task axis** -- same code, same configuration, different user prompt.
   Routinely underrated: **the task decides which mechanisms are reachable at
   all.** An experiment whose task never triggers the behavior under study
   produces a null that looks like a result.
4. **Held constant** -- fixtures, databases, environment definitions. Assert
   these are identical across cells (hash them); do not assume it.

## Branches

| kind | naming | merges | lifetime |
| --- | --- | --- | --- |
| praxis | `main` | PRs change praxis docs only | forever |
| experiment set | `set/<name>` | never merged to `main` | archival |
| jig work | `jig/<set>/<topic>` | merges into `set/<name>` | delete after merge |
| experiment | `exp/<set>/<slug>` | never merged anywhere | archival |

Rules:

- A PR against `main` never originates from a `set/`, `jig/`, or `exp/`
  branch.
- A `set/` branch changes only by PR from a `jig/` branch, so jig evolution
  is reviewed and visible.
- An `exp/` branch is committed to directly. That is the lab notebook; review
  would make it unusable.
- `set/` and `exp/` branches are **never deleted and never force-pushed**.
  Branch rules enforce this. A force-push is worse than a deletion because it
  destroys recorded results invisibly.

## Creating an experiment set

Create a new set when the *subject* changes -- a different installation, a
different room family, a different question. Reuse an existing set when only
the axes change; that is what experiments within a set are for.

    git switch main
    git switch -c set/<name>

Commit the jig. Keep the generic harness a **pinned dependency**, not a copy;
otherwise set branches quietly fork it.

## Running an experiment

1. **Open an issue** from the experiment template. It records the shared
   branch, the refs under test, model ids, N, the fixture seed, the harness
   version, and the verbatim task prompt.
2. **Branch from the set branch:**

       git switch set/<name>
       git switch -c exp/<name>/<slug>

3. **Verify preconditions before spending trials.** Print the state the
   hypothesis depends on -- resolved `defer_loading` flags, the tool names
   actually registered, which capabilities are deferred. Two nulls in the
   motivating investigation were burned on cells that structurally could not
   exhibit the behavior under test. One command would have caught both.
4. **Run.** Commit result data to the `exp/` branch as runs complete.
5. **Record findings as comments on the issue**, as you go. Interpretation
   lives in the issue; artifacts live in commits.

## What to commit

Commit:

- per-trial JSONL (one record per run)
- the **fixture generator**, not the fixture -- a seeded script, with the
  seed and the expected value recorded
- the report
- a *sample* raw message history, when one is illustrative

Do not commit:

- built virtualenvs, sandbox environment builds, RAG databases
- full raw message histories for every trial
- anything large enough that you would hesitate

## Reporting honestly

- State N. At N=20 a one- or two-run difference is not a result.
- Different metrics carry different signal. In the motivating work, turn
  count was steadier than correctness, and latency was mostly endpoint noise.
- A release axis bundles every change in the release. Attributing an effect
  to one of them requires a synthetic arm that holds the others constant.
- "Did not reproduce" is a finding. It is not "fixed", and it is not
  "no effect".

## What may not be committed here

**This repository is public.**

Never commit material derived from a customer or a private project:
production or staging room prompts, customer skill instructions, customer
data, or fixtures built from any of them.

An experiment that spans a public project and a private one has a
publishable part and an unpublishable part. Such an experiment lives in the
**most restrictive** bench available, and only its publishable subset is
reproduced here. When in doubt, it does not go here.
