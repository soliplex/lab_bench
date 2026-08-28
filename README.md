# lab_bench

A **lab bench**: a place to run and preserve measurement experiments about
how Soliplex installations actually behave.

Nothing here ships. This repository deliberately releases no software, and
it is deliberately separate from any repository that does. Its purpose is
reproducibility: an experiment run six months ago should still be findable,
re-runnable, and readable.

## The branch model

| branch | holds | merges? |
| --- | --- | --- |
| `main` | praxis documents only | PRs to `main` change praxis, nothing else |
| `set/<name>` | an experiment set and its measurement jig(s) | **never** merged to `main` |
| `jig/<set>/<topic>` | in-progress jig work | merges **into** its `set/` branch |
| `exp/<set>/<slug>` | one experiment: local jig bits, data, results | **never** merged anywhere |

`set/` and `exp/` branches are the archive. They are never merged and never
deleted. See [PRAXIS.md](PRAXIS.md).

## Finding things

There is no index file. The issue tracker is the index:

- every experiment has an issue, created from the experiment template, that
  names the branches it uses
- each issue carries a `set:<name>` label

So the list of experiments for a set is a label query, and it is always
current because nobody has to remember to update it.

## Start here

- [PRAXIS.md](PRAXIS.md) -- how and when to create a set, a jig, and an
  experiment; what to record; what may not be committed here
- [AGENTS.md](AGENTS.md) -- rules for AI coding agents, which differ by
  branch and are not what an agent would otherwise assume
