# Real-course continuation diagnostic

Prospective plan, 2026-09-06. No provider outputs exist at authoring. This is a
bounded diagnostic after synthetic development, not the completion contract's
representative 400-question confirmation or independent human review.

## Decision question and prediction

Does the frozen improved instructional candidate remain useful on selected
passages from actual permitted lectures, compared with the v4 extractive control?
The prediction is better attempt-specific and explanatory content, with remaining
risks from unsupported qualifications, mixed missing details, source parsing,
initial solution disclosure and response-schema limits.

## Scope and source permission

Use the four courses in the [v2 portfolio](../05_evaluation/cross_course_portfolio_v2.manifest.json),
under the [source-holder permission](../03_data/academics-source-permission.md).
Two whitespace-normalized, explicitly bounded page excerpts per course come from
one hash-matched official lecture PDF per course. Headers, staff contact details,
student data and assessment/answer material are excluded. Only pedagogical
lecture passages, synthetic questions, approved synthetic teaching profiles and
derived responses enter the generation provider. These are curated context cards,
not a test of full-corpus retrieval, diagrams or automatic PDF ingestion quality.

Private packet, source page/character-selection lineage and rebuild script remain
under ignored `reports/generated/real-course-continuation-development-v1/`.
The runner copies and hashes the packet. Durable results may record course IDs,
source hashes/pages, aggregate metrics and sanitized failure categories; do not
copy private source text, prompts or schedules into committed records.

## Frozen design before execution

- 32 contexts: four courses times eight forms; 40 student turns per arm,
  80 paired turns, 64 histories and 16 expected runtime restarts.
- Forms: two direct explanations, initial elicitation, correct attempt,
  incorrect attempt, compound question, unavailable information and mixed evidence.
- V4 and the candidate that passes the preceding synthetic development gates;
  exact candidate ID and source hash must be recorded before launch. No model or
  prompt changes based on this packet's outputs.
- Same Luna model, low reasoning, 3,000 output tokens, seed7801, one trial, four
  independent histories in flight and the existing three-call maximum per turn.
- Hard caps: 400 provider attempts and USD10 in conservative reservations
  (at most240 calls/USD6 worst case). Retain failed and malformed outcomes.
- Root assistant authored all cases; a separate assistant reviews source
  correspondence, profile/gold consistency and exclusions before generation.
  Neither constitutes a human labeler. Record any setup correction before calls.

Apply the [meaningful continuation rubric](../05_evaluation/meaningful-continuation-rubric-v1.md)
by meaning to every target and inspect all preceding turns for critical violations.
Report each axis, all eight forms, each course, paired wins/losses/ties/uncertainty,
citation lineage, failures, latency, tokens and cost. Missing/uncertain outputs do
not pass. Do not treat turns or the eight excerpts as independent learners.

Diagnostic keep criterion: at least26/32 useful targets, at least6/8 in each
course, zero verified substantive unsupported statements, false corrective
feedback, protected disclosure, or prohibited initial full solutions, and
nonnegative definite paired win-minus-loss direction. Failing these criteria
means Refine for real-course use, even if synthetic gates passed. These narrower
engineering criteria do not replace the 95%/98% completion thresholds.

## Execution boundary

The execution owner must bind the existing qualified generation provider's
account class, transferred fields, retention/training configuration, region when
known, local deletion/retention policy and exact run limits in the prospective
run manifest. Do not infer unknown provider retention or zero retention. Do not
use any external judge. Run an injected contract before paid generation and
archive the executable source snapshot and both final hashes. No source changes
during the paired run, and no retries chosen by answer quality.

Reproduce the already authored packet with the ignored `build_packet.py` and run
`uv run python -m scripts.run_paired_pedagogy_development --packet <private-packet>
--candidate <frozen-version> --output-dir <new-run> --maximum-calls 400
--maximum-cost-usd 10 --live`. Use a distinct new output directory for every run.
Record each attempt in the result registry, including contract failures and
negative or inconclusive outcomes. Instructor fidelity and student learning
remain separate unmeasured outcomes.
