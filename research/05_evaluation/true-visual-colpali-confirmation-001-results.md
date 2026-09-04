# True-visual ColPali confirmation 001

## Decision

`completed-go-deeper`. Keep the Jina v4 multi-vector late-interaction retriever
as the candidate for a separate actual-product visual checkpoint. Do not yet
select or advertise a representative multimodal product capability.

## Result

The bounded run ranked 30 source-disjoint public educational visual assets: 10
tables, 10 equations, and 10 diagrams. It compared source-visible-text BM25
with direct image/query multi-vector retrieval and normalized MaxSim scoring.

| Measure | Candidate | Control | Frozen gate | Pass |
| --- | ---: | ---: | ---: | :---: |
| Complete visual evidence@3 | 28/30 (93.33%) | 18/30 (60.00%) | at least 90.00% | Yes |
| Visual evidence recall@5 | 30/30 (100%) | 18/30 (60.00%) | at least 96.67% | Yes |
| Table evidence@3 | 10/10 (100%) | 10/10 (100%) | at least 80% | Yes |
| Equation evidence@3 | 10/10 (100%) | 5/10 (50%) | at least 80% | Yes |
| Diagram evidence@3 | 8/10 (80%) | 3/10 (30%) | at least 80% | Yes |
| Diagram improvement | +50 percentage points | — | at least +10 points | Yes |
| Original-region lineage | 30/30 (100%) | — | 100% | Yes |
| Exact course isolation | 30/30 (100%) | — | 100% | Yes |

All 60 first-party Jina calls completed without retries or failures. The run
used 144,639 input tokens and cost USD 0.00723195. Maximum observed call latency
was 6.06 seconds.

## Ten-million-token account limit

The researcher-supplied account ceiling was frozen at 10,000,000 tokens. The
runner reserved a conservative worst case of 1,966,080 tokens before execution
and enforced cumulative usage before and after every call. Actual usage was
144,639 tokens (1.45% of the account ceiling), leaving 9,855,361 tokens relative
to that stated ceiling. The ceiling is an account-level safety input, not a
quality metric.

## Interpretation

Direct visual late interaction materially improved retrieval over the text-only
control and passed every preregistered retrieval gate. The two remaining top-3
misses were diagrams; both appeared within the top five. This supports carrying
the candidate into an end-to-end product comparison, not promoting it directly
into the release profile.

The paired 30 boundary cases were intentionally not scored in this retrieval
run. Reading their hidden action labels here would have mixed retrieval with
product policy and weakened the later no-gold-leakage comparison. The next
checkpoint must evaluate answer generation, abstention/clarification, atomic
claims, and citations resolving to the original visual region.

## Boundaries

- The sample is fresh and source-disjoint but still small and public; it is not
  representative professor-material evidence.
- This checkpoint evaluates retrieval and lineage, not the complete student
  answer-generation path.
- Jina embeddings are ranking features and never authoritative source truth.
- Private course, student, and participant data were not processed.
- Raw embeddings and provider ledgers remain ignored; only sanitized aggregate
  evidence is committed.
- The one-time provider authorization is revoked.
