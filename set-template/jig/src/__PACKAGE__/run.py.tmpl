"""Run one cell's trials. Executed *inside* that cell's code-axis env.

Invoked as a script rather than an installed module, so a code-axis
environment only ever needs the software under test and the harness:

    <env>/bin/python run.py <cell>/spec.json [target]

'trials' in the spec is a **target**, not a count. 'records.top_up'
honours that: a smoke trial can be run and verified before extending to
the full N without discarding it, and an interrupted run resumes.
"""

from __future__ import annotations

import json
import pathlib
import sys

from soliplex_lab_harness import drive
from soliplex_lab_harness import records


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print(f"usage: {argv[0]} <spec.json> [target]", file=sys.stderr)
        return 2

    spec = json.loads(pathlib.Path(argv[1]).read_text(encoding="utf-8"))
    if len(argv) == 3:
        spec["trials"] = int(argv[2])
    results = pathlib.Path(spec["results"])

    target = drive.Target(
        installation=pathlib.Path(spec["installation"]),
        room_id=spec["room_id"],
        cwd=pathlib.Path(spec["cwd"]),
    )
    collector = drive.install_collector()
    installation = drive.load_installation(target)

    def one_trial(trial: int) -> records.TrialRecord:
        return drive.run_trial(
            target,
            spec["task"],
            cell=spec["cell"],
            trial=trial,
            collector=collector,
            installation=installation,
            metadata=spec["metadata"],
        )

    wanted = spec["trials"]
    ran = records.top_up(results, wanted, one_trial)
    if not ran:
        done = records.completed(results)
        print(f"[{spec['cell']}] already has {done}/{wanted}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
