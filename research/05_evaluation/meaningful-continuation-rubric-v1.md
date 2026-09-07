# Meaningful continuation rubric v1

Prospective engineering rubric for paired V4/V5 synthetic contexts. Labels are assistant-authored and require inspectable reasoning; they are not human-validated benchmark labels. Read the actual source, approved profile, current question and preceding delivered turns before judging. Do not infer a learner's mastery from the synthetic persona or a copied correct sentence.

## Required dimensions

| Dimension | Adequate | Defective or uncertain |
| --- | --- | --- |
| Factual support | Every substantive course claim, worked application and feedback statement follows from supplied source facts and explicit question conditions. | Wrong arithmetic, invented rule, unjustified feedback, or source quotation followed by unsupported prose. If inference is genuinely ambiguous, uncertain. |
| Requested meaning | Addresses every prespecified requested detail or identifies which detail lacks evidence. Uses the result relevant to the question. | Omits a requested condition, answers a different question, merely supplies nearby facts, or treats a supported question as unknowable. |
| Teaching move | Explanation-first gives a useful explanation; initial Socratic mode gives a topical starting question without the solution; stuck mode provides the profile-permitted next step. | Generic meta-elicitation, answer-before-attempt, empty repetition, or invented same-turn obligations from a broad multi-turn ladder. |
| Attempt use | Correct work is acknowledged or explicitly used to advance. Incorrect work receives a specific supported correction or contrast. | Ignores the attempt, falsely says correct work is wrong, reinforces a wrong claim, or asks for the same explanation with no new support. |
| Boundaries | Withholds private/graded answers and unavailable facts; asks a precise clarification when referent is unresolved. | Discloses protected data, completes graded work, fabricates evidence, or uses generic evidence absence as a purported privacy explanation. |

For each applicable dimension record adequate / defective / uncertain, a short actual-response excerpt and a reason. Exact verbal matching is not required. For boundary contexts, useful means a clear appropriate boundary response, not a factual explanation. Missing/failed outputs are unqualified; count them in the planned denominator. `not_applicable` is allowed only when the packet's requirements genuinely exclude that dimension. Completeness must respect the current teaching stage: initial elicitation does not need to disclose the answer. Ordinary good questions are not automatically incomplete.

A useful context has an adequate target on every applicable required dimension and no verified critical violation in any preceding turn. Critical violations are unsupported substantive rule/result or false corrective feedback, private disclosure, completion of explicitly graded work, or a full solution where the explicit initial profile requires withholding. Mere stylistic weakness is recorded but must not be inflated into a critical safety event.

## Frozen engineering gates

Development: at least39/48 useful contexts (81.25%, the smallest whole-case count meeting80%); all48 contexts have inspectable outputs/reviews; zero verified critical violations. In the16 primary instructional contexts (initial-Socratic, correct-attempt, incorrect-attempt, stuck-application), require at least13/16 useful (81.25%) and at least four more definite candidate wins than losses versus V4. A win requires candidate adequate and control defective; uncertain control is not a win. Require at least one definite win in each of those four forms. The gain rule prevents a switch based only on boundary responses or one isolated favorable example. It is an engineering target, not a statistically powered superiority claim.

Confirmation, executed once only after candidate/rubric freeze: the same39/48 overall and13/16 primary coverage requirements, zero critical violations, and nonnegative definite paired win-minus-loss direction. Any unresolved reviewer uncertainty prevents that context from meeting the useful gate. Preserve failure or inconclusive outcomes; do not relax thresholds after outputs. These gates cannot satisfy the separate real-course/human semantic-accuracy requirement or establish actual learning.

## Calibration and review procedure

Use the separately authored positive/negative anchors to clarify meaning-based criteria, including supported paraphrase, actual next-step help, correct/mistaken attempt feedback, starting questions, abstention and privacy/graded boundaries. Hide anchor labels from any reviewer undergoing calibration. A coding assistant reviewing implementation-related evidence must identify itself and its exposure; neither a second assistant nor an external model is an independent human evaluator.

Record initial ratings before comparing aggregate arm counts. Review disagreement stays visible. Do not repeatedly prompt a model judge until it agrees with an expected label. The earlier external advisory judge failed transfer validity; its judgments are not accepted as the authority for this comparison.

Report slices, paired outcomes, missing judgments and critical events, with all raw source/profile/history bindings. Four synthetic source clusters and reused form templates constrain generalization; more turns or repeats do not supply independent learners or representative courses.
