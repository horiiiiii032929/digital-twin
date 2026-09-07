# Next boundary after final-audit failure

Decision proposal, 6 September 2026. No implementation or provider calls. V2 stopped after 24 calls: twelve inputs reached, 100 blocked, one 30-second timeout with unknown cost and zero repairs. The observed Nelwick converse surviving both auditors also prevents its zero-critical gate from passing. Keep the frozen label and run evidence. Do not run the fresh bank on the strength of other improvements.

## Recommended next experiment

Test a small **approved relation contract with deterministic inference and controlled factual rendering**. Reuse existing source lineage and claim-validation interfaces. The valuable change is that a successful model judgment no longer authorizes an implication direction absent from the approved contract. Another free-text verifier, including a symbolic checker fed unchecked model translations, would retain the same trust gap.

This could materially help courses with explicit prerequisites, Boolean conditions and small decision tables. It cannot certify arbitrary lecture prose. Begin with a bounded component comparison; no knowledge-graph service, general theorem prover or new product integration is justified yet.

## What the repository already provides

`src/digital_twin/grounding/semantic_evidence_atoms.py` materializes immutable source text with canonical claims, source versions/checksums/ranges, semantic anchors, parent groups and adjacent/related atom IDs. Its relation metadata groups source passages; it does **not** encode a directed logical implication, equivalence, quantifier, exception or proof rule. “Related” is not “entails.” The source-side derivation avoids question/gold contamination but does not constitute instructor approval of a formal interpretation.

`grounding/models.py` supplies `AtomicAnswerClaim` and `ClaimSourceBinding`; the latter explicitly represents provenance rather than entailment. `grounding/claim_validation.py` already supplies a verifier protocol and a fail-closed `AtomicClaimEvidenceValidator`, with contiguous quote, canonical-source equivalence and NLI alternatives. These are reusable comparison points. Exact quotation can preserve wording but cannot prove a new scenario conclusion; NLI scores remain fallible. Validation of every *declared* claim does not establish that every claim in arbitrary rendered text was declared.

The missing authority is a reviewed source-to-relation mapping and an output path that cannot append undeclared factual prose.

## Minimal contract and interface

An immutable `ApprovedRelationSet` binds source ID/version/checksum and exact source spans to explicitly reviewed predicates and directed rules. Each rule records antecedent, consequent, scope, approval state/version and mapping rationale. Equivalence requires two approved directions; an implication never creates its converse. Ambiguous text is marked unresolved and supplies no disputed direction. An LLM may propose mappings for review but cannot activate them. Synthetic author/reviewer approval must be labelled separately from actual instructor approval.

Use bounded Boolean predicates and simple registered cardinality comparisons first, without arbitrary quantifiers, causal counterfactuals or unit conversions. Limit a problem to twelve ground predicates; exhaustive valuations provide a simple inspectable control. `verify_query(relations, scenario_premises, query)` returns `entailed`, `contradicted`, `undetermined`, `invalid` or `outside_scope`, plus rule IDs and a proof/countermodel. No closed-world inference: failure to prove success is not proof of failure. An inconsistent premise/rule set is invalid, never vacuously certified.

Keep premise grounding separate: instructor/source facts are not interchangeable with a student's mistaken attempt. Explicit hypothetical conditions may bind the current scenario only. The first component set supplies typed scenarios with separately reviewed text bindings; this tests inference and rendering, not automated natural-language parsing. A later parser must be evaluated independently, including entity, time and condition scope, before any end-to-end claim.

`render_verified_response(request_contract, verified_results, teaching_move)` emits only server-owned factual templates whose slots reference verified results or literal approved spans. Preserve requested-aspect coverage and existing privacy/teaching permissions. An LLM may choose among permitted teaching moves and approved examples; free-text factual additions remain outside this guarantee. For existing arbitrary prose, quarantine unverified assertions rather than claim that unchecked claim extraction made the entire response safe.

Optional-unit pruning is secondary: delete only an entire unit designated optional by a server-owned request contract, with no dependent references, and recompose/recheck coverage. If a unit mixes the required negative answer with an unsupported positive example, it cannot be deleted safely. Controlled rendering can construct the supported required answer without ever adding that example.

## Smallest useful integration, conditional on evidence

Avoid a separate demonstration solver disconnected from tutoring. The prospective integration has three small seams: attach approved relation-set IDs to the existing registered source ranges; let the existing request/typed-proposal boundary reference a finite scenario and query IDs; adapt the existing claim validator/composer to verify and render those results. Retrieve the original passages through the existing atom machinery, resolve approved relation IDs server-side and retain the same citations, profile context and turn traces. Do not build another retrieval index or let public questions create rules. The existing atom machinery should be reused for lineage/search; it cannot replace the missing direction/scope/approval semantics.

A first integrated slice should answer actual prerequisite/eligibility and small decision-table tutoring questions, show which source condition is missing, and ask a permitted concrete cue instead of a direct result under a Socratic profile. Both the required negative answer and optional example must pass the same checked renderer. Two unrelated rule systems and both teaching profiles must traverse the actual composer, with restart/source-version invalidation tests. Inputs outside the declared finite slice remain explicitly outside the new guarantee; they retain the currently selected evaluated product path, not the rejected V2 audit. Within the slice, unknown mapping or premise binding fails closed.

The principal near-term cost is annotation and request grounding, not inference. If no instructor-reviewed real-course rules or independently credible source mappings can be obtained, this remains a synthetic research component and cannot be presented as an immediately qualified product improvement. Stop after the bounded comparison if the useful slice is negligible, annotation effort dominates the intended tutoring benefit, or automatic premise grounding reintroduces the original error. In that case retain quotation/approved worked examples for high-risk rules, report the limitation and drop broader symbolic integration rather than expanding infrastructure to make a benchmark pass.

## Nelwick ambiguity and fixed evaluation

The source says the checklist “requires exactly two” seals and that one or three fails. A literal necessary-condition reading supports failure at three; it does not explicitly assert success at two. An ordinary reader may pragmatically understand this short checklist as a complete acceptance specification, especially because it says “this checklist” rather than shipment authorization. That makes the mapping a real interpretation question, not a formal proof supplied by English wording alone.

Retain the frozen unsupported-converse label for the existing study and disclose this interpretation sensitivity. Do not retrospectively turn an adverse result into a pass. For new evidence, contrast explicit “only if; further approval may be needed,” explicit “if and only if,” and intentionally unresolved “requires” passages. An instructor can approve a complete decision table or clarify sufficiency in a new source version. That changes authoritative knowledge prospectively; it does not prove what the old passage meant.

## Bounded evaluation and decision

Compare (A) existing quote/canonical-source control, (B) frozen model audit on any already available outputs as descriptive context, and (C) approved relations plus controlled rendering. Add an explicit ablation with model-proposed but unapproved relations blocked, demonstrating that schema validity cannot grant authority.

Prospectively author 32 independent source/scenario packs, six cases each (192 total): eight necessary-only, eight explicit equivalence, eight ambiguous/incomplete and eight scope/exception/inconsistent/no-evidence packs. Each pack tests a supported conclusion, unsupported converse, supported negative/boundary, missing premise, mixed required-answer/optional-error and a teaching-policy contrast. Independently review source mapping and text cases before outputs; split by source pack, not paraphrase. Preserve all failures. Seed any generated variants and freeze source/mapping/parser/renderer versions separately.

First run deterministic local tests only: zero provider cost, exhaustive supported-fragment truth-table checks, lineage/version/approval tampering, missing-claim coverage and no undeclared factual output. Require zero invalid-rule releases, no converse success without a sufficient rule, all inconsistent/ambiguous cases handled conservatively, and complete requested answers on all in-scope answerable fixtures. Compare exact quotation's low-risk but lower-application-coverage baseline. Report usefulness, abstention, unsupported releases, scope coverage, author/reviewer minutes, memory and latency by pack/family; abstention is not a useful answer when the case is answerable. Report source-pack uncertainty and limitations rather than treating 192 dependent cases as 192 independent course deployments.

Progress only if the candidate adds supported applications beyond quotation without unsafe releases, and review effort is practical. Then evaluate natural-language premise binding and profile-aligned tutoring on fresh inputs before integration. This is a narrow, testable correctness boundary, not a route to declaring a complete autonomous teacher formally verified.
