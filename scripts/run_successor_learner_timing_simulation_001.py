"""Run `successor-learner-timing-simulation-001` (network-free).

Compares three learner-state estimators and three proactive timing policies
on simulated learners with hidden state over thirty virtual days, plus oracle
and never-intervene bounds. Writes per-learner rows, an aggregate summary, and
a Markdown table. No model or provider call is made.

Usage:
    uv run python scripts/run_successor_learner_timing_simulation_001.py \
        --output-dir reports/generated/successor-learner-timing-simulation-001
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from src.digital_twin.evaluation.successor_simulation import (  # noqa: E402
    ProgramConfig,
    run_program,
    write_outputs,
)


def _code_revision() -> dict[str, str | bool]:
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT, check=True, capture_output=True, text=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=REPOSITORY_ROOT, check=True, capture_output=True, text=True).stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {"revision": "unknown", "dirty": True}
    return {"revision": revision, "dirty": dirty}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=REPOSITORY_ROOT / "reports" / "generated" / "successor-learner-timing-simulation-001")
    parser.add_argument("--smoke", action="store_true", help="tiny configuration for harness checks only")
    args = parser.parse_args()

    config = ProgramConfig()
    if args.smoke:
        config = ProgramConfig(seeds=(2000, 2001), development_seeds=(1000,), days=10, bootstrap_resamples=50)

    started = time.perf_counter()
    program = run_program(config)
    elapsed = time.perf_counter() - started
    program["summary"]["run"] = {
        "run_id": "successor-learner-timing-simulation-001" + ("-smoke" if args.smoke else ""),
        "code": _code_revision(),
        "elapsed_seconds": round(elapsed, 2),
        "network": "none",
        "provider_calls": 0,
    }
    write_outputs(program, args.output_dir)
    print(json.dumps(program["summary"]["run"], indent=2))
    print((args.output_dir / "summary.md").read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
