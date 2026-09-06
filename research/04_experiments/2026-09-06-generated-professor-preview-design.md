# Professor approval of generated teaching previews

This is a prospective design only. Implement after a candidate satisfies its quality gates; it is not evidence that generated previews or professor review have occurred.

## Problem and minimal alternative

The current ten-case teaching-profile preview contains expected-behaviour strings, not model responses. Approval binds their template hash. It cannot demonstrate the selected model's actual teaching behaviour; its generic direct-answer expectation can also conflict with a Socratic preference.

Retain expectations as clearly labelled guidance. Add a bounded POST operation that creates a persistent generated-preview artifact using the exact selected tutoring composition, professor-authored profile draft and permitted source snapshot. Begin with a synchronous bounded operation; introduce a job abstraction only if measured timeouts require it. GET should retrieve the saved artifact without triggering new model calls. Never regenerate samples silently at approval time.

## Binding and trust boundaries

The artifact records the course and owner; profile version/content hash; source IDs, versions, checksums and permission state; candidate, model, reasoning and output cap; prompt/configuration hash; each actual question and preceding dialogue; delivered responses and citations; provider identity, usage, failure status and timestamps; and a canonical artifact hash. Source association must remain labelled separately from semantic correctness.

Avoid a circular dependency on an already-published release: use an explicit draft course/profile snapshot trusted only within an isolated preview namespace. The preview cannot globally approve a draft, publish a release, send outreach, alter real learner state or contribute to instructor learning-gap analytics. Material must already be permitted for the configured external provider. No real student histories are needed; use authored fictional questions.

Professor approval supplies the artifact ID and displayed artifact hash. The server loads the immutable saved artifact, verifies ownership and current profile/source/selection bindings, and records the professor's decisions. Changed profile content, source version/permission, model or prompt makes the artifact stale. The professor must see the actual response and evidence being approved; a matching hash or source identifier is not an automatic teaching-quality pass. Approval retries should be idempotent and must not supersede another profile partially.

Unexpected incomplete generation or unknown usage cannot become an approved complete preview. A deliberately injected provider-failure demonstration is a separately labelled case, not disguised as a successful model response. Retain unsuccessful artifacts and explicit per-case accept/revise decisions; do not generate replacements until a favourable sample appears without recording the earlier sample.

## Evaluation before adoption

Compare the current expectation-only preview with the generated artifact on two contrasting fictional profiles. Test actual response differences through the real tutoring service, then have the professor assess relevance, factual meaning, helpful continuation and teaching style. This workflow supplies reviewable evidence but does not itself establish authentic professor fidelity or learning benefit.

Required contract checks: same-source contrasting profiles produce inspectable actual responses; repeated GET and approval do not generate again; unauthorized course access, stale settings, withdrawn source permission, modified response bytes, missing artifacts and partial jobs reject approval; approved artifact survives restart; preview activity creates no outreach or real-student analytics; approval records exactly the displayed version. Include actual API/UI review before claiming the workflow works. No implementation or provider execution is authorized by this design document alone.

## Authorized development implementation amendment

Implement and test the workflow now with an explicitly experimental, unselected
composition. This supersedes the earlier sequencing suggestion; it does not
promote that composition or claim professor/human approval. No actual provider
execution occurs until a finite provider budget and cases are separately approved.
The first comparison is expectation-only guidance versus saved actual generated
answers under two synthetic contrasting profiles. Injected transports verify
workflow contracts; they do not measure model quality.

Keep approval separate from activation. Approval atomically replaces the latest
approved profile and is idempotent for the identical approved hash. A superseded
profile retains its original approval metadata and remains authoritative only
for the exact currently published release that already binds its ID/content hash.
It cannot authorize a new release. Explicit withdrawal is allowed for that old
profile, invalidates future use and cancels its queued autonomy work. Retain the
existing one-latest-approved index; no automatic approval of historical drafts.

Generated artifacts are immutable, owned and bound to profile, permitted course
sources and actual composition. Approval verifies every displayed case decision
and saved hash without calling a provider again. Incomplete, stale or changed
artifacts fail closed. Tests include failed approval rollback, identical retry,
current-release continuity, withdrawal/outbox cancellation, owner access, changed
source permissions/content/configuration, restart, no GET calls and no real learner
state or analytics. Keep existing expectation guidance explicitly labelled and
retain old APIs; the generated workflow is opt-in and cannot silently replace it.
