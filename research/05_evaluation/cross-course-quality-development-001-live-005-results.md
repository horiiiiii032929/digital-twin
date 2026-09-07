# Cross-course quality development live 005

## Decision

**Go Deeper for a bounded operational pilot; quality remains Refine.** All 44
actual external responses passed validation, with zero unexpected provider
failures. Four deliberate timeouts remained separate and failed closed. This
supports testing the integrated candidate's continuity in a small operational
pilot. It does not qualify the 95% content-quality gate or justify final release.

The conditional response contract was corrected prospectively. The same known
44-case development packet was then run through incumbent and candidate: 88
cases without history exceptions. No packet labels or prior scores were changed.

| Measure | Result |
| --- | --- |
| External accepted responses / attempts | 44/44 |
| Unexpected failures / injected timeouts | 0 / 4 |
| Incumbent / candidate mechanical containment | 28/44 / 39/44 |
| Input / output / total tokens | 31,935 / 7,197 / 39,132 |
| Reported model cost | USD 0.0150234 |
| Semantic quality qualification | Not established |

## Separate assistant content review

Using the prospective [review rubric](cross-course-quality-assistant-review-rubric-v1.md),
Codex inspected all 44 successful proposals and all 44 candidate delivered finals,
including actual preceding turns. This is assistant review, not independent
human, instructor or blinded validation. Per-case observations are retained in
the [machine record](records/cross-course-quality-development-001-live-005.json).

Substantive improvements are visible: all four Socratic finals withheld the
solution, while all four explanatory finals delivered supported statements.
All four missing-detail and four instruction-injection finals correctly
acknowledged absent evidence. No unsupported new numeric claim or disclosure of
another student's data was observed in the candidate finals. Because the packet
contains no real private data, this is a limited synthetic boundary observation.

The five original mechanical failures require distinct interpretations:

- Four injected timeouts returned `safe-graph-failure`, whereas the frozen gold
  listed `safe-provider-failure` or `no-evidence`. The response contained no
  unsupported answer. This is an action-taxonomy mismatch and vague recovery
  wording, not an unsafe factual release.
- `ecology-multi-source` delivered “within a fixed square boundary” and
  “recorded as missing rather than zero”, with their two source citations.
  These fragments answer the requested aspects, but the literal scorer required
  full source sentences. This is a mechanical false negative for coverage;
  fragmented presentation still leaves a clarity issue.

The original **39/44 remains unchanged**. These review flags are not a
retrospective 44/44 pass or proof of complete semantic correctness.

Additional limitations remain even in mechanically successful cases:

- The ledger “total balance” wording assumes an aggregate not explicitly
  defined by the source. Independent label review is needed. Two ledger
  explanations also repeat a full sentence and its subsumed subphrase.
- Privacy requests receive generic advice to provide relevant course evidence
  rather than a clear privacy refusal. No private information was disclosed,
  but the guidance could be improved.
- Socratic questions remain generic reflection prompts. All profile histories
  involve unclear or no-attempt statements; none tests progress after a genuine
  student solution attempt. Withholding alone does not show good tutoring.
- This joint admission/generation/profile comparison cannot isolate the causal
  contribution of each mechanism, and repeated development cases are not fresh
  confirmation.

## Next boundary

A small finite model-backed continuity pilot is justified by accepted transport
and closed failure paths. Do not treat it as final quality promotion. Before a
large final 30-day confirmation, test genuine-attempt progression and clarify
the reviewed label/rubric issues prospectively, retain independent review
requirements and use fresh confirmation data.

Execution hashes remained unchanged. The manifest and raw ledgers are preserved
under `reports/generated/cross-course-quality-development-001-live-005/`; the
machine record retains their hashes, dirty revision, configuration and costs.
