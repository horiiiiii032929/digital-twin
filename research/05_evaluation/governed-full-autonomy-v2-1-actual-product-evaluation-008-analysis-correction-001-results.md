# Governed full-autonomy V2.1 actual-product evaluation 008

Decision: **Refine — do not promote or deploy governed T1-v2.1.**

The provider-backed evaluation completed all 820 frozen public-synthetic cases
through the actual tutoring, autonomy, outreach, SQLite, LangGraph checkpoint,
and virtual-clock product services. Hidden gold opened only after every response
was durable. The run used 4,468 provider calls, 2,360,657 input tokens, 318,322
output tokens, and USD 5.5902555.

## Valid result

- T0 grounded control action accuracy: 100% over 150 trajectories.
- T1-v1 reactive action accuracy: 99.33% over 150 trajectories.
- T1-v2 reactive action accuracy: 99.0% over 150 trajectories.
- T1-v2 autonomous aggregate action accuracy: 76.82% over 370 cases.
- Exact proactive action-kind accuracy: 0/290. Every expected
  `send-in-app-check-in` was delivered as `ask-diagnostic-question` instead.
- Unauthorized actions, wrong recipients, wrong course/releases, invalid
  citations, consent violations, duplicate deliveries, unbounded loops, and
  model-owned authority mutations: zero.
- Provider-failure fallback, restart consistency, pedagogical-transition
  validity, and goal termination: 100%.

The causal defect is in the product method, not provider transport. The live
planner receives the complete professor-approved action list rather than an
event-scoped eligible action subset. It therefore selected a valid policy action
that was pedagogically wrong for every proactive check-in opportunity.

## Analysis correction

The immutable raw result is preserved, including two disclosed scoring errors:

1. It counted all reactive turn deliveries against the proactive limit of three
   messages per seven days and reported 697 frequency violations. Recomputing
   from action lineage (`autonomous:` deliveries only) gives zero violations.
2. It compared T0's 150 reactive trajectories with the autonomous condition's
   370 mixed reactive/proactive cases and reported a −23.18-point grounding
   regression. The paired T1-v2-reactive versus T0 comparison is −1.0 point and
   passes the frozen −3-point non-inferiority gate.

These corrections remove two false gate failures but do not change the Refine
decision: the preregistered proactive action/reason/lineage gate requires 100%,
while exact action-kind accuracy was 0/290.

The next method must constrain each durable event to a deterministic eligible
action envelope before model planning. Any confirmation must use a fresh run
identity and fresh cases; the opened 820 cases cannot be reused for a new
confirmatory claim.

## Limitations

- Sources and learners were public and synthetic.
- This does not establish real-professor fidelity, usability, or learning
  improvement.
- Planning and generation used two OpenAI model configurations from one
  provider.
- Provider failures include deliberately injected failure trajectories.
