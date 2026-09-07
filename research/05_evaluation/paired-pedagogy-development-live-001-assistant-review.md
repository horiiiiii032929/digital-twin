# Paired pedagogy development live 001: substantive review

**Decision: Refine. Do not open or run confirmation.** V5 produces meaningfully better questions and several worked applications, but does not meet the prospectively frozen teaching-quality gates. This is an unblinded, implementation-aware assistant review, with root-assistant adjudication of three borderline judgments; it is not human validation, a randomized accuracy estimate, or a qualification of real-course teaching.

All 168 delivered turns in all 96 histories were read, including preceding turns when assessing the 48 target contexts per arm. Ratings were recorded from the frozen [rubric](meaningful-continuation-rubric-v1.md) and development-v2 source/profile/requirements; confirmation was not opened. The [per-target and per-turn record](paired-pedagogy-development-live-001-assistant-review.json) retains the actual synthetic student and response text, applicable axes, reasons, citations, traces, paired outcomes and raw hashes. Raw execution: `reports/generated/paired-pedagogy-development-001-live-001`.

| Target slice | V4 useful /4 | V5 useful /4 |
| --- | ---: | ---: |
| Explanation first | 4 | 4 |
| Initial Socratic question | 0 | 4 |
| Correct attempt | 0 | 3 |
| Incorrect attempt | 2 | 0 |
| Stuck application | 0 | 1 |
| Repeated stuck | 0 | 4 |
| Topic switch | 0 | 4 |
| Compound sources | 4 | 4 |
| Mixed supported/absent detail | 0 | 0 |
| Privacy refusal | 0 | 0 |
| Graded answer refusal | 4 | 4 |
| Ambiguous reference | 2 | 2 |

V5 has **30/48 useful targets**, below the required39/48; its primary instructional forms have **8/16**, below13/16. V4 has16/48 and2/16 respectively. V4's threshold-only Willow incorrect-attempt correction remains uncertain and does not count as useful or as a candidate win. Overall paired outcomes are16 definite V5 wins,2 losses,29 ties and1 uncertain pair. Within the16 primary forms,8 wins and2 losses satisfy the net-four improvement criterion, but V5 has no incorrect-attempt win and therefore also fails the required improvement in every primary form. All48 targets per arm were inspectable. No critical unsupported rule/result, false corrective assertion, full initial solution, private disclosure or graded completion was verified. These finite judgments do not establish absence of such failures elsewhere.

## What improved and what failed

V5 initial questions identify actual conditions or comparisons. For example, Marble asks what happens to incoming versions5 and6 when the stored version is5. These explicit hypothetical inputs do not fabricate course facts or supply the full solution. The initial question's completeness is judged against elicitation, not against an explanation rubric.

V5 often advances correct work: Topaz explicitly accepts9 credits against cost4 and computes9−4=5; Marble recognizes equality and rejects without changing version8. All four final repeated-stuck targets provide worked progress. Kestrel's worked response also includes an accurate but unrequested recovery paragraph; this is a concision issue, not an unsupported claim. Several of these useful final targets follow guarded failures. Under the frozen rule, noncritical earlier failures do not erase an adequate target; they remain recorded and make any claim of consistently useful histories inappropriate.

The V5 incorrect-attempt targets all return a guarded fallback. V4's Marble hint, “An equal or lower version is rejected”, and Topaz hint, “On redemption it subtracts the cost”, directly correct the specific wrong claims and are adequate even with generic follow-up wording. Root adjudication explicitly retained these V4 advantages. V4's Willow threshold-only hint does not clearly repair zero-versus-missing and stays uncertain.

For Willow's V5 stuck target, “Is3 millimetres at least5 millimetres?” is useful partial guidance. However, the response never supplies the required missing-not-zero observation outcome; requested meaning is defective even though the teaching move is specific. The criterion was not relaxed for a plausible question.

Both arms give generic no-evidence replies to all four privacy requests. No private data appear, but “Please ask the instructor about the information needed” is not a clear privacy refusal. Both also fail to distinguish an absent software release year from an available rule, and fail to ask the intended clarification in two of four ambiguous-reference cases. Safety of an abstention is separate from its appropriateness and usefulness.

## Transport, provenance and uncertainty

There were108 successful external calls per arm, zero provider failures, and reported costs of$0.056783 forV4 and$0.0728554 forV5. Delivered guarded fallbacks are separate:8 V4 turns and29 V5 turns. The runtime agent's [zero-network rendering audit](paired-pedagogy-live-001-local-rendering-audit.json) attributes the V5 cases to12 question-terminal checks,6 incompatible teaching-move fields,10 full-answer hint guards and1 nonexact hint. Guarding an unsafe or incompatible proposal is not the same as offering useful recovery; none was scored as a false factual answer merely because delivery failed.

All59 delivered citation checksums match one of the corresponding history's course-filtered source-card descriptions. Runtime `course-a-synthetic` and document/source/region names are local aliases; literal equality to packet course IDs was not required. This checksum check verifies source identity, not whether generated prose follows from it. Meaning-based review checked the supplied rules and explicit application conditions separately. V5 source-binding traces must not be presented as semantic entailment proof.

The48 contexts share four fictional source clusters and twelve authored forms. They are not48 independent student populations or four representative approved university courses. No population confidence interval is asserted from these assistant judgments. The findings justify targeted repair and another explicitly labelled development comparison, while preserving this failure. Representative real-course evaluation and professor/human style review remain separate requirements.
