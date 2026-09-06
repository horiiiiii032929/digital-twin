"""Measure actual tutoring POSTs; callers own deployment, authority and credentials."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import math
import time
import uuid

import httpx


@dataclass(frozen=True)
class StudentProbeSession:
    client: httpx.AsyncClient
    conversation_id: str
    course_id: str
    release_id: str


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]


async def measure_tutoring_requests(
    sessions: list[StudentProbeSession], messages: list[str]
) -> dict:
    """One sequential conversation per client, concurrent students; no retries.

    Timing includes request transport and response parsing. No provider identity
    is inferred from HTTP success. Empty replies or mixed-release citations fail
    the contract, while pedagogical/factual correctness remains unscored.
    """
    if not sessions or not messages or any(not m.strip() for m in messages):
        raise ValueError("Nonempty sessions and messages are required")
    if len({s.conversation_id for s in sessions}) != len(sessions):
        raise ValueError("Each student must have an independent conversation")
    active = maximum_active = 0
    nonce = uuid.uuid4().hex
    started = time.perf_counter()

    async def student(index: int, session: StudentProbeSession) -> list[dict]:
        nonlocal active, maximum_active
        rows = []
        for turn, message in enumerate(messages):
            row = {"student_index": index, "turn": turn, "ok": False}
            begin = time.perf_counter()
            active += 1
            maximum_active = max(maximum_active, active)
            try:
                response = await session.client.post(
                    f"/api/student/conversations/{session.conversation_id}/messages",
                    json={"content": message, "request_id": f"capacity-{nonce}-{index}-{turn}"},
                )
                row["http_status"] = response.status_code
                response.raise_for_status()
                data = response.json()
                tutor = data["tutor_message"]
                if not isinstance(tutor["content"], str) or not tutor["content"].strip():
                    raise ValueError("empty-response")
                if tutor["conversation_id"] != session.conversation_id:
                    raise ValueError("conversation-mismatch")
                citations = data["citations"]
                if not isinstance(citations, list) or any(
                    c["course_id"] != session.course_id or c["release_id"] != session.release_id
                    for c in citations
                ):
                    raise ValueError("citation-scope-mismatch")
                row.update(ok=True, action=tutor["action"], citation_count=len(citations))
            except Exception as error:
                # Never include response/request text or credential-bearing error strings.
                row["failure_class"] = type(error).__name__
            finally:
                active -= 1
                row["latency_ms"] = (time.perf_counter() - begin) * 1000
                rows.append(row)
        return rows

    groups = await asyncio.gather(*(student(i, session) for i, session in enumerate(sessions)))
    rows = [row for group in groups for row in group]
    successes = [row["latency_ms"] for row in rows if row["ok"]]
    failures = sum(not row["ok"] for row in rows)
    return {"scope": "full tutoring-message HTTP requests", "requests": rows,
        "student_count": len(sessions), "turns_per_student": len(messages),
        "maximum_client_requests_in_flight": maximum_active,
        "elapsed_seconds": time.perf_counter() - started,
        "request_count": len(rows), "failure_count": failures,
        "failure_fraction": failures / len(rows),
        "successful_response_p50_ms": percentile(successes, 0.5),
        "successful_response_p95_ms": percentile(successes, 0.95),
        "all_request_p95_ms": percentile([r["latency_ms"] for r in rows], 0.95),
        "quality_pass": None, "deployment_qualified": False}
