# Praxis

How we run and preserve measurement experiments. A pull request against
`main` may change files like this one, and two other things: the forms and
workflows under `.github/`, and the scaffold in `set-template/`.

`set-template/` is not a jig, and there is a mechanical test for that rather
than an argument: every file in it ends `.tmpl`, so nothing in the tree is
importable, buildable, or runnable, and there is no `pyproject.toml` for
tooling to discover. It is a form, like the issue templates beside it.

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
  one experiment set. Set-branch-local, and specific to that set's subject.
- **harness** -- the reusable machinery a jig is built on, released from
  [soliplex/lab_harness](https://github.com/soliplex/lab_harness) as the
  `soliplex-lab-harness` package.

## Axis kinds

Only the first involves the software under test changing. Conflating it with
the others makes a jig more complicated than it needs to be.

1. **Code axis** -- the hypothesis is about the software itself (a release
   comparison, a branch against its base). Each value is a **ref
   specification**, installed as a pinned dependency into its own virtualenv.
   See [Code axes](#code-axes).
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

## Code axes

An experiment does not check out the software under test. It **installs** it.

Each code-axis value is a pinned dependency in its own virtualenv:

- a released version -- an ordinary version pin, e.g. `soliplex==0.78.1`
- any other ref -- a git dependency, e.g.
  `soliplex @ git+https://github.com/soliplex/soliplex@<sha>`

Cells sharing a code-axis value share that virtualenv.

Record the **resolved commit sha** on the experiment issue, not just the tag or
branch name. Tags can be moved and branches certainly do; a finding pinned to
`main` is pinned to nothing.

Why install rather than check out:

- the experiment never touches a checkout it does not own, so there is nothing
  to dirty, restore, or accidentally commit
- an arm is reproducible from a spec string, which is small enough to live on
  the issue
- it measures the software **as shipped**, not as an editable working tree

### Confirm the assets are actually packaged

An editable checkout exposes every file in the tree. An installed distribution
exposes only what its packaging includes. If the software ships non-Python
assets that affect behavior -- prompt text, skill instructions, schemas -- then
an installed arm silently measures *different software* than a checkout would
when those assets are missing.

Check once per code axis, and assert it in the jig. For soliplex, `MANIFEST.in`
carries `global-include SKILL.md` and `soliplex/skills/bwrap_sandbox/SKILL.md`
is present in the built wheel, so skill instructions do travel.

### Isolating co-landed changes

A release bundles every change in it. Attributing an effect to one of them
needs a synthetic arm: ref A, but with one file taken from ref B.

Declare that as an **overlay** in the experiment spec -- the file, its source
ref, and where it lands -- applied after the environment is built, with the
overlay content committed to the `exp/` branch. The arm then describes itself,
and no branch has to be invented in the software repository to represent a
state nobody ever shipped.

## Branches

| kind | naming | merges | lifetime |
| --- | --- | --- | --- |
| praxis | `main` | PRs change praxis docs only | forever |
| praxis work | `praxis/<topic>` | merges into `main` | delete after merge |
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
- Each branch of open work gets its own **worktree**, and the `main` worktree
  stays on `main`. These branches hold mutually incompatible content, so
  switching one working tree between them invites committing a file to the
  wrong branch. See [AGENTS.md](AGENTS.md).

## Creating an experiment set

Create a new set when the *subject* changes -- a different installation, a
different room family, a different question. Reuse an existing set when only
the axes change; that is what experiments within a set are for.

A set is not created by hand. It is **proposed**, and the forge creates the
container when the proposal is accepted:

1. **File a set proposal** from the issue template. It is born
   `status:proposed`, and argues scope: what phenomenon, why it deserves
   apparatus, what it would cost. Start in a discussion and promote it here
   once the scope has settled -- nothing is lost when a discussion ends in
   no set.
2. **Acceptance is adding `status:accepted`.** A workflow creates
   `set/<name>` already pointing at its scaffold commit, mints the
   `set:<name>` label, and puts it on the proposal -- which becomes the
   set's own issue, since the scope it argued is exactly what that label
   is for. Declining is closing the proposal `status:declined`, with no
   branch and no label.
3. **The jig arrives by pull request**, from `jig/<name>/initial` into
   `set/<name>`, and is reviewed there.

The split is that **the forge generates the container, and people author and
review the contents.** No workflow writes anything anyone has to trust.

Two things follow from the `set/*` rules, and are worth knowing before
accepting anything:

- **Acceptance is irreversible.** The branch cannot be deleted or
  force-pushed, by anyone, without disabling the ruleset. The workflow
  therefore validates the name and the package before it creates the ref.
- **The scaffold lands in the creating push.** Ref creation is exempt from
  the `pull_request` rule, but nothing afterwards is, so the workflow gets
  exactly one shot and can never push a correction.

### Jig vs. harness

A jig is specific to one experiment set: it knows what a cell looks like for
*this* subject, which preconditions to assert, and how to score *these*
metrics. It lives on the set branch and it may accrete.

The reusable machinery underneath it -- the span collector, the trial driver,
environment construction for code axes, config overlays, the scorer framework,
export -- is **not** a jig. It is released from
[soliplex/lab_harness](https://github.com/soliplex/lab_harness) as the
`soliplex-lab-harness` package, and a jig **depends on a pinned version** of
it rather than vendoring a copy. Otherwise every set branch quietly forks the
harness, and two experiments a year apart are no longer comparable because
the thing that measured them drifted.

Record the pinned version on the experiment issue. A finding is only
reproducible if the measuring apparatus is identified too.

## Issues

The issue tracker is the index (see [README.md](README.md)), so it has to
stay in step with the branches.

### Labels mirror the branch kinds

| label | for work on | branch prefix |
| --- | --- | --- |
| `exp:<set>` | one experiment | `exp/<set>/<slug>` |
| `jig:<set>` | that set's jig | `jig/<set>/<topic>` |
| `set:<set>` | the set itself -- its scope, its retirement | `set/<set>` |
| `praxis` | these documents | `praxis/<topic>` |

So a label is the branch's first two segments joined with `:`. The slug or
topic is dropped, which is what lets every experiment in a set share one
label, and so what makes the label query for a set separate experiments run
from work on the apparatus. `praxis/<topic>` is the exception: praxis work
is not scoped to a set, so the label is bare `praxis`.

### Lifecycle is a second axis

| label | meaning |
| --- | --- |
| `status:proposed` | filed, not yet accepted |
| `status:accepted` | accepted; the branch and label exist |
| `status:declined` | not being run |

These derive from no branch -- they say where a proposal stands, not what
kind of work it is -- so they are a separate namespace and the rule above
does not reach them. A proposal carries one of the three *and* nothing else
until it is accepted, because the label naming its set is one of the things
acceptance creates.

Adding a named label is better than removing one: dropping
`status:proposed` is a stray click, while adding `status:accepted` is a
choice among three named outcomes, and the workflow can refuse unless
`status:proposed` was actually there.

### An issue needs to exist before the pull request

A bug, a new feature, or a guardrail gets an issue first, so the design can
be reacted to before an implementation arrives for review. Pure
housekeeping -- a version pin, a typo -- is the exception.

Keep the artifacts from repeating each other:

- the **issue** states the problem, and does not re-litigate the choices
  that led there
- the **pull request** mostly links to the issue
- the **commit message** is terse, pointing at the issue and the pull
  request for context

Reviewer fatigue is the reason, and it is not hypothetical: three tellings
of the same argument means checking that they agree, and the usual outcomes
are that something is overlooked or the whole thing stalls.

### Close the issue by hand

A `jig/` pull request targets a `set/` branch, never the default branch.
GitHub only forms a development link -- and only auto-closes -- for
pull requests into the default branch, so **nothing will close the issue for
you**. Close it when you merge.

Keep the `Closes #N` line in the pull request body anyway. It records the
intent, and it costs nothing. Two things about it are worth knowing, both
learned by getting them wrong:

- the keyword has to be in the pull request **body or title**; in a commit
  message alone it creates no link
- `Closes: #N` with a colon works as well as `Closes #N` without

Only `praxis/` pull requests target the default branch, so those are the
only ones where the automation does anything.

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
