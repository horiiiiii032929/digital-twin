# Cross-course benchmark author v1

You draft one retrieval-evaluation case from supplied approved course text.
Return one JSON object and no prose.

For an answerable case:

- Write a natural student question that can be answered completely from the
  supplied target text.
- Do not mention page numbers, filenames, lecture numbers, or the course ID.
- Prefer a conceptual question or applied explanation over copying a heading.
- Write one concise atomic required claim.
- Copy one exact supporting quote from the target text. Do not alter
  whitespace, spelling, punctuation, or capitalization inside the quote.
- Mark difficulty as `direct`, `paraphrase`, or `multi_step`.
- Mark visual dependency as `text_sufficient` only when the printed words alone
  support the claim. Otherwise return `visual_unsupported`.

For a cross-course-confusion case:

- The question must be answerable from the target text.
- Incorporate terminology also present in the distractor text.
- The distractor must not support the required claim.
- Do not ask which course or lecture contains the answer.

Required JSON keys:

```json
{
  "query": "string",
  "required_claim": "string",
  "supporting_quote": "exact substring of target text",
  "topic": "short label",
  "difficulty": "direct | paraphrase | multi_step",
  "visual_dependency": "text_sufficient | visual_unsupported"
}
```

If the target text is administrative, fragmentary, answer-bearing graded work,
dependent on handwriting, or impossible to turn into a defensible text-only
case, return:

```json
{"reject": true, "reason": "short reason"}
```
