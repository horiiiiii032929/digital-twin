# Course-tutor v1.2.3 authoring cross-review results

Result ID: `course-tutor-v1.2.3-authoring-cross-review-002`

Date: 2026-08-12

Status: Codex advisory completed; independent human authoring review pending;
held-out tutor outputs unopened.

Supersession note (2026-08-13): the unfavorable and advisory findings in this
result remain unchanged, but its proposed 152-case manual gate was replaced
prospectively by
[`course-tutor-hybrid-authoring-review-v1`](../04_experiments/2026-08-13-course-tutor-hybrid-authoring-review-v1-plan.md).
This result is not evidence that the replacement gate passed.

Decision: Drop private drafts 002 and 003, preserve their unfavorable
findings, and advance corrected draft 004 to independent human review. Do not
approve, seal, or execute the held-out split. Initiate GitHub server-side purge
of the superseded public commit before treating the privacy boundary as closed.

## Decision question

Does the second independent audit confirm the prior `133 clear / 19 uncertain`
authoring conclusion, and is the corrected dataset boundary safe and rigorous
enough to hand to the independent reviewer?

The prior conclusion did not survive the audit. Draft 002 contained material
privacy, split-isolation, multi-evidence, source-version, and semantic defects.
An intermediate draft 003 fixed those classes but exposed four further
semantic defects during full-family review. Draft 004 is the first candidate
that passes the expanded deterministic and Codex semantic checks.

## Inputs and boundary

- Historical baseline: private draft 001, already rejected.
- Superseded candidate: private draft 002, version `course-tutor-v1.2.1`.
- Rejected intermediate candidate: private draft 003, version
  `course-tutor-v1.2.2`.
- Current candidate: private draft 004, version `course-tutor-v1.2.3`.
- Development cases: 48.
- Held-out authoring cases: 104.
- Scenario balance: 19 cases each for direct, paraphrase, misconception,
  multi-evidence, ambiguity, no-evidence, assessed-work, and
  permission/version.
- Corpus: approved private `it5002-lectures-v1@1.0.0`, processed locally.
- Code base revision: `4c4afe42b9258fc8bd1498745ec14bbb5821eaa6`, with the
  authoring-QA changes dirty during the recorded advisory run.
- Random seed: not applicable; construction and checks are deterministic.
- Held-out tutor outputs, blinded condition mapping, seal, and one-time
  held-out ledger were not opened or created.
- Remote exposure: draft-002 authoring constants were pushed in public commit
  `02dbf8dedf9e5728a3c765b1e6e8616366fc3721`. The branch and PR now point to a
  clean rewritten history, but the superseded object remained publicly
  addressable by SHA at the end of this audit.

The draft-004 hash boundary is:

| Artifact | SHA-256 |
| --- | --- |
| Private authoring blueprint | `e86abe5e6dd4b662fa539ac586dee3ee598d8dee71936eec524b95fca60e004f` |
| Development dataset | `a582ea6806846ceda919a956946edbcbeae7692c5ee199d20d4e9e46a745d018` |
| Development conditions | `b370fd01be047da78435a6cacac874850a6c32a116747714bdfae690cdfddbda` |
| Held-out dataset | `c0aad4979e25de24cb8d0a99f876a47576a534d65257123f95b4edfcb3f000a2` |
| Held-out conditions | `3e855d5f92c903630400d9a2d171e1e29a58b3cb772dbfdc60384ea2dc928bf6` |
| Blank official review template | `af87b21c802f27127188073ebbd4267b84a9878c2fb6bf7ca5fec39bb8f7d804` |

## Audit expansion and corrections

The second pass added checks that the previous review omitted:

1. Private source-derived questions and gold claims must live only in the
   ignored authoring blueprint, not tracked builder or test code.
2. Development and held-out splits may share the approved corpus but may not
   share exact approved passage identities or authored family identities.
3. Every multi-evidence case needs distinct claim-to-passage links, followed by
   human confirmation that both passages are genuinely necessary.
4. Permission/version cases need an excluded conflicting superseded-version
   candidate tied to the active approved replacement, rather than a generic
   instruction-injection note.
5. Source pages used for authoring must exclude answer-bearing assessed-work
   material.
6. Every required factual claim must be complete, atomic, linked in both
   directions to one approved passage, and marked as citation-required.

Draft 002 failed the first four checks and had several multi-evidence claims or
questions that exceeded their exact pages. Draft 003 then failed the fifth and
sixth checks in four inherited source families. All were corrected in draft
004. The slide whose flattened text had ambiguous column ordering was also
rendered and inspected visually; the visual layout supported the authored
claim.

Because the repository is public, rewriting the branch is necessary but not a
complete remote purge. The owner must ask GitHub Support to remove cached views
and pull-request references and run server-side garbage collection for the
superseded commit. No course wording is repeated in this durable record.

## Candidate result

| Advisory disposition | Cases | Share |
| --- | ---: | ---: |
| Clear for independent human confirmation | 114 | 75.0% |
| Uncertain and requiring focused human review | 38 | 25.0% |
| Unresolved LLM-detected issue | 0 | 0.0% |

The 38 uncertain cases are exactly the 19 no-evidence and 19 multi-evidence
cases. For no-evidence cases, an LLM cannot conclusively establish
corpus-wide semantic absence. For multi-evidence cases, the authored passages
support separate claims, but the same LLM should not certify that no alternate
single passage makes one source unnecessary.

The expanded mechanical audit reports:

- 152 cases and 152 conditions with 19 cases in each scenario;
- 114 required factual claims and 114 citation-required claim bindings;
- 19 assessed-work boundaries with scaffold/hints-only behavior;
- 19 excluded superseded-version conflicts with approved replacements;
- zero exact approved-passage overlap between development and held-out;
- zero authored-family overlap between development and held-out; and
- zero filled decisions in the official human review template.

## Citation and multimodal interpretation

Citation structure is internally consistent: each required factual claim is
linked to one approved passage, each passage links back to its claim, and every
required factual claim is marked `must_be_cited`. This establishes citation
identity and authored coverage, not model-output semantic citation quality;
that remains a later blinded evaluation outcome.

The professor-fidelity dataset remains a text-evidence evaluation. Visual slide
inspection was used only as authoring QA where flattened extraction could
misrepresent layout. No multimodal retriever or generator profile is selected
by this result.

## Limitations and human gate

- This remains a single-LLM advisory and not independent human approval.
- Local and active-branch privacy checks pass, but the remote privacy incident
  remains open until GitHub confirms server-side purge of the superseded
  commit.
- The 114 clear dispositions are a prioritization aid, not automatic approval.
- The independent reviewer must decide all six checks for all 152 cases and
  give special attention to the 38-case focus packet.
- A reviewer who relies on this advisory cannot represent the official review
  as `codex_assisted: false`; every case must be inspected independently.
- No professor-fidelity component, policy, retriever, or multimodal profile is
  selected by authoring QA alone.

The current private packets are under
`reports/generated/course-tutor-v1.2.3-authoring-review/`; the focused packet
and machine advisory are under
`reports/generated/course-tutor-v1.2.3-llm-cross-review/`. Both paths are
ignored and contain no committed course wording.

## Reproduction

```bash
npm run build:course-tutor-splits
npm run prepare:course-tutor-authoring-review
npm run cross-review:course-tutor-authoring
```

These commands refuse to overwrite prior artifacts. Preserve each rejected or
superseded private draft before intentionally creating a new revision.
