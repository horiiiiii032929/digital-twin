# Multimodal benchmark Claude second review v1

Date: 2026-08-01

Result ID: `multimodal-benchmark-claude-second-review-v1`

Decision: **Refine the draft; do not seal or run retrieval candidates yet**

## Scope and validity

This advisory dataset-QA run reviewed all 40 cases in the private multimodal
draft against 26 eligible rendered pages. It tested whether a blinded vision
model could expose defects missed by the corrected assistant review v2, which
had accepted all 40 cases. It did not evaluate or select a retrieval model.

The run used Git revision
`482047d81b10675300bb2d4dd75fb7cd30f7cab6`. The working tree was dirty because
of pre-existing user-owned report and plotting changes outside the committed
review implementation. The private input SHA-256 was
`7abb5361f37cc482d21b83491ee83a1a2658fe3e6afb5e96ff7976fe08c1f413`.
The ignored private result is retained at
`data/processed/multimodal_retrieval_v1/claude_second_review_v1.json`, SHA-256
`2a8f04dfade3992bde58edc25678b8d41d7c8b932bdd06c40d86872d194daaa8`.

## Provider and data boundary

The source holder approved the recorded consumer boundary before execution.
The runner used the authenticated first-party Claude Code session under a
consumer Max subscription. It did not use an `ANTHROPIC_API_KEY`, API Console
credits, or pay-as-you-go API billing.

- Requested reviewer: `claude-sonnet-5`
- Models reported by Claude Code: `claude-sonnet-5`, with
  `claude-haiku-4-5-20251001` helper usage
- Calls: seven asset batches, no resumed session, no web searches
- Transferred: 26 eligible rendered pages and blinded fields for 40 cases
- Withheld: source paths, course IDs, prior decisions, excluded assessments and
  solutions, student data, credentials, and secrets
- Region: not exposed by the consumer client
- Model-improvement setting: not machine-readable; the source holder accepted
  the consumer setting and terms before the run
- Retention/deletion boundary: consumer terms apply; deleted chats are normally
  removed from backend systems within 30 days, while safety-flagged material
  may be retained longer

The CLI was run with safe mode, only the `Read` tool, access limited to a
temporary directory, and session persistence disabled. Temporary page copies
were removed after each batch. The provider may still process and retain data
under its consumer terms; no local flag can override that provider boundary.

## Results

| Outcome | Cases | Rate |
| --- | ---: | ---: |
| Accept | 22 | 55% |
| Revise | 17 | 42.5% |
| Reject | 1 | 2.5% |
| Schema-valid decisions | 40 | 100% |

Failed checks were 12 modality labels, eight visual-dependency labels, three
evidence regions, and one required-claim set. There were zero action,
source-eligibility, privacy, or permission failures.

By slice, outcomes were:

| Slice | Accept | Revise | Reject |
| --- | ---: | ---: | ---: |
| Visual-answerable | 13 | 10 | 1 |
| Text control | 2 | 6 | 0 |
| No evidence | 4 | 0 | 0 |
| Adversarial integrity | 3 | 1 | 0 |

The prospective prediction failed: only 22 cases were accepted rather than at
least 36, and one case was rejected for unsupported wording. The prediction's
privacy condition passed.

## Disagreement classification

Direct visual adjudication confirmed defects in four cases:

- `mmr1-it5003-fifo-02`: evidence region clips the rightmost panel;
- `mmr1-it5003-heap-03`: evidence region clips the substitution annotation and
  final value;
- `mmr1-it5007-web-01`: evidence region clips the location labels; and
- `mmr1-it5007-mapping-04`: required wording merges two separately labelled
  locations; its claim wording needs correction.

The remaining 14 disagreements were subsequently adjudicated by Codex on
2026-08-01 using the fixed benchmark taxonomy. This is a taxonomy decision,
not researcher verification. Five additional controls/refusal cases received
the same normalization so the rule is consistent across the full draft. The
original reviewer interpretations are retained below as disagreement evidence;
they are not the final schema labels:

- six text controls use `mixed` for the source-page modality while the reviewer
  interpreted modality as the minimum answer evidence and requested `text`;
- seven visual cases may be reconstructable from linearly extracted text, but
  whether ordering is reliable enough to make them text-sufficient is a
  benchmark-definition decision; and
- one integrity-refusal case proposed `not_applicable` for modality and
  dependency, which is not in the fixed schema.

The eight text controls retain their source-page modality (`mixed`) and
`text_sufficient` dependency. The seven visual cases whose claims are
recoverable from linear extracted text are held out of the visual denominator
pending genuinely visual replacement cases; they remain visible in the private
checklist so their source claims and regions can still be checked. The four
integrity cases retain source modality because refusal action, not evidence
modality, is the safety decision. The private checklist displays these
decisions and does not mutate the dataset automatically.

No private page content or model reasoning is reproduced here. The exact
per-case reasons remain in the ignored result.

## Operations

| Measure | Result |
| --- | ---: |
| Batch latency, mean | 95.78 seconds |
| Batch latency, maximum | 137.37 seconds |
| Claude Code provider-reported usage estimate | USD 1.6824451 |
| Confirmed incremental subscription charge | Not separately reported |
| External calls | 7 |
| Web-search requests | 0 |
| Permission denials | 0 |

Claude Code reported 62,134 output tokens, 114,641 cache-creation input tokens,
124,097 cache-read input tokens, and 32 direct input tokens for Sonnet, plus
24,754 input and 102 output tokens for the helper model. These are provider
usage counters, not evidence of an additional API invoice.

## Gates and decision

| Gate | Result |
| --- | --- |
| Approved provider, account, and source boundary | Pass |
| Mandatory-exclusion transfers | Pass: 0 |
| Complete call, usage, and cost log | Pass |
| Exactly 40 schema-valid decisions | Pass |
| Automatic benchmark mutation or sealing | Pass: none |
| Prospective quality prediction | Fail |

**Refine.** Apply the four visually confirmed corrections, retain the Codex
taxonomy adjudication, author seven genuinely visual replacement cases, rerun
structural checks, and complete researcher verification. Do not rerun Claude
merely to seek higher agreement, and do not select a retrieval or deployment
method from this QA run.

## Limitations

- Claude model agreement is not independent human or professor review.
- The source-holder approval used consumer Max terms, not commercial API,
  Team, or Enterprise controls.
- The model-improvement setting and processing region were not machine-readable.
- Batch latency includes agent/tool orchestration and is not a serving metric.
- The taxonomy adjudication is a project-method decision, not independent human
  verification.
- The benchmark remains researcher-unverified, private, ignored, and unsealed.

Reproduce only after accepting the documented consumer boundary:

```bash
npm run review:multimodal-private-claude
```
