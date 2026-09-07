# Source–oracle alignment and fixed-candidate rerun

## Decision, prediction and alternatives

The v2 main dialogue source gives B⇒A (an action requires a condition), while
some gold responses demand A⇒B (the condition guarantees the action). The
[oracle audit](../05_evaluation/meaningful-continuation-v2-oracle-audit.md) records
an explicit Topaz countermodel and affected historical evidence. The decision
question is whether the unchanged V14-medium candidate supports meaningful
teaching under an unambiguous procedure and preserves necessary-condition limits
when the source actually states a constraint.

Keep v2 and its run results immutable. Do not alter the model or relax gates.
Reject interpreting every only-when sentence as if-and-only-if, which would make
the independent logic controls inconsistent. Instead publish v3 complete procedure
sources plus a separate original-source necessary-condition diagnostic. Prediction:
source/gold agreement permits meaningful dialogue evaluation, while the diagnostic
still exposes unsupported positive guarantees.

## Dataset and implementation

A reproducible builder reads only the exposed v2 packet. Replace the four primary
synthetic procedure definitions with explicit positive and otherwise branches,
version those sources, update verbatim quoted learner attempts and support spans,
and retain all48 context IDs, question purposes, profiles and stages. All changes
and hashes must be inspectable. No sealed confirmation or private source is read.

Build eight explanatory single-turn diagnostic cases using the original four
primary sources: a positive-condition question asks whether the action is
necessarily established, and a negative-condition application asks for the
explicitly supported rejection/hold/postponement. Gold requires non-guarantee in
the former and the correct negative outcome in the latter. Keep the source text
unchanged and the public payload free of gold. Four paired scenarios are not
eight independent population samples.

Add a small truth-table audit over explicitly authored source/gold abstractions:
B⇒A permits A=true/B=false, whereas explicit complete behavior A⇔B does not.
This verifies the stated abstraction, not arbitrary natural-language entailment.
Tests cover the countermodel, old bytes preserved, source/version/span alignment,
public/gold separation, counts and strict comparison/equality boundaries. No
new product algorithm, provider role or release selection is introduced.

## Frozen evaluation and acceptance

After dataset review and injected runner checks, execute two v3 main trials with
schedule seeds8201/8202 using v14-luna-sol-medium versus V4. Each is bounded at
1200 calls/USD192. Execute the eight-case constraint diagnostic through the same
paired runner at120 calls/USD19.20, seed8201. At most two runs overlap; total2520
calls/USD403.20. No output-selected retry; retain failures and unknown usage.
Exact runtime/prompt/model hashes must match the preceding V14-medium Stage B;
new dataset/tooling provenance is recorded separately.

Retain main gates: at least92/96 useful targets, each trial at least39/48 and13/16
primary, every trial12/12 explanatory targets, zero critical errors over all
candidate turns, complete histories, known usage and unchanged snapshots. Require
8/8 constraint-diagnostic targets and zero criticals. No pass is inferred from
source association or model verdicts. Report per-case outcomes and prior turns,
slices, V4 differences, latency, tokens and cost. The original v2 main aggregate
remains unqualified even if v3 passes.

Reuse only unchanged, already reviewed V14-medium short28, profile12 and boundary/
mixed8+8 results; their exact product composition must match. Source-dependent
main scores are not transferred. Passing these gates allows the existing untouched
confirmation protocol to proceed once; course transfer, broad400/200/200 evaluation,
24 longitudinal histories and browser qualification remain separate. Root-only
semantic review and exposed synthetic data limit generalization and instructor
fidelity claims. No default or deployment change is authorized by a development pass.

## Execution clarification before dispatch

Run with the unchanged isolated Stage B runtime at
`/tmp/digital-twin-v14-medium-stage-b-20260906`, passing the new versioned packets
as explicit input artifacts. This preserves every prior runtime hash, including
the frozen execution registry. The working repository adds only a bounded dataset
builder authorization and registry entry; that administrative change is not
loaded into the evaluation runtime. Archive the new builder, tests and plan
separately. No source text, prompt or provider implementation in the isolated
runtime is edited. Root reviewed the four explicit positive/otherwise branches,
the eight original-source diagnostic questions and gold, strict greater-than versus
equality, rainfall threshold, and credit subtraction/rejection cases before calls.
