# AGENTS.md

Guidance for AI coding agents working in this repository. Human contributors
should read [PRAXIS.md](PRAXIS.md), which covers the same ground in full.

**Read this before doing anything.** This is not a software repository, and
several ordinary, helpful-looking actions are forbidden here.

## Two things that must not happen

1. **Never commit customer-derived material.** This repository is
   **public**. Production or staging room prompts, customer skill
   instructions, customer data, and fixtures built from them are all
   forbidden, and git history makes a mistake permanent. Copying a downstream
   prompt into a cell "so it reproduces faithfully" is exactly the mistake to
   avoid. If an experiment needs such material, it does not belong here.
2. **Never delete or force-push a `set/` or `exp/` branch.** They are the
   archive, not stale work. They will look abandoned -- unmerged, old, no
   open PR. They are supposed to look like that.

## Your rules depend on which branch you are on

Check first:

    git branch --show-current

| you are on | you may | you may not |
| --- | --- | --- |
| `main` | edit praxis docs on a `praxis/<topic>` branch, then PR to `main` | commit experiment code, jigs, or data |
| `praxis/<topic>` | commit praxis-doc changes; PR into `main` | commit experiment code, jigs, or data |
| `set/<name>` | read; branch to `jig/...` for changes | commit directly; open a PR to `main` |
| `jig/<set>/<topic>` | commit jig changes; PR **into** the `set/` branch | PR to `main` |
| `exp/<set>/<slug>` | commit results and experiment-local code directly | open a PR anywhere |

A branch off a `set/` branch is mergeable only if it is named `jig/...`. An
`exp/...` branch is never the basis for a pull request.

## One worktree per branch

Do not `git switch` in the `main` worktree. It stays on `main`. Every other
branch of open work gets **its own worktree**, named for the branch with the
slashes flattened:

    lab_bench/main                        main
    lab_bench/set-soliplex-room-behavior  set/soliplex-room-behavior
    lab_bench/jig-harness-0.1.1           jig/soliplex-room-behavior/harness-0.1.1
    lab_bench/exp-defer-loading-3x2       exp/soliplex-room-behavior/defer-loading-3x2

Create one with, from any existing worktree:

    git worktree add ../<flattened-name> <branch>
    git worktree add ../<flattened-name> -b <new-branch> main

Run `git worktree list` before assuming which tree you are in.

**Why.** These branches hold mutually incompatible content -- praxis
documents, a jig, results -- so moving one working tree between them churns
untracked files and invites committing a file to the wrong branch. That has
already happened once: an `experiment/` directory intended for an `exp/`
branch landed in a `jig/` commit and had to be amended out.

### Tidying up

- When a transient branch (`praxis/`, `jig/`) is deleted on `origin` after
  its pull request merges, delete its worktree.
- When an experiment's issue is closed, delete the experiment worktree **and
  the local branch**. The branch on `origin` is the archive, and it is
  protected against deletion; a local copy is just a second thing to keep
  straight.

Neither cleanup touches the archive.

## Issues

**An issue comes before the pull request** for a bug, a feature, or a
guardrail -- so the design can be reacted to before an implementation lands
for review. Housekeeping (a version pin, a typo) is the exception. Do not
write the implementation and the issue in the same breath.

**Do not repeat the argument three times.** The issue states the problem;
the pull request mostly links to it; the commit message is terse. Findings,
tables, and evidence belong in one place, not in all three.

**Label to match the branch:** `exp:<set>`, `jig:<set>`, `set:<set>`,
`praxis`. A label is the branch's first two segments joined with `:`, so a
set's experiments and jigs all carry that set's name; `praxis/<topic>` is
the exception, labelled bare `praxis`.

**Close the issue by hand.** A `jig/` pull request targets a `set/`
branch, and GitHub only auto-closes for pull requests into the
default branch. Nothing will close it for you. Keep `Closes #N` in the pull
request body regardless -- it records intent -- and note that the keyword
does nothing in a commit message alone.

## Running an experiment

Before spending trials, print the state the hypothesis depends on and confirm
it is what you expect -- which capabilities are deferred, which tool names
are registered, which environments exist. A cell that structurally cannot
exhibit the behavior under test yields a null that reads as a real result.
This has already happened twice.

Record interpretation as comments on the experiment's issue. Commit artifacts
to the `exp/` branch. Do not put findings only in a commit message.

## Reporting

Do not describe an unreproduced failure as fixed, or a null result as
evidence of no effect. State N. See the reporting section of
[PRAXIS.md](PRAXIS.md).
