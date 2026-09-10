"""Compare diagnostics-only audit behavior against an explicit deployed source file."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

from src.digital_twin.generation import final_response_audit as candidate
from src.digital_twin.llm import LlmUnavailableError
from tests import test_final_response_audit as fixtures


async def run(control_path: Path) -> dict:
    name = 'src.digital_twin.generation._slide_codefix_control'
    spec = importlib.util.spec_from_file_location(name, control_path)
    control = importlib.util.module_from_spec(spec)
    sys.modules[name] = control
    spec.loader.exec_module(control)
    cases = [(name, {"mutation": getattr(fixtures, name)}) for name in (
        'missing', 'duplicate', 'hash_wrong', 'proposal_wrong', 'context_wrong',
        'source_wrong', 'source_empty', 'bypass', 'extra', 'dimensions_missing',
        'affected_wrong')]
    cases += [('valid', {}), ('repair', {'rejects': {1}}),
              ('unchanged', {'rejects': {1}}), ('reject_repair', {'rejects': {1, 2}}),
              ('unknown_usage', {'known': False}), ('identity', {'model': 'wrong'}),
              ('unavailable', {'error': LlmUnavailableError('PRIVATE_SENTINEL')})]
    rows = []
    for case, options in cases:
        runs = []
        for module in (control, candidate):
            payload, raw, render = fixtures.fixture()
            audit = fixtures.Audit(**options)
            repair = fixtures.Repair(same=case == 'unchanged')
            start = time.perf_counter()
            result = await module.audit_final_response(proposal_json=raw,
                payload=payload, render=render, audit_client=audit,
                repair_client=repair, mode='quality')
            record = result.to_dict()
            diagnostics = {key: record.pop(key, None) for key in ('failure_stage', 'failure_code', 'failure_fields')}
            runs.append((record, diagnostics, (time.perf_counter() - start) * 1000))
        old, new = runs
        rows.append({'case': case, 'identical_behavior_requests_usage': old[0] == new[0],
            'outcome': new[0]['outcome'], 'calls': new[0]['calls'],
            'usage': new[0]['usage'], 'diagnostics': new[1],
            'control_latency_ms': old[2], 'candidate_latency_ms': new[2]})
    return {'run_id': 'slide-codefix-001', 'dataset': 'slide-aligned-codefix-v1',
        'code_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'dirty': True, 'control_sha256': hashlib.sha256(control_path.read_bytes()).hexdigest(),
        'candidate_sha256': hashlib.sha256(Path(candidate.__file__).read_bytes()).hexdigest(),
        'provider_calls': 0, 'provider_cost_usd': 0,
        'scope': 'synthetic deterministic contract comparison; injected usage is not provider billing',
        'cases': rows, 'all_behavior_identical': all(r['identical_behavior_requests_usage'] for r in rows)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--control', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run-id', default='slide-codefix-001')
    parser.add_argument('--dataset', default='slide-aligned-codefix-v1')
    args = parser.parse_args()
    record = asyncio.run(run(args.control))
    record["run_id"] = args.run_id
    record["dataset"] = args.dataset
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'cases': len(record['cases']), 'all_behavior_identical': record['all_behavior_identical']}))
    raise SystemExit(0 if record['all_behavior_identical'] else 1)
