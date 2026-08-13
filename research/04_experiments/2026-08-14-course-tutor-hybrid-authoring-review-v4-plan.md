# Course-tutor hybrid authoring review v4 plan

Plan ID: `course-tutor-hybrid-authoring-review-v4`

Date frozen: 2026-08-14

Status: invalid and stopped after 22 completed private judgments; superseded by
`course-tutor-hybrid-authoring-review-v5`. A 23rd case timed out and remained
explicitly in progress because the implementation incorrectly treated every
provider exception as a hard stop. No held-out authoring case, local private
judgment, human packet, seal, ledger, or tutor output was created.

## Decision question

Can the unchanged 152-case private course-tutor draft be qualified with the
current official DeepSeek V4 Pro reviewer, two local Qwen cross-checks, a
reliable structured-output transport, and no more than 48 independent-human
cases?

V1 through v3 remain invalid preserved attempts. Their judgments are not
reused, and this plan does not reinterpret them or authorize tutor-output
generation.

## Candidate and boundary

- Candidate: private draft 004, version `course-tutor-v1.2.3`.
- Development dataset SHA-256:
  `a582ea6806846ceda919a956946edbcbeae7692c5ee199d20d4e9e46a745d018`.
- Development conditions SHA-256:
  `b370fd01be047da78435a6cacac874850a6c32a116747714bdfae690cdfddbda`.
- Held-out dataset SHA-256:
  `c0aad4979e25de24cb8d0a99f876a47576a534d65257123f95b4edfcb3f000a2`.
- Held-out conditions SHA-256:
  `3e855d5f92c903630400d9a2d171e1e29a58b3cb772dbfdc60384ea2dc928bf6`.
- Cases: 48 development and 104 held-out authoring cases, with 19 cases in
  each of eight scenarios.
- Private course text and per-case judgments remain ignored local artifacts.
- No tutor output, blinded condition mapping, seal, or held-out execution
  ledger may be opened or created.
- Gemma remains excluded and cannot be used as a fallback.

## Authorization and external-data boundary

The repository owner's 2026-08-14 direction to use the proper newest DeepSeek
model for this authoring review applies to this prospective replacement. The
bounded continuation is recorded in
`research/03_data/academics-source-permission.md`.

DeepSeek receives only the same v3 fields: synthetic student question/state,
authored expected behavior, atomic claims, exact approved evidence passages and
metadata, and eight deterministic nearest approved passages for no-evidence
cases. No real student data, participant data, solutions, credentials,
environment values, tutor outputs, hidden condition mapping, other model
verdict, or human decision is sent.

The official endpoint is `https://api.deepseek.com`. Requests use the current
OpenAI Python client directly against DeepSeek's OpenAI-compatible Chat
Completions API and a non-personal `user_id`. V4 permits ten public synthetic
stress probes plus at most two attempts for each of 152 private cases: 314
requests maximum and a cumulative USD 2 hard stop. A second private attempt is
allowed only when the first response is empty or fails the exact JSON decision
contract. A valid approve or revise decision is never retried.

Every attempt records model, fingerprint, input/output tokens, latency,
conservative cost, status, and failure class. The API key and private text are
never emitted in committed artifacts. Provider retention/training remains a
known limitation, and this authorization does not extend to general judging,
professor approval, public deployment, or student-facing use.

## Frozen reviewers and transport

| Reviewer | Model binding | Family | Revision/digest | Thinking |
| --- | --- | --- | --- | --- |
| `deepseek-v4-pro-reviewer-v4` | Official OpenAI-compatible API model `deepseek-v4-pro` | DeepSeek V4 | Official documented `DeepSeek-V4-Pro-0813`; bind one non-empty stress-probe system fingerprint for all private attempts | enabled, `high` |
| `local-qwen3-4b-reviewer-v4` | `qwen3:4b` | Qwen 3 | `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7` | disabled |
| `local-huihui-qwen3-4b-reviewer-v4` | `huihui_ai/qwen3-abliterated:4b-thinking-2507-q8_0` | Qwen 3 derivative | `f5046078f1f6b4dc2ad23265d7d9e616aeb77088bc9092623b2f3f056f7b19d4` | disabled |

The model and API settings remain supported by DeepSeek's current official
documentation: <https://api-docs.deepseek.com/updates/>,
<https://api-docs.deepseek.com/quick_start/pricing/>,
<https://api-docs.deepseek.com/guides/thinking_mode/>, and
<https://api-docs.deepseek.com/guides/json_mode/>.

Before any private request, DeepSeek must complete ten public synthetic probes
with at least nine valid exact-schema decisions. Every completed response must
return `deepseek-v4-pro` and one unchanged non-empty system fingerprint. Any
model or fingerprint mismatch, authentication failure, or fewer than nine
valid probes stops the run. Both local bindings must then pass one public
synthetic exact-schema preflight with their frozen digests and thinking
disabled.

Private empty/malformed first attempts are preserved and retried once. If the
second attempt is also invalid, the case decision remains invalid. Provider
model/fingerprint drift is a hard stop rather than a retry. The cost ceiling is
checked after every completed external response.

## Six authoring checks

Every valid decision returns approve/revise, all six booleans, and a concrete
reason:

1. question authentic and synthetic;
2. expected behavior correct;
3. claims atomic and correct;
4. evidence supports claims;
5. permission and version correct; and
6. split assignment acceptable.

Approve is valid only when all six booleans are true. The scenario-specific
rules from v3 remain unchanged, including the bounded eight-neighbor
no-evidence check and exact claim/passage mapping for multi-evidence cases.

## Two-family cross-review rule

The two local artifacts share a Qwen base family and are not treated as two
independent votes. Outside the targeted human set, approval requires:

- one valid DeepSeek approve decision; and
- at least one valid local Qwen-family approve decision.

This is a two-family approval quorum. A single local artifact's dissent or
invalid response does not escalate a case when DeepSeek and the other local
artifact both approve. DeepSeek revise/invalid/missing, or the absence of every
valid local approval, requires human review. All three decisions and all
dissents remain recorded; none is silently discarded.

## Human audit contract

Sample seed: `course-tutor-hybrid-human-sample-v4`

Before reading v4 verdicts, select one stable-hash case from every
scenario-by-split stratum, producing a 16-case baseline. The required human set
is the union of:

- the frozen 16-case baseline;
- all 19 no-evidence cases;
- every case where DeepSeek is revise, invalid, or missing; and
- every case without at least one valid local approve decision.

The baseline and no-evidence census overlap in two cases, so 33 cases require
human review before model escalation. The hard ceiling remains 48. If the
union exceeds 48, stop and refine rather than transferring the workload.

The packet and reviewer contract remain blinded exactly as in v3. It hides
selection reasons, all model verdicts, and all model reasons; it requires six
checks, approve/revise, notes, reviewer identity/role, timezone-aware time, and
confirmation that model decisions were not inspected.

## Qualification and stop rules

- The DeepSeek public stress gate and both local preflights must pass.
- All 456 private reviewer-case decisions and every underlying attempt must be
  present.
- Every DeepSeek response must retain the frozen model and fingerprint.
- At most 314 DeepSeek requests may be attempted; cost must remain below USD 2.
- The required human set must contain at most 48 cases.
- Every case outside the human set must satisfy the two-family approval quorum.
- Every human-audited case requires six true checks and approve.
- Any human defect blocks sealing and requires a new candidate/review version.
- GitHub Support must confirm removal of superseded public commit `02dbf8d`
  before a seal can be created.

The allowed claim is: cross-provider, two-family model review with targeted
independent-human validation. Full human approval and professor validation are
not allowed claims.

## Measurements

- ten-probe DeepSeek public transport validity, model, fingerprint, latency,
  token use, and cost;
- first-attempt and retry validity/failure classes by split and scenario;
- final valid/invalid decisions and latency/token/cost by reviewer;
- DeepSeek revision consistency and cumulative request/cost totals;
- two-family approval, local dissent, and human-escalation slices;
- baseline, no-evidence census, escalated, and total human counts;
- exact prompt, model/digest/revision, thinking mode, dataset, conditions, code
  revision, and dirty state; and
- unopened-held-out boundary confirmation.

## Reproducibility sequence

1. Validate unchanged draft hashes, schemas, permission amendment, and split
   isolation.
2. Run ten public DeepSeek stress probes and both local public preflights.
3. Bind the DeepSeek fingerprint and run all 456 private decisions, preserving
   every attempt and using at most one malformed-output retry.
4. Apply the two-family quorum and generate the blinded targeted human packet.
5. Complete the independent-human audit without inspecting model records.
6. Validate ensemble and human decisions together.
7. After GitHub purge confirmation, create the immutable seal.
8. Run development only; keep held-out tutor outputs unopened until every later
   prospective gate passes.
