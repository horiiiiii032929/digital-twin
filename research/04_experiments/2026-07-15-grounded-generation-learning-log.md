# Grounded generation learning log

## Component

The first policy-enforced grounded-generation path for issue #24, including a
deterministic control and a disabled-by-default live provider adapter.

## Prediction

I expected citation validation to be the hardest boundary because provider text
can look grounded while referencing evidence that was never retrieved. I also
expected separating policy enforcement from the model call to make no-evidence
and graded-work behavior easier to test.

## How it works

The generator does not immediately send the student's question to a model. It
first removes chunks without tutoring permission and asks a deterministic policy
enforcer for an action. An unapproved professor policy, empty question, absent
evidence, or direct graded-work completion request stops before the provider.

For an allowed question, the prompt builder labels retrieved hits `S1`, `S2`,
and so on and includes only selected policy fields. A live provider must return
JSON containing answer text and those local citation IDs. The citation validator
maps the IDs back to retrieved chunks and constructs citations from trusted
chunk provenance. The provider never supplies the displayed source identity or
locator.

The deterministic generator uses the same policy and citation components but
returns an evidence excerpt instead of calling a model. This makes it a cheap,
inspectable control for testing the surrounding architecture.

## Evidence

- Versioned synthetic generation set: 25 questions in five categories.
- Preflight: 1.00 policy-action accuracy, citation validity, graded-work
  redirection, no-evidence accuracy, and required provider suppression.
- Provider usage: zero input tokens, zero output tokens, no cost, and no network.
- Unit tests cover approved-policy gating, evidence permission, prompt
  construction, valid output, malformed JSON, missing/duplicate/invented
  citations, timeout sanitization, empty questions, and LiteLLM error mapping.
- Reproduction: `npm run verify:generation`.
- A zero-cost local Ollama Gemma 3 4B exploratory run exercised 18 provider
  calls and seven deterministic short circuits. All 25 cases passed policy,
  citation-relationship, and suppression checks, using 13,368 total tokens at
  2,803.5 ms mean all-case latency.
- A post-run strict support audit passed 15/18 model answers. This audit is
  diagnostic because its rubric was not frozen before the run.

## What failed or surprised me

The first generation test helper used `citation_ids or ["S1"]`. An intentionally
empty citation list was therefore replaced by the default valid citation, so the
test did not exercise the missing-citation failure. Changing the condition to
default only when the argument is `None` fixed the test design.

The other important correction was requiring an approved tutor release policy.
Merely passing a `TutorPolicy` object is not enough; a draft policy must never be
used for student generation.

The first local-model smoke response wrapped JSON in a Markdown fence, which the
strict parser correctly rejected. Explicit LiteLLM/Ollama JSON response mode
made the transport contract reliable. More importantly, three otherwise valid
responses cited real retrieved chunks while adding claims those chunks did not
support.

## What I learned

Structured output and citations solve different problems. JSON proves that the
response has a parseable shape. Citation validation proves that referenced IDs
map to retrieved approved evidence. Neither proves that the prose is factually
entailed or pedagogically strong, which must be evaluated separately.

The local run made that distinction concrete: referentially valid citations can
still be semantically mismatched. Entailment or factual-support review must be a
separate prospective evaluation layer, not inferred from citation-ID validity.

I also learned that failure handling is part of the algorithm. Timeouts,
authentication problems, malformed output, and fabricated citations must all
fail closed without copying provider error text or returning unsupported prose.

## Limitations and next decision

The graded-work detector is lexical and can miss paraphrases. The deterministic
answer is an evidence excerpt, not a good tutor explanation. The local run used
one small synthetic corpus, one post-run reviewer, one prompt, and one model;
it did not measure repeated-run variance, tail latency, cold start, or pedagogy.
The next experiment must freeze the answer-quality rubric and review protocol
before output inspection, then compare prompt variants and at least one
fit-for-purpose model against the frozen controls before changing the profile.
