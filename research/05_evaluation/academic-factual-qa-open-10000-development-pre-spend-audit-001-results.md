# Open factual-QA development pre-spend audit

Result ID: `academic-factual-qa-open-10000-development-pre-spend-audit-001`

Date: 2026-08-27

Status: Complete network-free audit

Decision: **Refine the reference extraction and question layer before product
execution.**

## Result

The 500-case AFQC-044 package remains valid deterministic truth scaffolding:
all 500 public IDs match separate hidden-gold rows, the 400 answerable cases
retain exact source-range lineage, the 100 boundary cases retain empty lineage,
and there are zero normalized duplicates, public gold fields, canonical-answer
leaks, or lineage defects.

It is not yet fit for the 500-case T0 product evaluation. A prospective
fitness-for-use audit flagged 227/400 answerable cases (56.75%) across 68/100
source clusters for at least one high-risk reference-answer or modality
condition:

| Diagnostic | Flagged cases |
| --- | ---: |
| Possible fragment start | 169 |
| Possible fragment end | 92 |
| Raw markup or runtime artifact | 60 |
| Structured-code signal missing | 12/35 |
| Structured-equation signal missing | 4/6 |
| Structured-table signal missing | 3/3 |

These are conservative deterministic flags, not 227 independently adjudicated
semantic defects. A 12-case Codex-assisted priority audit confirmed that the
risk is material rather than cosmetic: five representative cases had unusable
reference answers or mismatched structured evidence, three required wording or
boundary refinement, and four were usable controls. This was model-assisted
review, not independent external human annotation.

Representative confirmed failures include:

- `academic-open-dev-0100-q1`: the expected answer begins mid-sentence and
  contains raw LaTeX markup;
- `academic-open-dev-0019-q4`: two extracted evidence spans are fragments rather
  than a coherent multi-evidence answer;
- `academic-open-dev-0068-q4`: the selected code answer is a truncated runtime
  snippet;
- `academic-open-dev-0092-q4`: the selected answer is not an equation; and
- `academic-open-dev-0098-q4`: the selected answer is prose despite the
  structured-table label.

## Cause and evaluation risk

The source allocator correctly records that a window overlaps code, equation,
or table markup, but the deterministic answer extractor then chooses early text
spans without targeting that semantic region. General source windows are
token-aligned rather than sentence-aligned, so their first extractable span may
start or end mid-sentence. Finally, all 500 questions are deterministic
development templates; several cues are understandable but not realistic
student wording.

Executing T0 now would confound Digital Twin quality with defective reference
answers and artificial questions. A failure could be caused by bad gold, while
a pass on a mislabeled structured case would not demonstrate the intended
capability. Provider reliability or budget cannot correct this validity issue.

## Required successor

Preserve AFQC-044 and this unfavorable audit unchanged. Build one prospective
development successor that:

1. aligns text evidence to complete source statements;
2. binds structured cases to the exact detected code, equation, or table region;
3. rejects fragment, markup/runtime, and modality mismatches before writing;
4. keeps actions, answers, claims, citations, and boundary reasons deterministic;
5. applies provider-neutral question paraphrasing only after the truth package
   passes, with canonical fallback and duplicate/leakage quarantine; and
6. reruns this same audit plus a bounded model-assisted semantic packet before
   requesting paid product execution.

The sealed final 10,000 cases, paid provider calls, private data, visual work,
Professor Digital Twin fidelity, and deployment remain closed.

## Provenance and limitations

- Audited dataset build revision: `fdf571c`.
- Audit implementation revision: `d6d0419`.
- Audit scope: committed 500 public cases, separate 500 hidden-gold rows, frozen
  100-cluster public source plan, and 12 priority examples.
- Provider calls, tokens, cost, private-data access, and final-split access: zero.
- The diagnostic rules are deliberately high-recall. Their aggregate counts
  establish a pre-spend risk gate; they are not substitutes for future semantic
  validation of the corrected package.
