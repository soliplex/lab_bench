# lab_bench

A **lab bench**: a place to run and preserve measurement experiments about
how Soliplex installations actually behave.

Nothing here ships. This repository deliberately releases no software, and
it is deliberately separate from any repository that does. Its purpose is
reproducibility: an experiment run six months ago should still be findable,
re-runnable, and readable.

## Companion repository

[soliplex/lab_harness](https://github.com/soliplex/lab_harness) holds the
reusable machinery -- the `soliplex-lab-harness` package. It is ordinary
released software with an ordinary branch model.

This repository holds only the experiment-specific parts: the jigs built on
that harness, and the results. A jig depends on a pinned harness version; it
never vendors one.

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
- every **set** has one too, created from the set-proposal template: a set
  is proposed and accepted rather than branched by hand, and accepting it
  is what creates `set/<name>`, its scaffold, and its label
- issues carry a label mirroring their branch kind -- `exp:<set>`,
  `jig:<set>`, `set:<set>`, `praxis` -- so a set's listing separates
  experiments run from work on the apparatus
- a `status:` label says where a proposal stands -- `proposed`, `accepted`,
  `declined` -- which is a different question from what kind of work it is

So the list of experiments for a set is a label query, and it is always
current because nobody has to remember to update it.

## Start here

- [PRAXIS.md](PRAXIS.md) -- how and when to create a set, a jig, and an
  experiment; what to record; what may not be committed here
- [AGENTS.md](AGENTS.md) -- rules for AI coding agents, which differ by
  branch and are not what an agent would otherwise assume
