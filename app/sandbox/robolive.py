"""Runs one learner program in the simulator. Runs in its own subprocess.

stdin:  JSON {"source": <learner code>, "arena": {...}, "seed": 12345}
stdout: JSON result payload (frames, events, prints, error, summary) for the browser replay.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import robosim  # noqa: E402

_real_stdout = sys.stdout


def main():
    payload = json.loads(sys.stdin.read())
    world, info = robosim.run_program(payload["source"], payload.get("arena") or {}, int(payload.get("seed", 12345)))
    out = robosim.result_payload(world, info)
    _real_stdout.write(json.dumps(out, separators=(",", ":")))


if __name__ == "__main__":
    main()
