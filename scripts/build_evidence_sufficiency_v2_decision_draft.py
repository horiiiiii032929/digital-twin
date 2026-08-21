#!/usr/bin/env python3
"""Build the deterministic synthetic-public v2 decision-set draft."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from typing import Any

from src.digital_twin.repository_freeze import (
    require_pre_evaluation_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    ROOT
    / "research/05_evaluation/drafts/evidence_sufficiency_v2_decision_draft_001.json"
)
DATASET_ID = "evidence-sufficiency-v2-decision-draft-001"
VERSIONED_SOURCE_INDEXES = {1, 2, 6, 7, 11, 12, 16, 17, 21, 26}
EXPECTED_SLICE_COUNTS = {
    "ambiguous": 10,
    "cross-course": 10,
    "direct": 15,
    "multi-evidence": 15,
    "multimodal": 10,
    "near-domain": 20,
    "no-evidence": 15,
    "paraphrase": 15,
    "permission-version": 10,
}


SOURCE_SPECS = (
    ("secure-web", "sessions", "text", "A session identifier must be rotated immediately after authentication to prevent session fixation.", "When must a session identifier be rotated?", "What should happen to the browser session ID as soon as login succeeds?", "A password reset must revoke every active session for the account.", "What must a password reset do to active sessions?", "After a user changes a compromised password, what happens to devices already signed in?"),
    ("secure-web", "cookies", "table", "The Secure cookie flag restricts transmission to HTTPS connections.", "What transport restriction does the Secure cookie flag impose?", "Which cookie setting prevents transmission over an unencrypted connection?", "The HttpOnly cookie flag prevents browser scripts from reading the cookie.", "What does the HttpOnly cookie flag prevent?", "Which setting keeps JavaScript from reading an authentication cookie?"),
    ("secure-web", "xss", "code", "Untrusted text must be inserted with textContent rather than interpreted as HTML.", "How must untrusted text be inserted into a page?", "Which DOM operation treats user input as text instead of markup?", "Output encoding must match the destination context such as HTML, attributes, CSS, or URLs.", "How must output encoding be selected?", "Why is one universal escaping function insufficient for every browser context?"),
    ("secure-web", "oauth", "diagram", "The OAuth state value binds the authorization response to the browser flow that initiated it.", "What does the OAuth state value bind?", "Which value links a login callback to the browser that started authorization?", "A redirect URI must be matched exactly against the registered allowlist.", "How must an OAuth redirect URI be validated?", "What comparison is required before accepting an authorization callback destination?"),
    ("secure-web", "authorization", "text", "Authorization must be checked for the specific requested object on every request.", "Where must object authorization be checked?", "Is a general logged-in check enough before returning a requested record?", "A denied authorization decision must not reveal whether the protected object exists.", "What information must an authorization denial avoid revealing?", "How should an access denial avoid leaking the existence of a private record?"),
    ("database", "transactions", "text", "A transaction commits all of its changes together or rolls all of them back.", "What atomicity rule applies to transaction changes?", "What happens if only part of a database operation can succeed?", "A durable commit must survive a process restart after success is acknowledged.", "What must be true after a durable commit is acknowledged?", "Should acknowledged data remain after the database process restarts?"),
    ("database", "indexes", "diagram", "A B-tree index supports ordered range scans without reading every table row.", "What query pattern does a B-tree index support?", "Which index structure can serve an ordered range query efficiently?", "An index can slow writes because each affected index entry must also be maintained.", "Why can adding an index reduce write throughput?", "What extra work does an insert perform when several indexes exist?"),
    ("database", "isolation", "table", "Serializable isolation prevents executions that cannot be ordered as serial transactions.", "What does serializable isolation prevent?", "Which isolation level rejects outcomes that have no serial ordering?", "Snapshot isolation can still permit write-skew anomalies across related rows.", "Which anomaly can remain under snapshot isolation?", "Why can two individually valid snapshot transactions violate a cross-row invariant?"),
    ("database", "replication", "diagram", "Synchronous replication waits for the required replica acknowledgement before confirming a write.", "When does synchronous replication confirm a write?", "What acknowledgement is required before a synchronous write returns success?", "Asynchronous replication can lose recently acknowledged writes during primary failure.", "What loss risk accompanies asynchronous replication?", "Which acknowledged updates may disappear when a primary fails before replicas catch up?"),
    ("database", "recovery", "text", "Write-ahead log records must reach durable storage before their corresponding data pages.", "What ordering does write-ahead logging require?", "Which must become durable first: the log record or the changed data page?", "A recovery checkpoint limits how far the log must be replayed after restart.", "What is the purpose of a recovery checkpoint?", "How does a checkpoint reduce restart recovery work?"),
    ("machine-learning", "splits", "table", "The test split must remain untouched until the final model decision.", "When may the test split be used?", "Which data partition must stay sealed during model tuning?", "Hyperparameters are selected using development or validation data rather than test outcomes.", "Which data should drive hyperparameter selection?", "Where should threshold tuning occur before the final test?"),
    ("machine-learning", "metrics", "equation", "Precision is the fraction of predicted positives that are truly positive.", "What does precision measure?", "Among items predicted positive, which fraction does precision count?", "Recall is the fraction of true positives that the model retrieves.", "What does recall measure?", "Among all truly positive items, which fraction does recall count?"),
    ("machine-learning", "regularization", "equation", "L2 regularization adds a penalty proportional to squared parameter magnitude.", "What penalty does L2 regularization add?", "How does weight decay discourage large model parameters?", "Regularization strength must be selected on development data rather than the final test set.", "Where must regularization strength be selected?", "Which split should determine the weight-decay coefficient?"),
    ("machine-learning", "calibration", "diagram", "A calibrated 0.8 probability should be correct on about 80 percent of comparable predictions.", "What does a calibrated probability of 0.8 mean?", "How often should similarly scored 0.8 predictions be correct?", "Calibration quality must be reported separately from ranking discrimination.", "How must calibration and ranking quality be reported?", "Why does a strong ranking metric not prove reliable probabilities?"),
    ("machine-learning", "embeddings", "code", "Document and query embeddings must use the model instructions required for their distinct roles.", "How must document and query embeddings handle role instructions?", "Why can the same raw prefix be wrong for both passages and questions?", "Embedding similarity ranks candidates but is not a calibrated answerability probability.", "What can embedding similarity establish?", "Does a high cosine similarity alone prove that evidence is sufficient to answer?"),
    ("human-computer-interaction", "usability", "text", "A usability test observes representative users attempting representative tasks.", "What does a usability test observe?", "Who should attempt which tasks during a usability study?", "Task completion and observed breakdowns must be recorded separately from user preference.", "How must task performance and preference be recorded?", "Why is liking an interface not the same as completing its workflow?"),
    ("human-computer-interaction", "accessibility", "table", "Keyboard focus must remain visible and follow the same logical order as the interface.", "What requirements apply to keyboard focus?", "How should focus visibility and order behave for keyboard users?", "Text and essential controls must satisfy the declared contrast requirement in every state.", "When must contrast requirements hold?", "Do hover, disabled, and error states also need adequate contrast?"),
    ("human-computer-interaction", "feedback", "diagram", "A system must acknowledge a user action promptly even when completion is asynchronous.", "When must a system acknowledge a user action?", "What feedback is needed while a long-running operation continues?", "An error message must state what happened and provide a recoverable next action.", "What information must an error message provide?", "How should an error help a user continue rather than merely report failure?"),
    ("human-computer-interaction", "cognitive-load", "text", "Progressive disclosure keeps advanced controls hidden until they are relevant.", "What does progressive disclosure do?", "When should advanced controls become visible?", "A workflow should not require users to remember information that the interface can display.", "What memory burden should an interface avoid?", "Why should prior values remain visible during a multi-step task?"),
    ("human-computer-interaction", "research", "table", "Interview notes must distinguish direct observations from researcher interpretation.", "How must interview notes separate evidence and interpretation?", "Which statements are observations and which are analyst inferences?", "A research claim must identify the participant scope and tasks that support it.", "What scope must accompany a user-research claim?", "Why should a finding name the participants and tasks behind it?"),
    ("distributed-systems", "consistency", "text", "Linearizability requires each completed operation to appear at one instant between invocation and response.", "What ordering does linearizability require?", "Where may a completed operation appear in a linearizable history?", "Eventual consistency allows replicas to diverge temporarily when no new updates occur.", "What temporary state does eventual consistency allow?", "Can replicas return different values before updates have converged?"),
    ("distributed-systems", "replication", "diagram", "A quorum read and write configuration must overlap on at least one replica.", "What overlap must quorum reads and writes provide?", "Why must the selected read and write replica sets intersect?", "A replication factor counts stored copies, not the number of failures automatically tolerated.", "What does replication factor count?", "Why does three replicas not by itself prove tolerance of any two failures?"),
    ("distributed-systems", "consensus", "diagram", "A consensus leader must step down when it observes a term higher than its own.", "When must a consensus leader step down?", "What should a leader do after receiving a message from a newer term?", "A committed log entry must be preserved by future leaders.", "What must happen to a committed log entry across leader changes?", "May a newly elected leader discard an entry that was already committed?"),
    ("distributed-systems", "failure", "table", "A timeout indicates missing timely evidence, not proof that a remote process has stopped.", "What does a timeout establish?", "Does a missed response prove that the remote process crashed?", "Retries require idempotency or deduplication because a timed-out operation may have completed.", "Why must retried operations be idempotent or deduplicated?", "What uncertainty remains after a client times out waiting for a write?"),
    ("distributed-systems", "time", "equation", "A monotonic clock measures elapsed duration without moving backward after wall-clock adjustment.", "What property makes a monotonic clock suitable for elapsed time?", "Which clock should measure a timeout when wall time may be corrected?", "Wall-clock timestamps require an explicit timezone and synchronization assumptions.", "What must accompany wall-clock timestamps?", "Why is an unlabeled local timestamp insufficient for distributed event comparison?"),
    ("software-testing", "unit", "code", "A unit test isolates one behavior and controls external dependencies.", "What does a unit test isolate?", "How should a small test handle network or database dependencies?", "A deterministic test must produce the same assertion result from the same controlled inputs.", "What makes a test deterministic?", "What outcome should repeated runs have when their controlled inputs do not change?"),
    ("software-testing", "integration", "diagram", "An integration test verifies a contract across real component boundaries.", "What does an integration test verify?", "When should a test use the actual persistence or transport adapter?", "Integration fixtures must be isolated so one test cannot depend on another test state.", "How must integration fixtures be isolated?", "Why should test order not affect an integration result?"),
    ("software-testing", "property", "equation", "A property test generates many inputs and checks an invariant rather than one example output.", "What does a property test check?", "How does property-based testing differ from a single example assertion?", "A failing generated case must be preserved with its seed or minimized counterexample.", "What must be retained for a failing property test?", "How can a generated failure be reproduced after the original run?"),
    ("software-testing", "mutation", "code", "Mutation testing checks whether tests fail after a deliberate fault is inserted.", "What does mutation testing check?", "What should happen when a deliberate implementation defect is introduced?", "A surviving mutation indicates missing sensitivity but does not identify the correct replacement assertion.", "What does a surviving mutation indicate?", "Does mutation survival automatically tell us which assertion to add?"),
    ("software-testing", "observability", "table", "A test failure record must include the case identity, stage, and sanitized failure category.", "What must a test failure record include?", "Which identifiers make an automated evaluation failure traceable?", "Operational latency must report a distribution such as p50 and p95 rather than only a mean.", "How must operational latency be reported?", "Why is an average alone insufficient for tail-latency qualification?"),
)


NEAR_DOMAIN_NEGATIVES = (
    ("secure-web", "sessions", "How long should a physical-training session last?", "session vocabulary refers to exercise rather than browser authentication"),
    ("database", "transactions", "What isolation period applies to an apartment escrow transaction?", "transaction and isolation vocabulary refers to real estate"),
    ("machine-learning", "calibration", "How should calibration adjust a laboratory pressure instrument?", "calibration refers to a physical instrument"),
    ("human-computer-interaction", "accessibility", "Which accessibility standard applies to a public building ramp?", "accessibility refers to a physical building rather than an interface"),
    ("distributed-systems", "consensus", "Which consensus method should a focus group use to choose a logo?", "consensus refers to a human group decision"),
)


NO_EVIDENCE_QUESTIONS = (
    "What interest-rate target did the central bank announce?",
    "Which antibiotic is recommended for a bacterial infection?",
    "How many grams of flour are required for the cake recipe?",
    "What is the train schedule between the two cities?",
    "Which tax form reports foreign dividend income?",
    "What is the tensile strength of the bridge cable?",
    "Who won the most recent football championship?",
    "What temperature will it reach tomorrow afternoon?",
    "Which chord progression opens the jazz recording?",
    "How should the apartment lease allocate utility costs?",
    "What fertilizer ratio is appropriate for tomato plants?",
    "Which museum currently displays the sculpture?",
    "How does the telescope correct atmospheric distortion?",
    "What dosage is printed on the medicine label?",
    "Which customs code applies to the imported furniture?",
)


class DecisionDraftError(ValueError):
    """Raised when deterministic decision-set construction drifts."""


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", value))


def _sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _stratified_sample(
    items: list[dict[str, Any]],
    count: int,
    *,
    offset: int = 0,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        grouped.setdefault(item["course_id"], []).append(item)
    course_ids = sorted(grouped)
    positions = {course_id: 0 for course_id in course_ids}
    selected: list[dict[str, Any]] = []
    for index in range(count):
        course_id = course_ids[(index + offset) % len(course_ids)]
        bucket = grouped[course_id]
        selected.append(bucket[positions[course_id] % len(bucket)])
        positions[course_id] += 1
    return selected


def _build_sources() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sources: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    for source_index, spec in enumerate(SOURCE_SPECS, start=1):
        (
            course_id,
            topic,
            modality,
            statement_1,
            question_1,
            paraphrase_1,
            statement_2,
            question_2,
            paraphrase_2,
        ) = spec
        logical_id = f"{course_id}-{topic}"
        source_id = f"{logical_id}-v2"
        source_claims = []
        for claim_number, (statement, question, paraphrase) in enumerate(
            (
                (statement_1, question_1, paraphrase_1),
                (statement_2, question_2, paraphrase_2),
            ),
            start=1,
        ):
            claim = {
                "claim_id": f"{logical_id}-claim-{claim_number}",
                "source_unit_id": source_id,
                "course_id": course_id,
                "modality": modality,
                "statement": statement,
                "evidence_quote": statement,
                "direct_question": question,
                "paraphrase_question": paraphrase,
            }
            source_claims.append(claim)
            claims.append(claim)
        sources.append(
            {
                "source_unit_id": source_id,
                "logical_source_id": logical_id,
                "course_id": course_id,
                "topic": topic,
                "version": 2,
                "active": True,
                "tutoring_allowed": True,
                "modality": modality,
                "content": " ".join(claim["statement"] for claim in source_claims),
                "claims": [
                    {
                        "claim_id": claim["claim_id"],
                        "statement": claim["statement"],
                        "evidence_quote": claim["evidence_quote"],
                    }
                    for claim in source_claims
                ],
            }
        )
        if source_index in VERSIONED_SOURCE_INDEXES:
            sources.append(
                {
                    "source_unit_id": f"{logical_id}-v1",
                    "logical_source_id": logical_id,
                    "course_id": course_id,
                    "topic": topic,
                    "version": 1,
                    "active": False,
                    "tutoring_allowed": True,
                    "modality": modality,
                    "content": (
                        f"Superseded guidance for {topic} uses a different rule and "
                        "must not support a current answer."
                    ),
                    "claims": [],
                }
            )
    return sources, claims


def _answer_case(
    case_id: str,
    slice_name: str,
    question: str,
    selected_claims: list[dict[str, Any]],
) -> dict[str, Any]:
    course_ids = {claim["course_id"] for claim in selected_claims}
    if len(course_ids) != 1:
        raise DecisionDraftError("answer case crosses course boundaries")
    return {
        "case_id": case_id,
        "slice": slice_name,
        "course_id": next(iter(course_ids)),
        "question": question,
        "expected_action": "answer",
        "required_claims": [
            {"claim_id": claim["claim_id"], "statement": claim["statement"]}
            for claim in selected_claims
        ],
        "evidence": [
            {
                "source_unit_id": claim["source_unit_id"],
                "claim_id": claim["claim_id"],
                "quote": claim["evidence_quote"],
            }
            for claim in selected_claims
        ],
        "boundary_reason": None,
        "tempting_source_ids": [],
        "review_status": "pending-independent-review",
    }


def _abstain_case(
    case_id: str,
    slice_name: str,
    course_id: str,
    question: str,
    boundary_reason: str,
    *,
    tempting_source_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "slice": slice_name,
        "course_id": course_id,
        "question": question,
        "expected_action": "abstain",
        "required_claims": [],
        "evidence": [],
        "boundary_reason": boundary_reason,
        "tempting_source_ids": tempting_source_ids or [],
        "review_status": "pending-independent-review",
    }


def build_draft() -> dict[str, Any]:
    sources, claims = _build_sources()
    cases: list[dict[str, Any]] = []
    active_sources = [source for source in sources if source["active"]]
    claims_by_source = {
        source["source_unit_id"]: [
            claim for claim in claims if claim["source_unit_id"] == source["source_unit_id"]
        ]
        for source in active_sources
    }

    for index, claim in enumerate(_stratified_sample(claims, 15), start=1):
        cases.append(
            _answer_case(
                f"esv2-direct-{index:02d}",
                "direct",
                claim["direct_question"],
                [claim],
            )
        )
    for index, claim in enumerate(
        _stratified_sample(claims, 15, offset=3),
        start=1,
    ):
        cases.append(
            _answer_case(
                f"esv2-paraphrase-{index:02d}",
                "paraphrase",
                claim["paraphrase_question"],
                [claim],
            )
        )
    for index, source in enumerate(_stratified_sample(active_sources, 15), start=1):
        first, second = claims_by_source[source["source_unit_id"]]
        cases.append(
            _answer_case(
                f"esv2-multi-{index:02d}",
                "multi-evidence",
                (
                    f"Answer both parts from the approved {first['course_id']} "
                    f"materials: {first['direct_question'].rstrip('?')}; and "
                    f"{second['direct_question'][0].lower()}"
                    f"{second['direct_question'][1:]}"
                ),
                [first, second],
            )
        )

    versioned_logical_ids = {
        source["logical_source_id"] for source in sources if not source["active"]
    }
    permission_claims = [
        claims_by_source[source["source_unit_id"]][0]
        for source in active_sources
        if source["logical_source_id"] in versioned_logical_ids
    ]
    for index, claim in enumerate(permission_claims, start=1):
        cases.append(
            _answer_case(
                f"esv2-permission-{index:02d}",
                "permission-version",
                (
                    "Using only the current approved source version, "
                    f"{claim['direct_question'][0].lower()}"
                    f"{claim['direct_question'][1:]}"
                ),
                [claim],
            )
        )

    multimodal_claims = _stratified_sample(
        [claim for claim in claims if claim["modality"] != "text"],
        10,
    )
    for index, claim in enumerate(multimodal_claims, start=1):
        cases.append(
            _answer_case(
                f"esv2-multimodal-{index:02d}",
                "multimodal",
                (
                    f"From the approved {claim['modality']} evidence, "
                    f"{claim['paraphrase_question'][0].lower()}"
                    f"{claim['paraphrase_question'][1:]}"
                ),
                [claim],
            )
        )

    for index, claim in enumerate(
        _stratified_sample(claims, 15, offset=2),
        start=1,
    ):
        cases.append(
            _answer_case(
                f"esv2-near-answer-{index:02d}",
                "near-domain",
                (
                    f"Within {claim['course_id']} rather than an unrelated domain, "
                    f"{claim['paraphrase_question'][0].lower()}"
                    f"{claim['paraphrase_question'][1:]}"
                ),
                [claim],
            )
        )

    source_by_course: dict[str, list[dict[str, Any]]] = {}
    for source in sources:
        if source["active"]:
            source_by_course.setdefault(source["course_id"], []).append(source)
    for index in range(10):
        course_id = sorted(source_by_course)[index % len(source_by_course)]
        members = source_by_course[course_id]
        first = members[index % len(members)]
        second = members[(index + 1) % len(members)]
        cases.append(
            _abstain_case(
                f"esv2-ambiguous-{index + 1:02d}",
                "ambiguous",
                course_id,
                (
                    f"Within {course_id}, which current rule applies here: "
                    f"the {first['topic']} control or the {second['topic']} control?"
                ),
                "multiple-in-scope-interpretations-not-resolved-by-question",
                tempting_source_ids=[first["source_unit_id"], second["source_unit_id"]],
            )
        )

    courses = sorted(source_by_course)
    for index in range(10):
        course_id = courses[index % len(courses)]
        local_topics = {source["topic"] for source in source_by_course[course_id]}
        foreign_sources = [
            source
            for candidate_course in courses
            if candidate_course != course_id
            for source in source_by_course[candidate_course]
            if source["topic"] not in local_topics
        ]
        foreign_source = foreign_sources[index % len(foreign_sources)]
        cases.append(
            _abstain_case(
                f"esv2-cross-{index + 1:02d}",
                "cross-course",
                course_id,
                (
                    f"For this {course_id} course, what rule applies to "
                    f"{foreign_source['topic']}?"
                ),
                "tempting-evidence-exists-only-outside-course-boundary",
                tempting_source_ids=[foreign_source["source_unit_id"]],
            )
        )

    for index, (course_id, topic, question, reason) in enumerate(
        NEAR_DOMAIN_NEGATIVES,
        start=1,
    ):
        tempting_source = next(
            source
            for source in source_by_course[course_id]
            if source["topic"] == topic
        )
        cases.append(
            _abstain_case(
                f"esv2-near-abstain-{index:02d}",
                "near-domain",
                course_id,
                question,
                reason,
                tempting_source_ids=[tempting_source["source_unit_id"]],
            )
        )

    for index, question in enumerate(NO_EVIDENCE_QUESTIONS, start=1):
        course_id = courses[(index - 1) % len(courses)]
        cases.append(
            _abstain_case(
                f"esv2-none-{index:02d}",
                "no-evidence",
                course_id,
                question,
                "approved-course-corpus-contains-no-supporting-evidence",
            )
        )

    priority_ids = [
        *(f"esv2-near-abstain-{index:02d}" for index in range(1, 6)),
        *(f"esv2-ambiguous-{index:02d}" for index in range(1, 4)),
        *(f"esv2-cross-{index:02d}" for index in range(1, 3)),
        *(f"esv2-permission-{index:02d}" for index in range(1, 3)),
    ]
    core = {
        "schema_version": 1,
        "dataset_id": DATASET_ID,
        "status": "draft-pending-independent-review",
        "synthetic_public_only": True,
        "private_data_read": False,
        "provider_or_model_calls": 0,
        "ground_truth_authority": "deterministic-source-linked",
        "decision_execution_authorized": False,
        "opened_for_candidate_evaluation": False,
        "sources": sources,
        "cases": cases,
        "priority_review_case_ids": priority_ids,
        "review": {
            "structural_review": "pending",
            "independent_advisory_review": "pending",
            "human_priority_review": "pending",
            "freeze_eligible": False,
        },
    }
    validate_draft(core)
    return {**core, "content_sha256": _sha256(core)}


def validate_draft(payload: dict[str, Any]) -> dict[str, Any]:
    sources = payload.get("sources", [])
    cases = payload.get("cases", [])
    if len(cases) != 120:
        raise DecisionDraftError("decision draft must contain exactly 120 cases")
    if len({case["case_id"] for case in cases}) != len(cases):
        raise DecisionDraftError("case IDs must be unique")
    questions = [_normalize(case["question"]) for case in cases]
    if len(set(questions)) != len(questions):
        raise DecisionDraftError("normalized questions must be unique")
    if Counter(case["slice"] for case in cases) != Counter(EXPECTED_SLICE_COUNTS):
        raise DecisionDraftError("slice distribution drifted")
    if Counter(case["expected_action"] for case in cases) != Counter(
        {"answer": 80, "abstain": 40}
    ):
        raise DecisionDraftError("action distribution drifted")
    source_map = {source["source_unit_id"]: source for source in sources}
    if len(source_map) != len(sources):
        raise DecisionDraftError("source IDs must be unique")
    active_by_logical = Counter(
        source["logical_source_id"] for source in sources if source["active"]
    )
    if any(count != 1 for count in active_by_logical.values()):
        raise DecisionDraftError("each logical source requires one active version")
    claim_map = {
        claim["claim_id"]: (source, claim)
        for source in sources
        for claim in source["claims"]
    }
    for case in cases:
        if case["review_status"] != "pending-independent-review":
            raise DecisionDraftError("draft review status drifted")
        if case["expected_action"] == "abstain":
            if case["required_claims"] or case["evidence"]:
                raise DecisionDraftError("abstain case contains authoritative lineage")
            if not case["boundary_reason"]:
                raise DecisionDraftError("abstain case lacks a boundary reason")
        else:
            if case["boundary_reason"] is not None:
                raise DecisionDraftError("answer case has a boundary reason")
            if not case["required_claims"] or not case["evidence"]:
                raise DecisionDraftError("answer case lacks source-linked truth")
            if len(case["required_claims"]) != len(case["evidence"]):
                raise DecisionDraftError("claim/evidence cardinality drifted")
            for required, evidence in zip(
                case["required_claims"],
                case["evidence"],
                strict=True,
            ):
                source, claim = claim_map[evidence["claim_id"]]
                if not source["active"] or not source["tutoring_allowed"]:
                    raise DecisionDraftError("answer cites an ineligible source")
                if evidence["source_unit_id"] != source["source_unit_id"]:
                    raise DecisionDraftError("evidence source binding drifted")
                if required["claim_id"] != claim["claim_id"]:
                    raise DecisionDraftError("required claim binding drifted")
                if required["statement"] != claim["statement"]:
                    raise DecisionDraftError("required claim text drifted")
                if evidence["quote"] != claim["evidence_quote"]:
                    raise DecisionDraftError("evidence quote is not exact")
                if case["course_id"] != source["course_id"]:
                    raise DecisionDraftError("answer crosses course boundary")
        if any(source_id not in source_map for source_id in case["tempting_source_ids"]):
            raise DecisionDraftError("case references an unknown tempting source")
    priority = payload.get("priority_review_case_ids", [])
    if len(priority) != 12 or not set(priority).issubset(
        {case["case_id"] for case in cases}
    ):
        raise DecisionDraftError("priority review packet must contain 12 valid cases")
    return {
        "dataset_id": payload["dataset_id"],
        "status": payload["status"],
        "source_count": len(sources),
        "case_count": len(cases),
        "action_counts": dict(sorted(Counter(case["expected_action"] for case in cases).items())),
        "slice_counts": dict(sorted(Counter(case["slice"] for case in cases).items())),
        "priority_review_case_count": len(priority),
        "provider_or_model_calls": payload["provider_or_model_calls"],
        "private_data_read": payload["private_data_read"],
        "opened_for_candidate_evaluation": payload["opened_for_candidate_evaluation"],
    }


def load_and_validate_draft(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    content_sha256 = payload.pop("content_sha256", None)
    if content_sha256 != _sha256(payload):
        raise DecisionDraftError("decision draft content hash drifted")
    summary = validate_draft(payload)
    return {**summary, "content_sha256": content_sha256}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    if arguments.write:
        require_pre_evaluation_operation_allowed("dataset_generation")
    if arguments.check:
        summary = load_and_validate_draft(arguments.output)
    else:
        payload = build_draft()
        summary = {
            **validate_draft({
                key: value for key, value in payload.items() if key != "content_sha256"
            }),
            "content_sha256": payload["content_sha256"],
        }
        if arguments.write:
            arguments.output.parent.mkdir(parents=True, exist_ok=True)
            arguments.output.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
