# Evaluation result: factual-qa-v3-semantic-role-triage-v1

Date: 2026-08-19

Decision: **Refine; provenance and integrity rules resolve 464 of 602 readable
sources, while 138 require content-level review**

## Method

This no-model pass used only frozen provenance, inventory eligibility, format,
course scope, and integrity-risk rules. It did not infer authority from an LLM
or filename alone.

- Exact hashes in approved `cross-course-portfolio-v2` become authoritative.
- Other clear course-scoped candidates become supporting context and cannot
  independently support factual answer claims.
- Conversion-resolved course-scoped uncommon formats become supporting context.
- Non-document artifacts under assessment-like paths are excluded
  conservatively because they pose a high completed-work risk.
- Assessment documents and unassigned sources remain unresolved.

The private role manifest remains ignored at
`data/interim/factual_qa_v3/source_roles_v1.json`. Its stable record SHA-256 is
`7a7829ac9ca47681d7d8091dbde27371e96524dedbc7acb98714276298080ddf`.

## Result

| Role | Files |
| --- | ---: |
| Authoritative evidence | 32 |
| Supporting context | 253 |
| Excluded integrity/privacy | 187 |
| Excluded duplicate/generated/tool state | 2,027 |
| Content-level review required | 138 |
| **Total** | **2,637** |

The 138 unresolved files are 58 PDFs, 63 text files, six code files, and eleven
structured-text files. Path-level strata are 56 exam/quiz, 30 assignment, 18
tutorial, 12 final, five project, and 17 without a strong assessment marker.
These markers are routing evidence, not final labels: blank question papers,
rubrics, tutorial instructions, completed work, and answer-bearing material can
share the same directory terms.

- Semantic-role gate: failed, 138 unresolved
- External provider calls: 0
- Model calls: 0
- API cost: USD 0
- Private paths or source content committed: 0

## Risk and next decision

Automatically excluding all 138 would be safe for academic integrity but could
discard legitimate teaching instructions and reduce the professor's requested
corpus breadth. Automatically accepting them would risk ingesting completed or
answer-bearing assessments. Content-level review is therefore necessary.

The preferred next method is a private deterministic feature packet followed
by sensitivity-tested model-assisted triage, with only disagreements and
uncertain cases reaching human review. That requires a prospective authorization
record before any model sees private text. The fallback is conservative blanket
exclusion of the 121 assessment documents plus the 17 unassigned sources.

## Decision

**Refine.** Keep the 32 authoritative, 253 supporting, and 179 newly excluded
assignments from this pass. Freeze the 138-file unresolved packet and obtain a
review-policy decision. No factual-QA generation or scale stage is authorized.
