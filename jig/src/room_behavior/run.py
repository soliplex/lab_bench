"""Run one cell's trials. Executed *inside* that cell's code-axis env.

Invoked as a script rather than an installed module, so a code-axis
environment only ever needs soliplex and the harness:

    <env>/bin/python run.py <cell>/spec.json
"""

from __future__ import annotations

import json
import pathlib
import sys

from soliplex_lab_harness import drive
from soliplex_lab_harness import records


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <spec.json>", file=sys.stderr)
        return 2

    spec = json.loads(pathlib.Path(argv[1]).read_text(encoding="utf-8"))
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

    for trial in range(spec["trials"]):
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
