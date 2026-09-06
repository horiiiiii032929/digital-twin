# Bounded response contract: independent assistant review

Run: `bounded-contract-progression-development-001-live-001`. **Decision: keep the demonstrated contract-handling improvement for development; Refine completeness of service and useful continuation.** The review is unblinded, by an assistant separate from the implementer, not an instructor. No external judge verdict is used as authority.

Reviewed all72 delivered responses with their actual preceding turns: six situations × three order seeds × two versions × two turns. The outputs contain39 distinct situation/stage/action/text combinations; repeats and differing histories were checked. [Sanitized per-case findings](bounded-contract-live-001-assistant-findings.json) retain each question, response, preceding turn, source-membership diagnostic, citations and review-time source hashes. The [existing progression rubric](dialogue-progression-assistant-review-rubric-v1.md) guides interpretation; no post-hoc semantic pass threshold is invented.

## What improved and what remains broken

| Situation | V2 observations | V3 observations | Interpretation |
| --- | --- | --- | --- |
| Five related details | All6 turns fail schema validation | Three grounded answers, two generic questions, one clarification | When an answer is rendered, requested facts are retained; schema success alone hides three instances of unfulfilled assistance. |
| Supported plus absent detail, then narrowed request | Three failures on initial mixed request; two answers and one generic question after narrowing | Three no-evidence responses followed by three complete four-detail answers | Useful recovery improvement; no invented timeout. Initial refusal could name the particular absent detail more clearly. |
| Four queue details, then two-source stored-state comparison | Three queue answers; comparison produces one failure, one generic question, one answer | Two queue answers and one generic question; comparison produces two answers and one generic question | Relevant multi-source explanations work in some repetitions; duplicates and inconsistent selection of teaching move remain. |
| Nine separate details, then explicitly narrowed rule | Three initial failures, three follow-up clarifications | Three initial clarifications, three follow-up clarifications | Initial narrowing is defensible under the bounded contract. Continued referent clarification after an explicitly named narrow question is not useful recovery. |
| Explicit non-attempt | Initial questions and three generic starting-question loops | Initial questions and three generic loops, one naming the topic instead of the phrase “starting question” | No complete answer is prematurely disclosed, but useful starting guidance is missing. |
| History labelled `topic-reset` | Two initial questions, one failure; three explanations after attempt | Three initial questions; two explanations and one generic re-elicitation after attempt | This fixture does **not** change topic: both turns concern amber queue. It cannot establish new-concept reset behavior. |

V2 has14 guarded failures, ten questions, nine answers and three clarifications. V3 has zero guarded failures,14 questions,12 answers, seven clarifications and three no-evidence responses. These are observed action counts, not teaching-quality pass counts. A question can be appropriate withholding or an unhelpful substitute for the explanation requested.

## Content assessment

All21 rendered answer responses across both versions consist of paragraphs found in the approved synthetic card text. Manual review found the requested facts in the rendered five-detail answers: epoch/sequence attachment, epoch comparison, retired-epoch rejection, strict sequence comparison, atomic storage; and queue capacity, order, freed-place admission, duplicate-acknowledgement behavior, and continued waiting. The equal-sequence outcome is implicit in “only if ... greater than”; it is not worked through explicitly. Some comparisons duplicate previously included fragments or add supported context without improving the explanation.

The nine-detail follow-up asks specifically for cobalt ticket's handling of a retired epoch. Every repetition still asks which concept or referent the learner means. That failure is visible even though no schema or provider failure occurs. Similarly, requests for five named facts sometimes receive “what is your current explanation?” instead of those facts. These are substantive adequacy/continuation limitations, not merely cosmetic style differences.

No complete answer was disclosed on either explicit-non-attempt turn in the reviewed Socratic histories. However, “For ‘starting question’, what is your current explanation?” does not actually provide a topic-specific starting question. After a relevant amber-queue attempt, generic re-elicitation persists in one V3 repetition; other responses restate the source without explicitly acknowledging or extending the attempt. No worked-example, learning benefit or stable professor fidelity is established.

## Limits and decision boundary

Three seeds change scheduling/order and supply repeated realizations; they do not provide three independent populations. Four fictional cards describe one synthetic protocol context, not representative heterogeneous courses. The comparison changes the generation contract/prompt composition, not only model quality. The six two-turn situations do not evaluate arbitrary long histories, new-concept resets, deployed auth, or real students.

Retain V2 and its failures as evidence. V3's successful bounded representation and absence handling are worthwhile development improvements, while further candidate work should target concrete explanations after narrowing and meaningful starting questions. Preserve the current Refine quality status; do not replace a semantic judgment with successful parsing or source membership.

Attribution follow-up: the six narrowed named-rule follow-ups have `provider_model=not-called` and prompt `not-built`. The lexical `_UNRESOLVED_REFERENCE_V2` rule matches “explain that” before generation despite an explicit cobalt-ticket referent. This local action-routing false block, rather than a failed model proposal, explains these particular continuation failures. Delivered behavior remains a failure; the later opt-in named-referent comparison preserves this predecessor unchanged.
