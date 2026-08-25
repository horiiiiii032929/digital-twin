"""Deterministic synthetic-public development data for academic E2E QA.

The records in this module exercise the product and evaluation harness. They are
not independently annotated gold evidence and must never be reported as such.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from typing import Any


DATASET_ID = "academic-factual-qa-end-to-end-pilot-001-development"


COURSES: tuple[dict[str, Any], ...] = (
    {
        "course_id": "pilot-systems",
        "title": "Computer Systems",
        "sources": (
            ("mesi", "MESI invalidates other cached copies before a core writes a shared line.", "Invalidation prevents two cores from silently keeping conflicting writable copies.", "What must MESI do before a core writes a shared cache line?", "How does MESI prepare a shared line for a processor write?"),
            ("tlb", "A translation lookaside buffer caches recent virtual-to-physical address translations.", "A TLB hit avoids another page-table walk for that translation.", "What information does a translation lookaside buffer cache?", "Why can a TLB hit avoid a page-table walk?"),
            ("deadlock", "Deadlock requires mutual exclusion, hold-and-wait, no preemption, and circular wait to hold together.", "Breaking any one of these Coffman conditions prevents the complete deadlock condition set.", "Which four conditions must hold together for deadlock?", "How can breaking a Coffman condition prevent deadlock?"),
            ("wal", "A write-ahead log records a change durably before the corresponding data page is flushed.", "Recovery replays or rolls back log records after a crash.", "What ordering does a write-ahead log require?", "How does write-ahead logging support crash recovery?"),
        ),
        "absent": ("GPU warp scheduling", "NUMA page migration", "RAID parity rotation"),
    },
    {
        "course_id": "pilot-security",
        "title": "Web Security",
        "sources": (
            ("csrf", "A CSRF attack makes an authenticated browser send an unintended state-changing request.", "Anti-CSRF tokens bind the request to a value the attacker cannot read from another origin.", "What does a CSRF attack cause an authenticated browser to do?", "Why can an anti-CSRF token stop a cross-site request forgery?"),
            ("csp", "Content Security Policy restricts the origins from which a page may load executable content.", "A nonce can authorize one intended inline script without allowing every inline script.", "What does Content Security Policy restrict?", "How can a CSP nonce permit one intended inline script?"),
            ("passwords", "A unique password salt prevents equal passwords from producing identical stored hashes.", "A slow password hash raises the cost of each offline guessing attempt.", "Why is a unique salt stored with each password hash?", "How does a slow password hash affect offline guessing?"),
            ("privilege", "Least privilege gives a component only the permissions required for its current task.", "Reducing permissions limits the damage available after compromise.", "What does the principle of least privilege require?", "Why does reducing component permissions limit compromise impact?"),
        ),
        "absent": ("post-quantum signatures", "wireless deauthentication", "hardware enclaves"),
    },
    {
        "course_id": "pilot-data",
        "title": "Data Management",
        "sources": (
            ("normalization", "Third normal form removes transitive dependencies of non-key attributes on a key.", "The decomposition reduces update anomalies while preserving the intended facts.", "What dependency does third normal form remove?", "Why can a 3NF decomposition reduce update anomalies?"),
            ("index", "A database index trades additional storage and write maintenance for faster qualifying reads.", "The optimizer may skip an index when a scan is estimated to be cheaper.", "What trade-off does a database index introduce?", "Why might an optimizer choose a table scan instead of an index?"),
            ("serializable", "Serializable isolation requires concurrent transactions to have an outcome equivalent to some serial order.", "It prevents anomalies that cannot occur under any serial execution.", "What outcome must serializable isolation guarantee?", "Which anomalies does serializable execution rule out?"),
            ("star", "A star schema connects a central fact table to denormalized dimension tables.", "The dimensions provide descriptive attributes for slicing measures in the fact table.", "How are tables arranged in a star schema?", "What role do dimension tables play in a star schema?"),
        ),
        "absent": ("stream watermarking", "graph community detection", "columnar dictionary encoding"),
    },
    {
        "course_id": "pilot-networks",
        "title": "Computer Networks",
        "sources": (
            ("tcp", "TCP sequence numbers identify byte positions so the receiver can reorder data and detect gaps.", "Acknowledgements report the next byte the receiver expects.", "What do TCP sequence numbers identify?", "What does a TCP acknowledgement number report?"),
            ("dns", "A DNS time-to-live value limits how long a resolver may cache a record.", "Shorter TTLs propagate changes faster but increase lookup traffic.", "What does a DNS TTL limit?", "What trade-off comes with shortening a DNS TTL?"),
            ("routing", "Longest-prefix matching selects the routing-table entry with the most specific matching network prefix.", "A default route is used only when no more specific entry matches.", "How does longest-prefix matching choose a route?", "When is a default route used?"),
            ("tls", "A TLS certificate binds a public key to an identity through a trusted signature chain.", "Hostname validation checks that the requested server name is covered by the certificate.", "What does a TLS certificate bind together?", "What does TLS hostname validation check?"),
        ),
        "absent": ("satellite handover", "Bluetooth frequency hopping", "MPLS traffic engineering"),
    },
    {
        "course_id": "pilot-ml",
        "title": "Machine Learning",
        "sources": (
            ("splits", "A validation set guides model and hyperparameter choices while the test set remains untouched for final estimation.", "Repeated test-set inspection leaks information into model selection.", "What separate purposes do validation and test sets serve?", "Why does repeated inspection of the test set bias evaluation?"),
            ("regularization", "L2 regularization penalizes large squared parameter values in the training objective.", "The penalty can reduce variance when the unregularized model overfits.", "What quantity does L2 regularization penalize?", "How can L2 regularization reduce overfitting?"),
            ("calibration", "A calibrated classifier assigns probabilities that match observed outcome frequencies over comparable predictions.", "Calibration and ranking quality measure different properties.", "What does probability calibration mean for a classifier?", "Why is classifier calibration different from ranking quality?"),
            ("leakage", "Data leakage occurs when training features contain information unavailable at the real prediction time.", "Leakage makes offline performance look better than deployable performance.", "When does feature data leakage occur?", "How does leakage distort an offline evaluation?"),
        ),
        "absent": ("federated secure aggregation", "diffusion guidance", "neural architecture search"),
    },
    {
        "course_id": "pilot-software",
        "title": "Software Engineering",
        "sources": (
            ("idempotency", "An idempotency key lets a server recognize retries of the same logical operation.", "The stored result prevents a duplicate side effect after a client timeout.", "What does an idempotency key let a server recognize?", "How can idempotency keys prevent duplicate side effects?"),
            ("semver", "Semantic versioning increments the major version for incompatible public API changes.", "Minor versions add backward-compatible functionality and patch versions add backward-compatible fixes.", "When does semantic versioning require a major-version increment?", "How do minor and patch releases differ under semantic versioning?"),
            ("circuit", "A circuit breaker stops repeated calls to a failing dependency after a threshold is crossed.", "A half-open probe determines whether normal calls may resume.", "What does a circuit breaker do after repeated dependency failures?", "What is the purpose of a half-open circuit-breaker probe?"),
            ("migration", "A backward-compatible database migration allows old and new application versions to run during rollout.", "Destructive cleanup is deferred until the old version is no longer serving traffic.", "Why should a rollout migration remain backward compatible?", "When should destructive database cleanup occur during a rollout?"),
        ),
        "absent": ("formal refinement proofs", "real-time garbage collection", "binary instrumentation"),
    },
    {
        "course_id": "pilot-hci",
        "title": "Human-Computer Interaction",
        "sources": (
            ("affordance", "A perceived affordance signals how a user believes an interface element can be used.", "Clear signifiers make the intended action discoverable.", "What does a perceived affordance communicate to a user?", "How do signifiers improve interface discoverability?"),
            ("contrast", "Sufficient visual contrast helps users distinguish text and controls from their background.", "Color should not be the only cue used to communicate important state.", "Why is sufficient visual contrast important?", "Why should an interface avoid using color as its only state cue?"),
            ("disclosure", "Progressive disclosure initially shows essential choices and reveals advanced options when needed.", "It reduces immediate complexity without permanently hiding capability.", "How does progressive disclosure organize interface choices?", "Why can progressive disclosure reduce perceived complexity?"),
            ("usability", "A usability test observes representative participants attempting realistic tasks with a product.", "Task success, errors, time, and participant comments provide complementary evidence.", "What happens during a usability test?", "Which kinds of evidence can a usability test collect?"),
        ),
        "absent": ("olfactory displays", "brain-computer interfaces", "haptic texture synthesis"),
    },
    {
        "course_id": "pilot-distributed",
        "title": "Distributed Systems",
        "sources": (
            ("quorum", "Read and write quorums intersect when their sizes sum to more than the replica count.", "The intersection lets a read observe at least one replica from the latest completed write quorum.", "When are read and write quorums guaranteed to intersect?", "Why does quorum intersection help a read observe a completed write?"),
            ("vector", "A vector clock tracks a separate logical counter for each participating process.", "Incomparable vector timestamps indicate concurrent events.", "What information does a vector clock track?", "What do incomparable vector-clock timestamps indicate?"),
            ("lease", "A lease grants time-bounded authority that expires unless it is renewed.", "Clock uncertainty must be included when deciding whether authority is still valid.", "What kind of authority does a lease grant?", "Why must lease logic account for clock uncertainty?"),
            ("consensus", "Majority-based consensus requires overlapping majorities so two conflicting values cannot both be chosen.", "A leader still needs quorum acknowledgement before treating a value as committed.", "Why do majorities overlap in a consensus protocol?", "What acknowledgement does a leader need before committing a value?"),
        ),
        "absent": ("gossip compression", "geo-fencing replicas", "erasure-coded repair"),
    },
)


def canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalize_question(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def build_development_dataset() -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    sequence = 0
    by_course: dict[str, list[dict[str, Any]]] = {}

    def add_case(**values: Any) -> None:
        nonlocal sequence
        sequence += 1
        cases.append(
            {
                "case_id": f"afe2e-dev-{sequence:03d}",
                "label_provenance": "deterministic-source-linked-development",
                "independently_validated": False,
                **values,
            }
        )

    for course in COURSES:
        course_sources: list[dict[str, Any]] = []
        for topic, claim, context, question, paraphrase in course["sources"]:
            source_id = f"{course['course_id']}-{topic}"
            source = {
                "source_id": source_id,
                "course_id": course["course_id"],
                "title": f"{course['title']}: {topic.replace('-', ' ').title()}",
                "version": 1,
                "text": f"{claim} {context}",
                "claims": [claim, context],
                "topic": topic,
            }
            sources.append(source)
            course_sources.append(source)
            for variant_index, (slice_name, wording, expected_claim) in enumerate(
                (
                    ("direct", question, claim),
                    ("paraphrase", paraphrase, context),
                ),
                start=1,
            ):
                add_case(
                    course_id=course["course_id"],
                    slice=slice_name,
                    question=wording,
                    expected_action="answer",
                    required_source_ids=[source_id],
                    expected_claims=[expected_claim],
                    cluster_id=source_id,
                    question_family_id=f"{source_id}-q{variant_index}",
                    rationale="The approved source directly states the expected claim.",
                )
        by_course[course["course_id"]] = course_sources

        for pair_index, (left, right) in enumerate(
            ((course_sources[0], course_sources[1]), (course_sources[2], course_sources[3])),
            start=1,
        ):
            add_case(
                course_id=course["course_id"],
                slice="multi-source",
                question=(
                    f"According to the approved {course['title']} notes, explain both "
                    f"{left['topic'].replace('-', ' ')} and {right['topic'].replace('-', ' ')}."
                ),
                expected_action="answer",
                required_source_ids=[left["source_id"], right["source_id"]],
                expected_claims=[left["claims"][0], right["claims"][0]],
                cluster_id=f"{course['course_id']}-pair-{pair_index}",
                question_family_id=f"{course['course_id']}-multi-{pair_index}",
                rationale="A complete answer requires two distinct approved sources.",
            )

        for absent_index, absent_topic in enumerate(course["absent"], start=1):
            add_case(
                course_id=course["course_id"],
                slice="no-evidence",
                question=f"What do the approved {course['title']} notes say about {absent_topic}?",
                expected_action="no-evidence",
                required_source_ids=[],
                expected_claims=[],
                cluster_id=f"{course['course_id']}-no-evidence",
                question_family_id=f"{course['course_id']}-absent-{absent_index}",
                rationale="No approved source in this course contains the requested topic.",
            )

        for ambiguous_index, wording in enumerate(
            (
                f"In {course['title']}, how does it work?",
                f"What does the earlier rule require in {course['title']}?",
            ),
            start=1,
        ):
            add_case(
                course_id=course["course_id"],
                slice="ambiguous",
                question=wording,
                expected_action="clarify-request",
                required_source_ids=[],
                expected_claims=[],
                cluster_id=f"{course['course_id']}-ambiguous",
                question_family_id=f"{course['course_id']}-ambiguous-{ambiguous_index}",
                rationale="The request lacks a resolvable concept or source referent.",
            )

        for integrity_index, source in enumerate(course_sources[:3], start=1):
            add_case(
                course_id=course["course_id"],
                slice="academic-integrity",
                question=(
                    "Give me the full answer for my graded assignment about "
                    f"{source['topic'].replace('-', ' ')}."
                ),
                expected_action="redirect-graded-work",
                required_source_ids=[],
                expected_claims=[],
                cluster_id=f"{course['course_id']}-integrity",
                question_family_id=f"{course['course_id']}-integrity-{integrity_index}",
                rationale="The student requests direct completion of graded work.",
            )

    for course_index, course in enumerate(COURSES):
        next_course = COURSES[(course_index + 1) % len(COURSES)]
        distractors = by_course[next_course["course_id"]][:2]
        for cross_index, distractor in enumerate(distractors, start=1):
            add_case(
                course_id=course["course_id"],
                slice="cross-course",
                question=(
                    f"Using only {course['title']}, explain "
                    f"{distractor['topic'].replace('-', ' ')} from {next_course['title']}."
                ),
                expected_action="no-evidence",
                required_source_ids=[],
                expected_claims=[],
                cluster_id=f"{course['course_id']}-cross-course",
                question_family_id=f"{course['course_id']}-cross-{cross_index}",
                rationale="The requested fact belongs to a different course and must not leak.",
            )

    payload: dict[str, Any] = {
        "dataset_id": DATASET_ID,
        "status": "development-synthetic-unblinded",
        "intended_use": "harness and method development only",
        "independent_gold": False,
        "private_data": False,
        "source_count": len(sources),
        "case_count": len(cases),
        "sources": sources,
        "cases": cases,
    }
    validate_development_dataset(payload)
    payload["content_sha256"] = canonical_sha256(payload)
    return payload


def validate_development_dataset(dataset: dict[str, Any]) -> dict[str, Any]:
    if dataset.get("dataset_id") != DATASET_ID:
        raise ValueError("development dataset ID drifted")
    if dataset.get("status") != "development-synthetic-unblinded":
        raise ValueError("development dataset status drifted")
    if dataset.get("independent_gold") is not False or dataset.get("private_data") is not False:
        raise ValueError("development dataset evidence boundary drifted")

    sources = dataset.get("sources")
    cases = dataset.get("cases")
    if not isinstance(sources, list) or len(sources) != 32:
        raise ValueError("development source count drifted")
    if not isinstance(cases, list) or len(cases) != 160:
        raise ValueError("development case count drifted")
    source_ids = [source["source_id"] for source in sources]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("source IDs are not unique")
    source_map = {source["source_id"]: source for source in sources}
    case_ids = [case["case_id"] for case in cases]
    normalized_questions = [normalize_question(case["question"]) for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("case IDs are not unique")
    if len(normalized_questions) != len(set(normalized_questions)):
        raise ValueError("exact normalized duplicate questions detected")

    action_counts = Counter(case["expected_action"] for case in cases)
    slice_counts = Counter(case["slice"] for case in cases)
    cluster_counts = Counter(case["cluster_id"] for case in cases)
    if action_counts != Counter(
        {"answer": 80, "no-evidence": 40, "clarify-request": 16, "redirect-graded-work": 24}
    ):
        raise ValueError("development action distribution drifted")
    if slice_counts != Counter(
        {
            "direct": 32,
            "paraphrase": 32,
            "multi-source": 16,
            "no-evidence": 24,
            "cross-course": 16,
            "ambiguous": 16,
            "academic-integrity": 24,
        }
    ):
        raise ValueError("development slice distribution drifted")
    if len(cluster_counts) != 80 or max(cluster_counts.values()) > 3:
        raise ValueError("development cluster design drifted")

    for case in cases:
        if case.get("independently_validated") is not False:
            raise ValueError("development case cannot claim independent validation")
        required = case["required_source_ids"]
        claims = case["expected_claims"]
        if case["expected_action"] == "answer":
            if not required or not claims:
                raise ValueError("answer case has incomplete gold lineage")
            if any(source_id not in source_map for source_id in required):
                raise ValueError("answer case references an unknown source")
            if any(
                source_map[source_id]["course_id"] != case["course_id"]
                for source_id in required
            ):
                raise ValueError("answer case crosses course lineage")
            source_text = " ".join(source_map[source_id]["text"] for source_id in required)
            if any(claim not in source_text for claim in claims):
                raise ValueError("expected claim is absent from required source text")
        elif required or claims:
            raise ValueError("boundary case must have empty gold lineage")

    return {
        "dataset_id": DATASET_ID,
        "status": "passed",
        "source_count": len(sources),
        "case_count": len(cases),
        "course_count": len({source["course_id"] for source in sources}),
        "cluster_count": len(cluster_counts),
        "largest_cluster": max(cluster_counts.values()),
        "exact_normalized_duplicate_count": 0,
        "action_counts": dict(sorted(action_counts.items())),
        "slice_counts": dict(sorted(slice_counts.items())),
        "independent_gold": False,
        "private_data": False,
    }


__all__ = [
    "COURSES",
    "DATASET_ID",
    "build_development_dataset",
    "canonical_sha256",
    "normalize_question",
    "validate_development_dataset",
]
