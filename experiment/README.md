# `defer_loading`, isolated from the 0.78 skill hardening

Tracked as [issue #4](https://github.com/soliplex/lab_bench/issues/4), where
the metadata and the findings live. This directory holds the artifacts.

## What was run

Three code arms x two models, N=20, task held constant.

| arm | soliplex | what it isolates |
| --- | --- | --- |
| `v077` | 0.77.2 | defer-all policy, original `SKILL.md` |
| `v077skill` | 0.77.2 + 0.78.1's `SKILL.md` | defer-all policy, hardened skill |
| `v078` | 0.78.1 | per-skill `defer_loading`, hardened skill |

`v077` vs `v077skill` isolates the skill-instruction hardening (#1309).
`v077skill` vs `v078` isolates the `defer_loading` default change (#1305).

Jig: `set/soliplex-room-behavior` @ `de84b79`.
Harness: `soliplex-lab-harness` v0.1 (`417b383`).

## Reproducing

```bash
cd jig
uv sync
uv run python -m room_behavior build  <work> --trials 20
uv run python -m room_behavior run    <work>
uv run python -m room_behavior report <work>
```

Nothing here depends on a checkout of soliplex: each arm installs its
version from PyPI, and the overlay arm's `SKILL.md` is extracted from a
throwaway install of the donor version.

## Contents

- `results/<cell>.jsonl` -- one record per trial: tool calls under the names
  the model actually used, response, timing, and the metadata identifying
  the arm.
- `report.txt` -- the scored table, as posted to the issue.

The working tree the run produced (`work/`) is not committed: cells and
environments are disposable and rebuildable from the jig.
