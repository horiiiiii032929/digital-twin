# Request coverage v7

The preserved v6 run improved useful continuation but did not qualify: main43/48
and13/16 were within development gates; the boundary sidecar6/8 failed. Both main
provider-schema failures were `feedback.student_excerpt` longer than200 characters,
not truncation. Boundary failures omitted one of two unavailable requested items
and added an unrequested learner-only access statement that excluded an approved
staff exception. Some correct-attempt responses asked the requested application
back instead of providing it when the approved ladder permitted explanation.

V7 is a distinct opt-in task/configuration; v6 remains reproducible. Three general
changes form one request-coverage discipline:

1. Feedback references the current learner message rather than copying a long
   excerpt in model output. The server displays a length-bounded exact excerpt,
   explicitly labeled as an excerpt; feedback text and factual content are not
   silently truncated. The complete current message remains in the dialogue.
2. Each assessed requested aspect includes an exact current-message request_focus
   and one simple goal: assess_attempt, apply_rule, explain_rule, define_term or
   provide_information. Missing-detail statements derive from all unsupported
   aspect foci. Known partial facts must belong to selected supported requested
   aspects. Separately represent requested assessment and application after an
   attempt; profile permission remains model-assessed, not forced by a keyword.
3. Pure definition steps render selected exact source spans, avoiding unsolicited
   paraphrased policy restrictions. Compound steps retain their other requested
   goals; do not discard explanation, comparison or application. Selected spans
   are not proven to be relevant definitions. Other instructional wording remains
   bounded source-linked prose, with explicit requirements to preserve source
   scope, conditions and role exceptions and omit unrequested policy claims.

The compact proposal removes redundant legacy question_focus, hint_span and
single missing_focus/supported_focus fields. No heavy semantic judge, keyword ban,
fixture-ID branch or automatic semantic-success assertion is added. Source binding
continues to prove only provenance. Definitions can be incorrectly selected;
free prose can still overgeneralize; a goal or current-message reference can be
misclassified. Independent unchanged semantic/zero-critical gates apply.

Mixed missing-evidence responses retain all missing-detail notices. When initial
Socratic withholding applies, offer the supported part or a focused instructional
prompt without copying its solution. Render supported partial factual content
only when the model chooses that profile-compatible path, with explicit partial
ANSWER/citations and unresolved-detail trace. This stage decision is not machine
verified. Typed privacy refusal remains for actual third-party data requests.

Before paid work test long attempts, multiple missing items, pure definition and
compound goals, current-focus/binding failures, actual graph/provider schema and
initial/mature mixed boundaries. Preserve v4/v5/v6 prompts and defaults. Then use
the same consumed48 development contexts, the prior8 boundary contexts and the
separately prepared fresh8 mixed-stage contexts with Luna/3,000-token cap and
finite existing runner limits. Confirmation stays unopened until all development
gates and independent review justify it. Do not chase100% or revise evaluation
criteria to fit results. Register all outcomes and exact configurations.
