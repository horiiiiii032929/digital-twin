# Component evaluation inventory

This inventory is the readable view of the machine-validated
[`student-tutor-v0`](../research/05_evaluation/profiles/student-tutor-v0.json)
experimental profile. The profile is authoritative when this table and the JSON
disagree.

| Component | Runtime boundary | Current state | Selected or control | Next comparison | Primary evidence or gates |
| --- | --- | --- | --- | --- | --- |
| Source adapter | Provides an approved source artifact | Selected | Local files v1 | Optional Canvas adapter | Approval, sensitivity, version integrity |
| Parser | Produces normalized document segments and figures | Selected | PyMuPDF document parser v1 | Layout-aware parser; OCR only if justified | Extraction, reading order, provenance |
| Chunker | Produces stable retrieval units | Selected / Refine | Heading-paragraph chunker v1 | Fixed-token and semantic chunking | Retrieval quality, duplication, boundary loss |
| Retriever | Returns ranked approved chunks and an explicit sufficiency decision | Selected / Refine | BM25 v1 plus any-hit only as rollback/control; no safe gate selected | Cross-encoder relevance verifier vs calibrated answerability classifier | Recall@K, MRR/nDCG, false answer/abstention, permission filtering, latency |
| Reranker | Reorders retrieved candidates | Pending | No selected implementation | No reranker vs cross-encoder or LLM | Ranking gain, latency, cost, evidence preservation |
| Figure description | Produces reviewable semantic figure text | Pending | Caption/context is metadata, not selected description | Caption/context vs vision model | Factuality, figure lineage, review and display permission |
| Generator | Produces a grounded answer | Pending | DeepSeek API is the fixed primary product constraint but remains unqualified; deterministic and local Gemma controls are unselected | DeepSeek qualification against deterministic and local controls in #24 | Grounding, failure handling, latency, tokens, cost |
| Prompt | Packages question, evidence, and policy | Pending | Direct grounded prompt implemented but not selected | Direct vs guided grounded prompt with fixed DeepSeek and sufficient evidence | Pedagogy, consistency, prompt traceability |
| Tutor policy | Stores professor-approved behavior | Selected | Structured professor policy v1 | Versioned policy refinements | Professor approval, privacy, integrity boundaries |
| Policy enforcement | Applies policy to a tutoring turn | Pending | Deterministic rules pass synthetic preflight but are not selected | Challenge with paraphrased and adversarial requests | Refusal precision, safe redirection, no-evidence behavior |
| Citation validation | Confirms answer citations map to hits | Pending | Deterministic validator implemented but not selected | Test against live malformed and invented citations | Hit relationship, locator, active version |
| Conversation orchestration | Maintains student-turn state | Pending | No implementation selected | Deterministic state vs graph orchestration | Traceability, recovery, data minimization |
| Proactive trigger | Decides whether to initiate support | Deferred | No implementation selected | Future work after the deployed pilot | Trigger precision/recall, suppression, student control |
| Learning-gap analytics | Aggregates confusion signals | Deferred | No implementation selected | Future work after the deployed pilot | Accuracy, privacy thresholds, uncertainty, actionability |

## Current profile meaning

Five components are selected because the repository already has design or
evaluation evidence: local source input, PyMuPDF parsing, heading/paragraph
chunking, BM25 retrieval, and the structured professor policy. Seven remain
pending and two are deferred from the final critical path. Pending does not mean
unimportant; it prevents the roadmap from pretending a technical decision
exists before its evaluation.

Issue #24 now has implemented candidates for generator, prompt, policy
enforcement, and citation validation. They intentionally remain pending. A
local Gemma 3 4B run passed all structural checks at zero monetary cost, but a
post-run diagnostic found three unsupported or citation-mismatched answers in
18 model calls. The quality rubric was not frozen prospectively, so the result
selects nothing. DeepSeek API is now the fixed primary product constraint, with
synthetic-only inputs and a cumulative USD 10 qualification cap, but the exact
configuration and prompt remain unselected until they pass prospective #24
evidence.

The chunker is selected with a `Refine` decision because the algorithm works
and preserves provenance, but size and overlap still need comparison on a
larger approved corpus. Retrieval v2 evaluated BM25, local BGE-small dense
retrieval, and reciprocal-rank fusion on a harder held-out set. None satisfied
all gates, so no candidate replaced BM25 v1 and the next comparison must target
the observed evidence-sufficiency and ranking failures. Both retrieval runs and
the ingestion result are indexed by the durable evaluation-result registry.

Evidence-sufficiency v1 then compared any-hit, calibrated BM25 raw score,
lexical coverage, and BGE-small semantic agreement on 30 calibration and 50
held-out cases. Every learned candidate failed calibration and held-out gates.
Semantic agreement was strongest but still produced 5/18 false answers and
8/32 false abstentions while regressing unconditional ranking quality. No gate
was selected and #25 remains blocked from making an end-to-end grounding claim.

## Roadmap integration

- #11 first freezes the method, dataset, rubric, privacy, architecture, and
  professor-reporting protocol.
- #24 resolves generator, prompt, policy enforcement, and citation validation;
  its first local live result is `Refine` with no selection.
- #41 records the failed evidence-sufficiency v1 comparison. #43 evaluates the
  actual returned-context verifier required before #25 makes end-to-end
  grounding claims.
- #25 validates the first complete end-to-end experimental RAG profile.
- #8 evaluates conversation state plus authentication, authorization,
  persistence, storage, student/professor journeys, and staging deployment.
- #9 evaluates security, privacy, reliability, rollback, and professor
  evaluation-release review.
- #10 evaluates calibrated LLM judging, frozen simulated-student trajectories,
  and deployed synthetic accounts. Proactive triggers and full analytics remain
  deferred.
- #12 runs the final blinded comparison and evidence freeze.

Each issue may refine the inventory, but it must not silently select an
implementation. A profile change requires evidence and a decision record.

## Deployable-pilot release boundaries

The current experimental profile covers RAG and tutor behavior but does not yet
model these release boundaries. Issue #11 must decide how they enter the profile
or a linked release checklist before #8 implementation begins.

| Boundary | Current control | Candidate class | Required evidence |
| --- | --- | --- | --- |
| Authentication | Unauthenticated local prototype | One managed or standards-based identity design | Invite, expiry/revocation, auth latency and recovery |
| Authorization | No multi-user boundary | Professor/student roles and course membership | Zero cross-role and cross-course bypass |
| Persistence | In-memory repositories | Transactional database and migrations | Restart survival, isolation, migration/rollback, latency |
| Private storage | Local fixtures | Access-controlled object storage | Upload/download isolation, deletion, provenance |
| Deployment | Local development | One managed FastAPI/Vite architecture | TLS, secrets, health, cost, deploy/rollback, recovery |
| Operations | Test-time failures only | Redacted logs, rate limits, backups, monitoring, runbooks | Error rate, p50/p95, restore time, incident handling |
| Professor review | Deterministic walkthrough | Deployed professor workflow | Evidence comprehension, release control, anchor approval |
| LLM judge | Authored rubric labels | Fixed calibrated judge plus distinct-family sensitivity judge | Expert agreement, order/repeat consistency, false passes |
| Simulated student | Authored scripted turns | Frozen state-card trajectories | Safe completion, checkpoint actions, recovery, simulator validity |
| Synthetic accounts | Local API/UI checks | Scripted deployed journeys | Role isolation, persistence, reliable turns, privacy, recovery |
