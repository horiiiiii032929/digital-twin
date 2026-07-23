# Professor checkpoint: method and preliminary results

Date: 2026-07-24

GitHub checkpoint: #44 / P0

Status: internal preliminary record; not sent. On 2026-07-23 the reporting rule
changed to reserve professor time for a valid course-specific experiment
result. The first planned external checkpoint is the separate rapid retrieval
result package after one frozen 59-case held-out run, due 2026-07-24.

## Update

I have selected the project direction and evaluation method rather than waiting
for the professor to design them. The final contribution will be a deployable,
professor-configurable, course-grounded tutor evaluated without student
recruitment.

The evaluation combines deterministic safety and grounding checks,
course-specific claim/evidence labels, calibrated LLM judging for subjective
pedagogy, frozen simulated-student trajectories, and scripted synthetic-account
deployment tests. Human usability and learning outcomes are explicitly outside
the supported claim.

## Current status

**Amber, with useful preliminary results.** The project already has reproducible
component evidence and several informative negative results. It does not yet
have a selected live generator, safe returned-context verifier, end-to-end
course RAG result, or deployed application.

The important finding is not that RAG is complete. The existing evidence shows
why a plausible retrieval result and valid citation ID are insufficient for a
safe tutor.

## Preliminary evidence already obtained

| Component | Dataset and denominator | Result | Decision |
| --- | --- | --- | --- |
| Parsing and corpus | 13 IT5002 lectures, 508 pages | All PDFs have selectable text; copied hashes match; provenance inventory is complete | Keep the full local lecture corpus |
| Retrieval v1 | 25 synthetic questions, 9 chunks | BM25 Recall@1 `0.80`, Recall@5 `1.00`, MRR `1.00`, no-evidence accuracy `1.00` | Keep BM25 as the provisional control |
| Retrieval v2 | 40 held-out questions, 40 chunks | BM25 Recall@3 `0.711`; dense `0.676`; RRF `0.755`. Dense alone achieved no-evidence accuracy `1.00`; BM25 and RRF each failed one of six no-evidence cases | Refine; no v2 replacement |
| Evidence sufficiency v1 | 50 held-out cases: 32 answerable, 18 no evidence | The strongest semantic gate reached balanced accuracy `0.736` but produced `5/18` false answers and `8/32` false abstentions | Refine; no safe verifier selected |
| Deterministic generation preflight | 25 synthetic cases | Policy action, citation relationship, graded-work redirect, no-evidence behavior, and required provider suppression all passed `25/25` where applicable | Keep as the structural control only |
| Local Gemma exploratory run | 18 generated answer cases | Structure and citation IDs passed, but only `15/18` answers passed the diagnostic claim-support review | Refine; no generator or prompt selected |
| Course evaluation instrument | 12 private IT5002 anchor cases | `12/12` cases and conditions validate, with 27 atomic claims and 12 hashed evidence passages | Ready for rubric/prompt calibration, not a performance result |

These runs used synthetic data except for the local corpus inventory and private
anchor construction. They do not yet measure course-tutor performance.

## Interpretation

Three conclusions are currently supported:

1. **BM25 is an appropriate inspectable baseline, not a final solution.** It
   remains fast and competitive, while the denser alternatives did not satisfy
   every quality and no-evidence gate.
2. **Evidence sufficiency is the immediate technical bottleneck.** A retrieved
   passage can look relevant while still being insufficient to answer. The
   strongest tested gate both answered unsafe cases and rejected useful ones.
3. **Citation validity is weaker than factual support.** Gemma produced valid
   citation identifiers but added unsupported or mismatched claims in `3/18`
   answer cases.

These negative results justify the next experiments. Adding a more complex
retriever or agent framework before resolving sufficiency and claim support
would not address the measured failures.

## Research question selected

For the frozen IT5002 corpus, professor policy, model configuration, and
deployment revision:

> Does the configured course-grounded tutor improve safe grounded task success
> and pedagogical-policy compliance over controlled baselines, and does it
> preserve those behaviors across frozen simulated-student trajectories and
> deployed synthetic-account tests?

The planned contrasts hold the generator and decoding configuration constant:

- `C0`: generic assistant, no course context;
- `C1`: oracle evidence plus generic tutoring policy;
- `C2`: the same oracle evidence plus the project professor policy;
- `C3`: retrieved evidence plus the project professor policy; and
- `C4`: full approved context, only when it fits safely.

## Evaluation method selected

### Primary outcomes

1. **Unconditional safe grounded task success:** correct answer or safe action,
   all required claims supported, correct citation behavior, and no hard-gate
   failure, divided by all cases.
2. **Professor-policy pedagogical success:** every required applicable pedagogy
   dimension passes. An LLM judge contributes to this result only after
   calibration.
3. **Multi-turn safe trajectory completion:** every frozen checkpoint passes
   and the valid stop state is reached without leakage, policy drift,
   unsupported claims, or operational failure.

### Evaluation portfolio

| Dataset | Inspectable | Sealed | Purpose |
| --- | ---: | ---: | --- |
| `generator-qualification-v1` | 48 cases | 104 cases | Qualify the exact generator and prompt using synthetic oracle evidence |
| `context-sufficiency-v2` | 60 contexts | 150 contexts | Classify returned context as complete, partial, or none |
| `course-tutor-v1` | 12 anchors + 48 development cases | 104 final cases | Course-specific C0-C3 comparison |
| `course-tutor-dialogue-v1` | 16 trajectories | 32 trajectories | D0/D2/D3 multi-turn stress test |

### LLM-judge controls

- deterministic rules remain authoritative for permissions, citations, policy
  actions, latency, cost, and operational failures;
- system identity is blinded and pairwise answer order is swapped;
- a stratified 20% of judgments is repeated;
- a distinct-family judge checks the anchor and 25% of sealed outputs;
- primary use requires agreement at least `0.67`, exact agreement at least
  `80%`, position consistency at least `90%`, repeat consistency at least
  `90%`, and zero false pass on an anchor hard-gate failure; and
- failed calibration makes the LLM score diagnostic only.

The simulated student generates controlled follow-up pressure from a frozen
state card. It never judges tutor success and is not treated as a model of real
student learning.

## Working assumptions I selected

- All 13 official lecture PDFs may be processed locally for the project.
- Tutorials, assignments, exams, answers, secrets, and student records remain
  excluded.
- No human participants or real-student interaction data will be collected.
- DeepSeek remains synthetic-only under the existing cumulative USD 10 cap.
- Course-specific tutor, simulator, and judge processing remains local.
- The project policy and researcher-authored anchor are the frozen reference.
  If the professor later reviews them, that adds an expert-validity check; it is
  not a prerequisite for beginning the planned work.
- Without professor output labels, LLM-judge pedagogy scores remain calibrated
  to the researcher anchor and are reported as proxy evidence.

## Immediate plan

| Date | Work | Evidence produced |
| --- | --- | --- |
| 2026-07-23 to 2026-07-24 | Execute #46: freeze, build, run, validate, and report the separate 59-case R1-versus-R5 rapid checkpoint | First course-specific retrieval result |
| 2026-07-25 to 2026-07-28 | Complete expanded retrieval-v3 and returned-context sufficiency | Confirmatory retrieval and safe-abstention decisions |
| 2026-07-29 to 2026-07-31 | Qualify generator/prompt and end-to-end RAG | Frozen vertical-slice decision |
| 2026-08-01 to 2026-08-04 | Build authenticated persistent staging around the selected or rollback profile | Deployed professor/student application |
| 2026-08-05 to 2026-08-08 | Harden and run simulated, synthetic-account, and final evaluation | Frozen evidence and claim boundary |

The next professor checkpoint should contain the #46 rapid result, the `39`
answerable and `20` no-evidence denominators, uncertainty, latency and resource
evidence, favorable and unfavorable cases, no more than two figures, and a Go
Deeper / Refine / Drop decision. It should state that final Keep selection
requires the expanded confirmatory study and should not ask the professor to
choose the method.

## Feedback requested

I would present the work as a completed research decision and ask for critique,
not permission:

> I selected this method because the current experiments show that retrieval
> relevance, evidence sufficiency, and generated-claim support fail at different
> boundaries. Is the research question meaningful, is the claim boundary
> honest, and which observed failure would you most want me to investigate in
> the report?

## Limitations

- Current quality results are synthetic and mostly single-reviewer.
- The private 12-case anchor is an instrument check, not a performance result.
- No exact DeepSeek configuration, returned-context verifier, or end-to-end
  course profile is selected.
- No simulated-student or LLM-judge performance result exists yet.
- No authentication, persistent storage, or staging deployment exists.

These limitations are part of the reportable result and define the next
experiment; they are not reasons to wait for the professor to design the
project.
