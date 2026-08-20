# Evaluation result: factual-qa-v3-semantic-role-triage-v2-correction-001

Date: 2026-08-19

Predecessor: `factual-qa-v3-semantic-role-triage-v1`

Decision: **Refine; retain only provenance-proven authority and return 570
path- or format-routed sources to content-level review**

## Correction trigger

Independent methodology review found that v1 used course path and format to
finalize 253 supporting-context labels and 179 integrity exclusions. Those
signals are appropriate for routing, but they cannot establish content-level
eligibility. Assessment paths may contain legitimate instructions, blank
question papers, or rubrics, while ordinary course paths may still contain
completed work, answers, or private content.

The v1 result remains unchanged as historical evidence. This prospective v2
correction uses `factual-qa-v3-design-002` and does not reinterpret v1 as a
successful semantic gate.

## Corrected method

- Exact hashes in approved `cross-course-portfolio-v2` remain authoritative.
- Existing deterministic duplicate, generated, sensitive, empty, and unrelated
  exclusions remain unchanged.
- Recognized course candidates, conversion-resolved uncommon formats, and all
  assessment-path candidates remain `review_or_conversion_required`.
- No path, extension, conversion success, or model verdict can independently
  establish semantic eligibility or authoritative evidence.

The private corrected role manifest remains ignored at
`data/interim/factual_qa_v3/source_roles_v2.json`. Its stable record SHA-256 is
`a223deebeca752a7d05c425f6462dcc9556304af5f9fae3a810bfcdce9bc6733`.

## Corrected result

| Role | V1 | V2 | Change |
| --- | ---: | ---: | ---: |
| Authoritative evidence | 32 | 32 | 0 |
| Supporting context | 253 | 0 | -253 |
| Excluded integrity/privacy | 187 | 8 | -179 |
| Excluded duplicate/generated/tool state | 2,027 | 2,027 | 0 |
| Content-level review required | 138 | 570 | +432 |
| **Total** | **2,637** | **2,637** | **0** |

The 570 review records consist of 300 assessment-routed candidates, 248 clear
course-path candidates, five conversion-resolved candidates, and 17 remaining
ambiguous candidates. These are review strata, not semantic labels.

- Complete physical accounting: passed, 2,637/2,637
- Proven authoritative promotion: 32 exact approved hashes
- Path- or format-only final labels: zero
- Content-level semantic-role gate: failed, 570 unresolved
- External provider calls: 0
- Local model calls: 0
- API cost: USD 0
- Private paths or source content committed: 0

## Validity and next boundary

This correction increases the review queue intentionally. It prevents false
confidence and does not imply that 570 files require manual review one by one.
After the repository correctness freeze, every candidate first receives a
deterministic local content-boundary screen. A separately authorized,
sensitivity-tested cross-model protocol may then classify eligible ambiguous
records, with human review of all disagreements and a sample of agreements.

Model agreement remains screening evidence, never ground truth. Models cannot
clear privacy alone or promote a source to authoritative evidence.

## Decision

**Refine.** Use the v2 role manifest for prospective work. Keep factual-QA
generation, held-out evaluation, provider execution, and scale closed until the
repository correctness freeze and corrected source-governance gates pass.
