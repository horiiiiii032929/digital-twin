# V10 generation model and reasoning comparison

Prospective design, 2026-09-06, before any comparison outputs or implementation changes. V10's once-only confirmation remains failed because of a verified unsupported entity attribution. This experiment does not relabel or repeat that packet as fresh confirmation.

## Decision question and prediction

Can a generation model or reasoning change reduce entity-attribution and logical-implication errors without adding response fields or changing the V10 prompt? The prediction is that increased reasoning or model capability may improve these semantic failures, at a measurable latency and cost increase. The alternative is to retain Luna-low and refine the method if no variant passes the prospective diagnostic gates. No model is presumed better from its name or external benchmarks.

## Baseline and alternatives

Compare three explicit generator configurations: `gpt-5.6-luna` with low reasoning, the same model with medium reasoning, and `gpt-5.6-sol` with low reasoning. All use the identical V10 algorithm, typed schema, approved-profile handling, source-association validator and 3,000-token output cap. The reactive and autonomous planner transports remain Luna-low. Default application and release configuration remain unchanged.

A task-routing client sends only the exact V10 generation task to its assigned generator transport. Other supported planner tasks retain the existing Luna-low transport; unexpected tasks fail closed. The factory binds the generator's expected model independently of the planner model, so actual returned identity is never mislabelled. One shared outer budget remains responsible for cumulative calls and cost across roles and restart. Role-specific ledgers capture actual model, reasoning, output cap, task, usage, failures and latency. Recorded request serialization must match the actual transport, including medium reasoning.

The intervention is the generator configuration. Actual generated histories can subsequently change planner decisions; that is a mediated consequence, not evidence that planner configuration was switched. Report this distinction explicitly.

## Dataset and execution

Use the independently authored synthetic entity/implication diagnostic with version and byte hash frozen before dispatch. Keep any known-error replay separate from newly authored cases. The proposed packet has 28 contexts; inspect its public turn counts before finalizing the execution manifest. Gold and reviewer decisions never enter the runtime or provider request. All arms receive the same initial source cards, approved profiles and fixed student inputs; later tutor history comes from actual persistent service calls.

Use one fixed repeat and seed 7801, randomized arm order within each context, fresh isolated runtime/database per arm/context, and at most three concurrent histories. Restart multi-turn histories at the same prespecified boundary in every arm and verify actual generator identity/configuration after restart. Retain every planned outcome, including provider schema rejection, missing usage, local guard failure and cleanup failure. No output-selected retry, changed cap or changed prompt is allowed.

The finite global bound is 500 actual provider attempts and USD 100. Reserve at least USD 0.16 per attempt under the repository's current maximum 20,000-byte serialized input plus 4,096 framing allowance and 3,000 output tokens: the catalogued Sol rates give USD 0.156384. The runner must reject a packet whose conservative three-calls-per-turn requirement across all arms exceeds the bound before dispatch. Increasing reasoning may consume output capacity; truncations remain failures and are not silently given a larger cap. Current price assumptions, all actual usage and unknown-cost failures remain inspectable.

## Metrics and gates

Before outputs, attach the packet author's meaning-based rubric and freeze its exact useful-response, implication/entity, profile and critical-event gates. Report useful contexts, critical errors, uncertainty and all packet slices separately for each arm. Use paired win/loss/tie/uncertain outcomes against Luna-low; do not infer semantic quality from source-ID validity, action or provider completion. Record output-cap failures, tokens, cost, end-to-end and provider latency, local memory, source hashes and host workload. More turns do not constitute more independent source clusters or learners.

Adopt a variant only if it passes the frozen diagnostic criteria and improves the prespecified paired comparison without introducing a critical failure. This is a bounded development decision, not independent confirmation or the project's broader 95%/98% completion contract. Any adopted variant still needs a newly authored, prospectively sealed confirmation and same-configuration application/operational evidence.

## Implementation and verification boundary

Implement only after the current operating evaluation and required repository check release their source freeze. Add the smallest explicit generator-model factory/bridge seam, a default-preserving reasoning parameter in the recorded provider wrapper, and a reusable role-routing configuration behind the existing client interface. Tests must prove exact task routing; fixed planner model/reasoning; generator model/reasoning/schema/cap; response identity rejection; cumulative cost and unknown-usage failure closure; restart configuration; and preserved historical defaults.

Expose each explicit experimental model variant through the same application selector and authenticated application factory, not only an evaluation fixture. An accepted variant's single startup selector must bind its algorithm, role models, reasoning and cap with an observable configuration. Keep the current release/default untouched. Add a named runner with source/configuration archives, full per-case outputs and aggregate summary; register the exact evaluation entrypoint and operation before any external calls. Run an injected contract and an actual bounded schema qualification before the full diagnostic, preserving every named attempt. No private course material is used in this comparison.

## Frozen selection rule

Before any outputs, require at least 24/28 useful contexts and zero verified critical events across every preceding and target turn. A replacement must have at least one more definite paired win than definite loss against Luna-low. Reviewer uncertainty is not a win and does not count as useful. Apply the [meaningful-continuation rubric](../05_evaluation/meaningful-continuation-rubric-v1.md), with the diagnostic packet's explicit entity/implication requirements as the required meanings.

If both alternatives qualify, prefer the variant with more useful contexts, then fewer guarded failures. On a quality tie, prefer lower observed cost, then lower latency; co-resident host activity makes latency a diagnostic tiebreaker, not a production guarantee. If neither demonstrates the required gain, return to method refinement. A Luna-low diagnostic pass does not erase its failed confirmation or justify re-confirming the unchanged candidate.

Before any newly authored confirmation, the chosen replacement must also pass the existing 48-context main, eight-context boundary, eight-context mixed-stage and 24-case profile-handling development gates under its exact model-role configuration. The main includes the prospective 12/12 appropriate-explanation requirement. Prior Luna results do not qualify a Sol or medium-reasoning replacement. Each later evaluation requires its own prospective model-role and budget amendment; the unexecuted V10 Luna real-course scope remains preserved.

## Packet binding before implementation

The independently authored development packet is `reports/generated/fresh-attribution-protocol-v1/entity-implication-development-v1.json`, SHA256 `ce94e18048facd768567907d131c549c15a00b1e049e422751c7f835167558db`. It contains 28 single-turn contexts across 12 synthetic source clusters: unrelated mechanisms, explicitly related mechanisms, implication direction and four boundary cases. Three arms therefore yield 84 target turns and a conservative 252-call requirement, within the frozen 500-call/USD100 ceiling. The execution owner read every development source, question and required meaning before any outputs and found no authoring blocker.

The [diagnostic quality plan](2026-09-06-entity-implication-quality-plan.md) supplements the shared rubric. Archive only this exact development packet and explicitly approved source/plan/rubric files. Its directory also contains sealed material: do not inspect or automatically archive sibling authoring builders or confirmation files. No current or future confirmation contents inform this comparison's implementation or prompts.

### Pre-output challenge revision

Use development v2 instead of the retained, unexecuted v1: `reports/generated/fresh-attribution-protocol-v1/entity-implication-development-v2.json`, SHA256 `acbe1d63b24808d4bcc8d75e071007b3678db67eb421beaa2792d718a4cc2c0f`. Before implementation or outputs, the parent requested that half of the unrelated-mechanism and implication families omit explicit negative cues. The revised required meanings distinguish an unstated dependency from a disproven one, and an undetermined converse from an asserted false converse. Other families retain explicit controls. The execution owner reviewed every changed source/question/required meaning and found no blocker. Counts, gates, model settings and bounds are unchanged; no confirmation file or sibling builder was opened.

## Prospective authenticated variant transport check

The existing six-burst authenticated HTTPS schedule remains a separate, post-selection operational evaluation: 180 actual requests, the unchanged 15-second p95 gate and provider concurrency five. Only explicit model-role variants use new bounds of 800 calls and USD128, partitioned into 400 calls/USD64 per role with USD0.16 reservation per call. This covers up to 360 generation and 180 planner calls without borrowing between roles. A single outer application budget and semaphore cap combined role overlap at five within that process. Existing historical candidates retain 300 calls/USD10. These are process-level limits, not a shared API/worker distributed budget.

Implement and test the variant transport before the comparison source freeze, but do not dispatch this paid timing evaluation until a selected variant passes its required quality gates and the host is quiet after repository checks and operating evaluations. Contract responses verify authenticated application composition and persistence only, not semantic quality or provider capability. Preserve any later negative latency result with the unchanged gate.

## Final budget implementation and qualification sequence

The diagnostic uses six shared recorded ledgers: three arms, each split equally into planner and generation roles. At the 500-call ceiling, integer partitioning gives 83 calls per role, 498 overall; each role receives USD100/6. Every isolated history also has the existing cumulative outer budget, retained across restart. There is no global pooled allowance or cross-process budget; unused role capacity cannot be borrowed. Any stopped role blocks subsequent dispatch through that arm's shared facade, and the orchestrator stops new histories if any arm has stopped. Already in-flight requests still reconcile usage.

After a named injected full-packet contract and source freeze, run a separate six-turn provider-schema qualification: the first two development-v2 contexts across all three arms, maximum 60 calls/USD10, with actual source/packet hashes recorded. This is an openly declared replay before the main development trial, not six additional independent observations. The qualification gate is six inspectable completed runtime turns, valid provider/schema responses, known usage, no budget stop and unchanged source/input hashes. Retain adverse semantic content but do not reinterpret provider acceptance as useful instruction. Any protocol failure stops the main trial; no repaired or selectively retried qualification is permitted without a new prospective decision. If qualification passes, execute the entire 28-context/84-turn diagnostic once under its fixed 500-call/USD100 bounds; keep both named artifacts separate.

## Prospective downstream paired variant wiring

Before paid model comparison, extend the existing V4/candidate paired runner to the explicit role aliases. V4 retains its historical Luna-low transport; only the candidate uses the role router. Retain all historical version defaults and bounds. Model-variant main or new confirmation trials use up to 800 calls/USD128; boundary uses 80/USD12.8; mixed-stage uses 120/USD19.2. The main conservative three-calls-per-turn envelope is 504 attempts, covered without role borrowing. Exact packet and condition sizes remain unchanged. The private 32-context diagnostic, if later authorized after quality acceptance, requires its own model-specific disclosure/budget amendment; no private transfer is authorized by this wiring step.

Input provenance artifacts must be explicitly named for archive inclusion. The default archives only the requested packet, avoiding accidental reads of sibling builders or still-sealed packets. An approved real-course run may explicitly name its already-reviewed source-lineage and reconstruction files. This change affects archive selection, not the model's inputs or historical results.
