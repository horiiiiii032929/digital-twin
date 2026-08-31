# Evaluation result: academic-factual-qa-grounding-selection-002 build

## Run identity

- Component: finite #153 actual-product grounding selection
- Date: 2026-09-01
- Base code revision: `7205d262416ef95fa789ccb5702d15e17ae6f492`
- Dirty state: yes; the build was verified before its publication commit
- Instrument SHA-256:
  `9dc562ef220d08ad20114942eeff69a2b06d69d9b0e912c62032a28b0c82af8b`
- Binding SHA-256:
  `7119e3bff9372fc0b9b088878a76d60d33527454f428eed40a42be9e260c47eb`
- Historical retrieval runtime SHA-256:
  `a3a00689c81619eef5a10e6761fae97aaf688d699c9aed713c67c59bc517d951`
- Reproducible commands:
  `npm run validate:academic-factual-qa-grounding-selection-002` and
  `npm run simulate:academic-factual-qa-grounding-selection-002`
- Provider boundary: build-only; zero calls, tokens, and cost
- Machine record:
  `research/05_evaluation/records/academic-factual-qa-grounding-selection-002-build.json`

## Decision question

Is one finite 500-case candidate plus fixed 100-case control checkpoint ready
to decide #153 without another binding, ordering, hidden-gold, resume, or
canary-control failure?

## Method

The candidate freezes deterministic pre-generation action routing, historical
BM25 plus Qwen3 hybrid retrieval, question-targeted atomic evidence release,
and canonical source-range claim/citation validation. The control shares the
same corpus, retriever, generator, and decoding but retains the any-hit release
method.

The direct OpenAI binding names exact `gpt-5.4-mini-2026-03-17`,
`store: false`, structured output, no fallback, zero retries, two public
canaries, 600 product calls, and an absolute USD 50 stop. A typed run binding
requires the instrument, candidate/control manifests, model, prompt, pricing,
code revision, dataset, and exclusive output path. Responses join by exact
case ID rather than provider array position. Hidden gold cannot load until all
candidate and control responses are durable.

## Result

Validation and all five network-free terminal simulations passed:

- completed Keep;
- valid quality Refine;
- canary invalid with zero bulk calls;
- provider invalid; and
- interruption-safe resume.

The preflight correctly reports `blocked-not-authorized` because paid/provider
authority is false, metadata requires a fresh check, the bounded freeze entry
is absent, and the implementation worktree is not yet published. No provider
call or quality measurement occurred.

## Decision

Outcome: **Go Deeper**.

Publish this build as the sole next #153 checkpoint. Immediately before a paid
run, refresh official model availability, identity, pricing, limits, and data
controls, then freeze and authorize this exact instrument. A valid `Refine`
stops the provider-backed autonomy branch. A valid `Keep` may open the already
built actual-product evaluation 002 under the same later program authority.

## Limitations

- This is execution-readiness evidence, not factual or release-quality
  evidence.
- The final 10,000-case package remains known historical evidence and is not
  opened or retuned here.
- Current provider metadata is intentionally marked refresh-required.
- Professor fidelity, usability, learning outcome, and private-course claims
  remain out of scope.
