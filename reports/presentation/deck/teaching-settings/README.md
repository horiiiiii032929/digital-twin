# Teaching settings: slides 19–21

Current artifact: `slides-19-21-v3.pptx`. Three reviewable English slides following chapter 2. Earlier approved decks are unchanged.

- 19: Actual React form fields populated with the saved IT5004 explanatory profile. Element screenshots at 2x device scale. The course/governance API responses were browser-local fixtures to render the form; no draft was saved, no approval submitted, and no AI provider called. This is labelled as a form illustration on the slide. Actual component: `apps/web/src/components/professor/professor-autonomy-panel.tsx` ProfileForm.
- 20: Formal editable UML activity diagram and short pseudocode for approval, release binding and per-turn context checks. Source `reports/presentation/diagrams/chapter03/20-teaching-profile-activity-v2.drawio`. Code: TeachingProfileService in `teaching_profile.py`, ReleaseLifecycleService in `publication.py`, `approved_teaching_profile_context` and `profile_authorizes_release` in `teaching_profile_context.py`. Repository parameter and broader publication checks omitted explicitly. A superseded profile can remain valid only for its exact current published release. Editing alone does not change that binding. Invalid context raises an error; no universal client recovery behavior claimed.
- 21: Saved actual V19 first-turn responses, same question and three IT5004 lecture excerpts, Socratic case 0 versus explanatory case 1. Left response is complete; right uses first sentence and final understanding check with an ellipsis for the omitted middle. Observational example, not a single-variable causal estimate or evidence of general reliability or fidelity to Professor Lek.

Response source: `reports/generated/it5004-presentation-teaching-live-002/case-{0,1}-repeat-0-v19-luna-luna-medium/turns.jsonl`. Profile values cross-checked against the generation provider ledger for case 1 turn 0. Both are synthetic teaching settings using actual course material.

Author: `reports/generated/teaching-settings-batch/build.mjs`; diagram author `diagram.py`. Use the bundled Node runtime with `RUNTIME_NODE_MODULES`. Validation receipt `reports/generated/teaching-settings-batch/validation-v2.json`. Rendered slides inspected individually. No PowerPoint-app or timed speaking rehearsal claimed. Notes contain evidence and scope, not a new read-through script.

## Readable design names, 2026-09-09

Latest artifact: `slides-19-21-v3.pptx`. Visible internal generation version labels removed. “Excerpt tutor” means the experimental control that assembles source excerpts/fixed wording. “Audited tutor” means the candidate that generates teaching text and reviews it. Original implementation/run IDs remain in provenance notes and source records. Official model names and implementation identifiers needed to explain actual code are retained. Comparison numbers and release selection unchanged.
