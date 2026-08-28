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
| `main` | edit praxis docs; open a PR from a branch off `main` | commit experiment code, jigs, or data |
| `set/<name>` | read; branch to `jig/...` for changes | commit directly; open a PR to `main` |
| `jig/<set>/<topic>` | commit jig changes; PR **into** the `set/` branch | PR to `main` |
| `exp/<set>/<slug>` | commit results and experiment-local code directly | open a PR anywhere |

A branch off a `set/` branch is mergeable only if it is named `jig/...`. An
`exp/...` branch is never the basis for a pull request.

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
