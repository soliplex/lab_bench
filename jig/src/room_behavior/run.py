"""Run one cell's trials. Executed *inside* that cell's code-axis env.

Invoked as a script rather than an installed module, so a code-axis
environment only ever needs soliplex and the harness:

    <env>/bin/python run.py <cell>/spec.json [target]

``trials`` in the spec is a **target**, not a count: this tops the result
file up to that many records and does nothing if it is already there. So a
single smoke trial can be run first, verified, and then extended to the full
N without discarding it -- and an interrupted run resumes rather than
restarting.
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
        # vLLM ignores the key, but the OpenAI client insists on one.
        env={"OPENAI_API_KEY": "unused-by-vllm"},
    )

    collector = drive.install_collector()
    installation = drive.load_installation(target)

    done = len(records.read(results)) if results.exists() else 0
    wanted = spec["trials"]
    if done >= wanted:
        print(f"[{spec['cell']}] already has {done}/{wanted}", flush=True)
        return 0

    for trial in range(done, wanted):
        record = drive.run_trial(
            target,
            spec["task"],
            cell=spec["cell"],
            trial=trial,
            collector=collector,
            installation=installation,
            metadata=spec["metadata"],
        )
        records.append(results, record)
        names = " -> ".join(n or "?" for n in record.call_names)
        print(
            f"[{record.cell} #{trial}] {record.elapsed_s}s "
            f"ok={record.ok} {names or '(no calls)'}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
