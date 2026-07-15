# Generation v1 deterministic preflight results

## Recorded run

- Date: 2026-07-15
- Code revision: `6a67ada0137b1213650c9ceb7162a2a8457bc5bf`
- Working tree: clean
- Dataset: `generation-v1`
- Corpus: `synthetic-browser-security-v1`
- Cases: 25
- Retrieval: BM25 v1, `k1 = 1.2`, `b = 0.75`, limit 5
- Generator: deterministic grounded generator v1
- Paid provider called: no
- Reproduction: `npm run verify:generation`

The full per-case JSON was generated locally at
`reports/generated/generation-v1-clean.json`. Generated output remains ignored.

## Measurements

| Metric | Result | Required preflight threshold |
| --- | ---: | ---: |
| Policy-action accuracy | 1.00 | 1.00 |
| Citation validity | 1.00 | 1.00 |
| Graded-work redirect accuracy | 1.00 | 1.00 |
| No-evidence accuracy | 1.00 | 1.00 |
| Required provider-suppression accuracy | 1.00 | 1.00 |
| Mean local generation latency | 0.049 ms | Informational |
| Input tokens | 0 | 0 |
| Output tokens | 0 | 0 |
| Approximate provider cost | Not applicable | No cost allowed |

No case failed. The 25 questions include five direct-grounding, five
misconception, five integrity-boundary, five ambiguous, and five no-evidence
cases. Two integrity cases required graded-work redirection; five cases required
no-evidence behavior. All seven stopped before a provider boundary.

## Interpretation

The result verifies the deterministic control and surrounding safety plumbing:

- only approved retrieval hits enter prompt construction;
- a fully resolved professor release policy is required;
- direct graded-work completion and no-evidence cases stop before generation;
- normal answers cite retrieved source/locator relationships;
- policy action and operational telemetry are recorded; and
- the test is reproducible without credentials, network, tokens, or cost.

The result does not evaluate explanation quality. The deterministic control
returns a cited evidence excerpt and therefore cannot establish pedagogy,
misconception correction, factual entailment of model prose, prompt quality, or
live-provider reliability.

## Failure analysis and limitations

There were no failures in the recorded set. That perfect score reflects a
bounded preflight, not generalization:

- the integrity detector is lexical and can miss indirect or novel paraphrases;
- BM25 may retrieve weak lexical matches for other out-of-scope questions;
- citation validity proves source relationship, not sentence-level entailment;
- the dataset is synthetic and contains no professor-approved private course
  material;
- no provider timeout, authentication, or malformed response occurred during
  this run, although those paths are covered with injected automated tests; and
- no live tokens, latency, cost, answer-quality, or model comparison exists.

## Decision

Go deeper. Freeze this deterministic implementation as the control for #24, but
keep generator, prompt, policy-enforcement, and citation-validation entries
pending in the experimental profile. Select nothing until one provider/model,
budget cap, live results, failure analysis, and standard component decision
records exist.
