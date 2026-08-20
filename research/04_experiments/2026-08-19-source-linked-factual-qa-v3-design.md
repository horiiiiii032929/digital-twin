# Source-linked factual QA v3 design

Date: 2026-08-19

Issue: [#87](https://github.com/horiiiiii032929/digital-twin/issues/87)

Status: frozen for no-model implementation; model execution and scale remain
unauthorized

## Decision question

Can the product create and answer a large, permission-safe factual-QA corpus
from the complete eligible Academia Vault while preserving source lineage,
claim-level evidence, safe boundary actions, and an inspectable human audit?

This is method and product validation, not a model leaderboard. A failed gate
routes to the responsible pipeline component and requires method revision.

## Prediction and controls

The prediction is that a source-first pipeline with exact evidence quotes,
deterministic validation, targeted independent review, and mutation tests will
produce auditable factual cases without treating an LLM verdict as ground
truth.

Two lanes remain separate:

1. The primary lane uses every eligible academic file in the canonical
   `Documents/academia_vault` collection. Every regular file receives an
   explicit disposition before corpus release.
2. The oracle-control lane uses a small deterministic dummy corpus generated
   from a hidden structured fact manifest. It proves extraction, retrieval,
   citation, boundary-action, and mutation mechanics; it is not evidence of
   real-course quality.

The sealed 32-PDF retrieval benchmark remains historical evidence and is not
expanded or reopened by this work.

## Corpus governance

The approved local collection is defined by
`research/03_data/academics-source-permission.md`. The canonical source is the
Documents copy; the partial Downloads copy is prohibited.

Every discovered regular file must resolve to exactly one role:

- `authoritative_evidence`: approved official teaching material that can
  support answer claims;
- `supporting_context`: useful context that cannot independently establish a
  factual claim;
- `question_inspiration_only`: personal notes or prompts that may inspire a
  question but must be verified against authoritative evidence;
- `excluded_integrity_or_privacy`: solutions, answer keys, completed or graded
  work, student or participant data, secrets, or unrelated content;
- `excluded_duplicate_generated_tool_state`: exact duplicates, caches,
  environments, build products, and generated tool state; or
- `review_or_conversion_required`: ambiguous eligibility or unsupported
  conversion that must be resolved before release.

Exact-content duplicates are processed once while every source path and
disposition remains traceable. Personal notes are never promoted to
authoritative evidence without an approved official source that establishes
the same claim.

## Product path

The v3 pipeline is:

1. inventory and classify all source files;
2. convert eligible documents locally while preserving file, page, region,
   version, and checksum lineage;
3. extract atomic evidence units across text, tables, diagrams, equations,
   screenshots, and OCR-bearing pages;
4. create factual questions and expected safe actions from source units;
5. retrieve from the actual released corpus without injecting gold evidence;
6. generate a structured Digital Twin response;
7. run deterministic source, quote, action, privacy, duplication, and mutation
   checks;
8. route unresolved semantic disputes to an independent reviewer; and
9. create a compact human-audit packet before any scale decision.

The internal response contract uses `answer`, `clarify`, `abstain`, or `refuse`
and requires atomic claims. Every answer claim contains one or more evidence
objects with a citation identifier and an exact quote. The rendered answer is
derived from the structured claims rather than accepted as an untraceable text
blob.

## No-model implementation gates

No provider call is permitted until all of these pass:

- complete file disposition with zero unclassified regular files;
- mandatory-exclusion and private-path sanitization checks;
- deterministic conversion lineage and checksum stability;
- oracle-control extraction, retrieval, citation, and boundary-action checks;
- claim-level response-schema validation;
- exact-quote and citation-target validation;
- content-deduplication with retained path lineage;
- deterministic mutation sensitivity; and
- complete audit-packet rendering from sanitized fixtures.

Mutation coverage includes wrong numeric values, reversed comparisons, omitted
table rows, wrong diagram edges, changed equation symbols, unsupported claims,
wrong citations, incomplete multi-source evidence, cross-course confusion,
wrong answer-versus-abstain decisions, and over-refusal.

## Prospective model roles

Model execution is not authorized by this design record. If the no-model gates
pass and a separate provider record is approved, the prospective roles are:

- direct DeepSeek V4 Flash for routine question drafting and product
  generation;
- direct DeepSeek V4 Pro only for unresolved disputes after deterministic
  sensitivity checks; and
- local `qwen3.5:9b-q4_K_M` as an advisory diagnostic reviewer only.

Gemma, Claude, and retired local general-Qwen models remain prohibited. Every
external run must prospectively record provider, exact model, transferred
fields or pixels, retention/training state, region where known, calls, cost,
and expiry or deletion procedure. Passing this design does not authorize a
30--50 case pilot or scaling toward 10,000 cases.

## Human audit and failure routing

Each audited case must show the original page or crop, extracted text, source
identifier, page and region, source version and checksum, requested action,
atomic claims, exact evidence quotes, deterministic checks, reviewer
disagreements, and mutation outcomes. No private absolute path or excluded
content enters a committed packet.

Failures are assigned to one primary class: source governance, conversion or
OCR, chunking or evidence-unit construction, retrieval, evidence sufficiency,
generation, citation binding, safety policy, integration, or operations. The
pipeline is refined at that boundary; a different model is not the default
response.

## Staged exit

Stage A freezes and validates the source disposition, control corpus,
conversion lineage, response contract, mutations, and audit packet with zero
model calls. Stage B may authorize a bounded 30--50 case real-source pilot only
after Stage A passes and a specific external-processing record is approved.
Scale remains a later decision based on the pilot's audited failure profile.
