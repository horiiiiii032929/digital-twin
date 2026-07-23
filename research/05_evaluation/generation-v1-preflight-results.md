# Generation v1 deterministic preflight results

## Run identity

- Result ID: `generation-v1-preflight-clean`
- Components: generator control, prompt candidate, policy enforcement, and
  citation validation
- Status: completed
- Date and owner: 2026-07-15, Digital Twin project
- Code revision: `6a67ada0137b1213650c9ceb7162a2a8457bc5bf`
- Working tree: clean
- Reproduction: `npm run verify:generation`
- Runtime: the current reproduction environment uses Python 3.12.13 and
  Pydantic 2.13.4; the clean run did not capture exact dependency versions, and
  no live model was loaded
- Generated artifact: `reports/generated/generation-v1-clean.json` (ignored)
- Predecessor: none

## Decision context

The question was whether the deterministic control and its surrounding policy,
prompt, citation, and provider-suppression plumbing were safe and reproducible
enough to freeze before a live comparison. The prediction was that applying
policy before generation would make graded-work and no-evidence behavior fully
deterministic, while citation validation would be the most failure-prone normal
answer boundary.

- Control: deterministic grounded generator v1
- Live candidate: none in this preflight
- Retrieval: BM25 v1, `k1 = 1.2`, `b = 0.75`, limit 5
- Prompt: direct grounded prompt v1
- Policy: approved synthetic structured professor policy v1 plus deterministic
  policy enforcer v1
- Citation validation: deterministic prompt-local evidence binding v1
- Hard gates: every recorded accuracy must equal 1.00, provider tokens must
  equal zero, and no provider cost may be reported

## Data and sample size

- Dataset: `generation-v1`
- Corpus: `synthetic-browser-security-v1`
- Cases: 25 fixed preflight cases, with five each for direct grounding,
  misconception, integrity boundary, ambiguity, and no evidence
- Special raw counts: two graded-work redirects and five no-evidence cases; all
  seven require provider suppression
- Split: no calibration or held-out split; this is an exhaustive regression
  check of the frozen fixture, not an estimate of production performance
- Permission and sensitivity: synthetic-only, approved for tests, with no
  instructor or student data
- Exclusions: live answer-quality, provider-failure, multilingual, image, and
  private-course cases

The sample is large enough to exercise each implemented control path but not to
support a generalization claim. Confidence intervals would misrepresent this
fixture-style verification, so raw counts are reported instead.

## Aggregate results

| Candidate | Metric | Value | Raw count | Uncertainty | Threshold | Pass |
| --- | --- | ---: | ---: | --- | ---: | --- |
| Deterministic control | Policy-action accuracy | 1.00 | 25/25 | Fixed fixture | 1.00 | Yes |
| Deterministic control | Citation validity | 1.00 | 25/25 | Fixed fixture | 1.00 | Yes |
| Deterministic control | Graded-work redirect accuracy | 1.00 | 2/2 | Fixed fixture | 1.00 | Yes |
| Deterministic control | No-evidence accuracy | 1.00 | 5/5 | Fixed fixture | 1.00 | Yes |
| Deterministic control | Required provider suppression | 1.00 | 7/7 | Fixed fixture | 1.00 | Yes |

## Slice results

| Candidate | Slice | Cases | Fully passing cases | Important observation |
| --- | --- | ---: | ---: | --- |
| Deterministic control | Direct grounding | 5 | 5 | Each answer used retrieved evidence and a valid citation. |
| Deterministic control | Misconception | 5 | 5 | Plumbing passed; explanation quality was not judged. |
| Deterministic control | Integrity boundary | 5 | 5 | Both direct-completion requests redirected before a provider call. |
| Deterministic control | Ambiguous | 5 | 5 | BM25 found evidence for all five synthetic short queries. |
| Deterministic control | No evidence | 5 | 5 | Every case stopped before generation. |

## Hard gates

| Candidate | Gate | Result | Raw count | Evidence |
| --- | --- | --- | ---: | --- |
| Deterministic control | Correct policy action | Pass | 25/25 | Per-case generated artifact |
| Deterministic control | Valid citation behavior | Pass | 25/25 | Per-case generated artifact |
| Deterministic control | Suppress provider when required | Pass | 7/7 | Provider model recorded as `not-called` |
| Deterministic control | No provider usage | Pass | 0 tokens | Aggregate usage trace |
| Deterministic control | No provider cost | Pass | 0 calls | `paid_provider_called=false`; cost not applicable |

## Operational results

- Mean local generation latency: 0.049 ms
- Provider calls, input tokens, and output tokens: zero
- Approximate provider cost: not applicable
- Network, model load, and provider cold start: not exercised

## Failures and surprises

No case failed. Citation validation did not fail as predicted because the
deterministic generator copied only prompt-local evidence bindings. This is a
useful control result, but it does not test whether free-form model prose is
entailed by the cited evidence.

The perfect fixture score is not evidence of broad policy understanding. The
integrity detector is lexical and can miss indirect or novel paraphrases. BM25
can also return weak lexical matches for vocabulary-sharing out-of-domain
questions, as the later retrieval-v2 benchmark demonstrated.

## Validity review

- Calibration/test separation: not applicable; this is a named preflight
  regression set, not a model-selection test
- Metric reliability: deterministic comparisons against explicit fixture labels
- Data defects found: none
- Run invalidated: no
- Private or unapproved data: none

## Decision

**Go deeper.** Freeze this deterministic implementation as the control for #24,
but keep generator, prompt, policy-enforcement, and citation-validation entries
pending in the experimental profile. Select nothing until one provider/model,
budget cap, live results, failure analysis, and standard component decision
records exist. The preflight adds no production profile selection.

## Limitations and follow-up

- The result does not establish pedagogy, misconception correction, factual
  entailment of model prose, prompt quality, or provider reliability.
- Provider timeout, authentication, and malformed-output paths use injected
  tests rather than live failures.
- The next comparison needs frozen controlled evidence, a live model and prompt
  configuration, human-readable answer-quality judgments, latency, tokens,
  cost, and a spending cap.
- End-to-end generation must also wait for a separately evaluated retrieval
  evidence-sufficiency gate.

## Learning notes

Safety behavior that can be decided from approved policy and evidence presence
belongs before the probabilistic model call. That separation makes refusal,
redirection, provider suppression, and citation identity independently testable.
It does not make the generated explanation grounded by itself: sentence-level
support and pedagogical quality still require a live-output evaluation.
