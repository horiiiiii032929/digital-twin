# Generation v1 Gemma 3 4B exploratory results

## Run identity

- Result ID: `generation-v1-gemma3-4b-exploratory`
- Components: generator and direct grounded prompt candidate
- Status: inconclusive exploratory comparison
- Date and owner: 2026-07-15, Digital Twin project
- Code revision: `7ddf00a2882a0090574f00611219929ed8090f85`
- Working tree: clean for both control and live runs
- Reproduction: `npm run verify:generation -- --output
  reports/generated/generation-v1-deterministic-current.json` and
  `npm run benchmark:generation-local`
- Runtime: local Ollama, `gemma3:4b`, LiteLLM JSON response mode, temperature 0,
  60-second per-call timeout, and 600 maximum output tokens
- Generated artifacts: `reports/generated/generation-v1-deterministic-current.json`
  and `reports/generated/generation-v1-gemma3-4b.json` (ignored)
- Predecessor: `generation-v1-preflight-clean`
- Paid API calls and credential use: zero

## Decision context and validity

This was a safe exploratory transport and structure comparison after discovering
that the machine already had a local Gemma 3 4B model. It was not the
prospectively planned provider/model comparison required to select #24. The
existing deterministic structural gates were frozen, but no answer-quality
rubric, human-review protocol, or latency threshold was declared before the
run. The result can reject a candidate or motivate a proper experiment; it
cannot select one.

The first one-case transport smoke returned fenced JSON and correctly failed the
strict parser. LiteLLM/Ollama JSON response mode then returned strict JSON, so
the committed benchmark mode used that explicit configuration.

## Data and conditions

- Dataset: `generation-v1`, 25 synthetic cases
- Slices: five each for direct grounding, misconception, integrity boundary,
  ambiguity, and no evidence
- Model calls: 18 normal answer cases
- Deterministic short circuits: two graded-work redirects and five no-evidence
  cases; all seven stopped before Ollama
- Retrieval: the small `synthetic-browser-security-v1` BM25 fixture
- Evidence boundary: controlled synthetic v1 conditions only; the harder
  evidence-sufficiency v1 result still blocks end-to-end claims
- Sensitive data: none

## Structural comparison

| Candidate | Policy action | Citation relationship | Graded redirect | No evidence | Required suppression | Mean latency | Input tokens | Output tokens | Cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Deterministic control | 25/25 | 25/25 | 2/2 | 5/5 | 7/7 | 0.051 ms | 0 | 0 | Not applicable |
| Ollama Gemma 3 4B | 25/25 | 25/25 | 2/2 | 5/5 | 7/7 | 2,803.5 ms | 12,542 | 826 | $0.00 |

All 18 live calls produced parseable JSON and citation IDs that resolved to
retrieved approved hits. This proves transport, output structure, deterministic
policy short-circuiting, source identity, and usage telemetry. It does not prove
that the prose is entailed by those citations.

The deterministic control's 18 answer cases have grounded support by
construction: each answer copies the first approved retrieved chunk verbatim
and cites that same chunk. This is a mechanical control property, not evidence
of tutoring quality.

## Diagnostic grounding review

A post-run single-reviewer audit applied one strict criterion: every factual
statement must be supported by the model's cited evidence. The durable labels
are in
[`generation-v1-gemma3-4b.json`](judgments/generation-v1-gemma3-4b.json).

- Supported answer cases: 15/18 (0.833)
- Unsupported or citation-mismatched cases: 3/18
- `misconception-05` cited allowed tutoring help rather than the retrieved
  no-guess evidence.
- `ambiguous-01` introduced a secure-connection claim unsupported by evidence
  about authentication.
- `ambiguous-03` introduced unauthorized-request wording not stated in the
  cited synthetic passages.

Because this rubric was defined after seeing outputs and has one reviewer, the
0.833 score is diagnostic and cannot be used as an unbiased selection estimate.

## Operational evidence

- The installed model occupied about 3.3 GB on disk; Ollama reported about
  2.9 GB loaded on the local GPU during the run.
- Mean latency includes deterministic short circuits. The 18 actual model calls
  therefore have a higher mean than the reported all-case 2.80 seconds.
- Local usage was 13,368 total tokens and reported $0 cost.
- Cold-start latency, energy, resident memory, repeated-run variance, concurrency,
  and tail latency were not recorded.

## Decision

**Refine; select no generator or prompt.** Keep Gemma 3 4B as a zero-cost local
live control candidate and keep the deterministic generator as the frozen
structural control. The profile remains pending. A valid selection requires a
prospectively frozen grounding and pedagogy rubric, independent review or a
validated judge, repeated runs, prompt variants, latency/tokens/cost, and at
least one fit-for-purpose model candidate.

## What this means for #25

The local model path is technically usable for further controlled-evidence
experiments, but it does not unblock the product smoke demo. Evidence-sufficiency
v1 selected no retrieval gate, and this exploratory generation run found
sentence-level support failures that citation-ID validation alone cannot catch.

## Learning notes

Valid citation IDs prove referential integrity: the cited source was retrieved
and approved. They do not prove entailment. A model can cite a real chunk while
adding an unsupported adjective, relationship, or policy conclusion. Generator
evaluation therefore needs both deterministic citation validation and a
separate, prospectively validated factual-support rubric.
