# Cross-course benchmark author v2

Draft one retrieval-evaluation case from supplied approved course text. Return
one JSON object and no prose.

For a single-evidence case:

- obey `REQUESTED DIFFICULTY`;
- write a natural student question completely answerable from the target text;
- write one concise required claim;
- copy a complete exact quote that directly supports the claim;
- for `direct`, the question may share important words with the evidence;
- for `paraphrase`, express the concept with materially different wording;
- reject text that is administrative, fragmentary, answer-bearing graded work,
  handwriting-dependent, diagram-dependent, or too trivial to evaluate.

Return:

```json
{
  "query": "string",
  "required_claim": "string",
  "supporting_quote": "complete exact substring",
  "topic": "short label",
  "difficulty": "direct | paraphrase",
  "visual_dependency": "text_sufficient | visual_unsupported"
}
```

For a multi-evidence case, use both target texts. The question must require both
claims; neither text alone may completely answer it. Copy one complete exact
quote from each text in the same order as its claim.

Return:

```json
{
  "query": "string",
  "required_claims": ["claim supported by target A", "claim supported by target B"],
  "supporting_quotes": ["exact quote from target A", "exact quote from target B"],
  "topic": "short label",
  "difficulty": "multi_step",
  "visual_dependency": "text_sufficient | visual_unsupported"
}
```

For a cross-course-confusion case, make the target answerable while reusing
terminology present in the distractor. The distractor must not support the
required claim. Do not ask which course or lecture contains the answer.

For an unusable target, return:

```json
{"reject": true, "reason": "short reason"}
```
