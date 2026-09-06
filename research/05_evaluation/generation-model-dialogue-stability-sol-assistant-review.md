# Sol-low dialogue stability assistant review

**Sol-low fails the prospective zero-critical-error gate.** Both main trials were adequate on all48 targets, but profile trial2 asserts that altered bytes necessarily produce a different digest. The frozen checksum anchor explicitly excludes that guarantee.

| Slice | Trial 1 | Trial 2 |
| --- | ---: | ---: |
| Main useful targets | 48/48 | 48/48 |
| Primary useful targets | 16/16 | 16/16 |
| Appropriate explanatory moves | 12/12 | 12/12 |
| Context-on useful style responses | 6/6 | 5/6 |
| Fully adequate matched profile contrasts | 3/3 | 2/3 |
| Verified critical events in candidate-owned main/profile outputs | 0 | 1 |

The review read all168 main delivered turns and all48 profile responses, including every preceding dialogue turn. Source facts, current questions, approved profile values, excerpts, per-axis judgments and raw hashes are retained in the [trial1 rows](generation-model-dialogue-stability-sol-trial-1-assistant-review.json) and [trial2 rows](generation-model-dialogue-stability-sol-trial-2-assistant-review.json). These are unblinded judgments by an implementation-exposed coding assistant, not independent human validation. No uncertain ratings were identified in this review; uncertainties would be unqualified rather than forced into wins.

In profile trial2, `explanatory-approved-teaching-profile-context-v1-fresh-checksum-question` states: “If bytes were altered, the newly computed digest will differ, allowing the alteration to be detected.” The source describes storing and comparing digests to detect alteration; it does not establish a collision-free mapping. The response turns possible detection into a universal converse. Its later statement that matching digests indicate no alteration *detected* does not withdraw the earlier unsupported guarantee. Trial1 instead states the supported direction: differing digests signal altered bytes.

All main applications preserved the supplied comparisons and results; correct attempts were acknowledged, new topics received starting questions, and both concepts remained distinct in compound responses. Profile escrow responses preserved local spending allowance and total rights; prefix examples retained suffixes and reconstructed complete keys. Context-off responses were assessed for baseline interaction suitability without requiring preferences omitted from their model-facing context. All dispatched profile bindings matched according to the retained request-binding audit; cases without generation are explicitly untested for propagation.

All four run summaries report unchanged source hashes. The trial rows bind those summaries, manifests and raw case/turn files. The group master review owns cross-alias paired counts and final selection; this sidecar does not infer a model win or statistical superiority. Reused contexts and two stochastic trials are not independent learners, source families or representative confirmation. Do not promote Sol or open confirmation on these results.
