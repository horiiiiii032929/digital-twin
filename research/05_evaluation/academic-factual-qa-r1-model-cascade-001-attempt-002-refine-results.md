# R1 four-model product cascade — attempt 002

Result ID: `academic-factual-qa-r1-model-cascade-001-attempt-002-refine`

Decision: **Refine / retain deterministic grounded fallback**

## What ran

The corrected cascade executed from clean revision
`c6338a9b5a9e641d472325434f954d4b33d5e6ec`. It built and verified four
immutable hybrid BM25 + local-Qwen3 indexes over 2,100 public source regions,
then ran the same stratified 200 cases through exact direct-OpenAI bindings for
GPT-5.4 mini, GPT-5.6 Luna, GPT-5.6 Terra, and GPT-5.6 Sol. Each arm persisted
200 responses; 19 deterministic boundary responses per arm required no model
call.

The screening gate required zero severe unsupported releases, 100% source-
version-valid citations, at least 98% boundary action accuracy, at least 99%
provider completion, and at most 1% malformed output. No model passed, so the
runner correctly made zero 500-case, paired-control, or advisory-review calls.

## Results

| Model | Grounded factual success | Answerable action | Boundary action | Source version validity | Severe releases | All evidence@3 | Recall@5 | p95 latency | Cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| GPT-5.4 mini | 16.9% | 51.3% | 87.5% | 95.0% | 3 | 57.5% | 66.6% | 3.01 s | $0.4020 |
| GPT-5.6 Luna | 15.0% | 51.9% | 92.5% | 95.6% | 1 | 57.5% | 66.6% | 3.15 s | $0.0985 |
| GPT-5.6 Terra | 18.1% | 52.5% | 92.5% | 98.1% | 2 | 57.5% | 66.6% | 2.91 s | $0.8957 |
| GPT-5.6 Sol | 16.3% | 57.5% | 95.0% | 96.9% | 1 | 57.5% | 66.6% | 4.00 s | $1.7402 |

All 724 provider calls completed with exact identities, zero malformed
responses, zero retries, and zero operational failures. They used 1,400,172
input tokens and 87,996 output tokens for a total reported cost of
USD 3.13628185. The four screening arms persisted 800 responses. Local index
materialization took 641.755 seconds and made no provider call.

## Diagnosis

The same retrieval failure appears under every generator: 68/160 answerable
screening cases lacked complete evidence in the top three and 54/160 lacked at
least one required span in the top five. A larger model cannot recover evidence
that the product did not retrieve. Generation and policy also remain unsafe:
every model answered at least one deliberately ambiguous question instead of
clarifying, producing seven severe unsupported releases across the four arms.

Representative severe failures include
`academic-open-dev2-0007-q5`, `academic-open-dev2-0027-q5`,
`academic-open-dev2-0039-q5`, and `academic-open-dev2-0051-q5`. Each asks what
an unresolved “it” does next; the authoritative action is `clarify`, but at
least one model selected a plausible retrieved sentence and released it as an
answer. Direct inspection found no critical source-truth ambiguity in these
four planted boundary cases.

## Validity and decision

The run is valid unfavorable development evidence. Public cases and product
responses remained physically separate from hidden gold until scoring; model
identity, accounting, checkpoint, and source hashes remained intact. The
sealed 10,000 cases, private data, T0/T1 confirmation, and public tunnel did not
open.

No OpenAI model is selected for R1, and the one-time cascade authority is
revoked. The release path retains the deterministic grounded generator and must
make no LLM-quality or LLM-backed-autonomy claim. The next finite product step
is a network-free T0/T1 graph confirmation under that explicit fallback; the
shared retrieval/evidence method requires a new method-level successor before
the sealed 10,000-case academic evaluation.
