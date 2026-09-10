Current production: [live virtual-time demo](live-virtual-demo.md). The earlier films below are retained as superseded iterations.

# Recording preparation

Prepared 7 September 2026. A [2:50 captioned film is now recorded](recorded-video.md).
This folder contains its synthetic recording materials. Use the ordinary product UI for setup,
publication and student entry. The separate service-event replay is a later
chapter, not evidence of a single continuous browser session.

## Start and reset

From the repository root:

```bash
uv run python -m scripts.prepare_recording_materials
uv run python -m scripts.prepare_recording_checkpoint
uv run python -m scripts.start_recording_workspace
```

The second command checks both actual PDF ingestion and publication workflows
and four cited student answers in a temporary API runtime. It does not modify
the running recording workspace. The last command starts one local API and six
ordinary Vite product views. It uses explicit deterministic demo settings,
fresh synthetic accounts in temporary SQLite, temporary source storage and no hosted model calls.
It does not read `.env`, change the selected release profile, or use the existing
API on port 8000. This demo uses synchronous ingestion; do not describe it as
the production asynchronous worker path or the qualified R1 configuration.

| Actor | Start page | Material / student assignment |
| --- | --- | --- |
| Professor A | http://127.0.0.1:5178/professor/setup | [Systems notes](systems-notes.pdf); Student A1 and A2 |
| Professor B | http://127.0.0.1:5179/professor/setup | [Release governance notes](release-governance-notes.pdf); Student B1 and B2 |
| Student A1 | http://127.0.0.1:5180/student | `student-a-synthetic` |
| Student A2 | http://127.0.0.1:5181/student | `student-a2-recording` |
| Student B1 | http://127.0.0.1:5182/student | `student-b-synthetic` |
| Student B2 | http://127.0.0.1:5183/student | `student-b2-recording` |

Use these actor URLs, rather than the professor screen's Student tutor link:
that link shares the professor build's synthetic identity. The synthetic demo
headers are an existing local feature, not the credentialed production login.
Do not show this section as a sign-in/security demonstration.

Ctrl+C in the launching terminal stops only its seven child processes. Starting
again resets courses, messages, sources and approvals. In the professor UI use
Restart session if a cached session is unavailable. In student UI refresh and
start the current course release if the old conversation is unavailable. Keep
the same actor origins throughout a take. The launcher refuses occupied ports.

For a **later-scene retake** on a fresh workspace:

```bash
uv run python -m scripts.prepare_recording_checkpoint --published
```

This creates both courses through the real APIs, submits all five interview
answers, registers source metadata, ingests the actual PDFs, accepts the
synthetic policy previews, approves ten-case teaching-profile previews, runs
release preflight, publishes and assigns all four students. It stops before
student consent and questions, so those can be filmed. It refuses to overwrite
existing courses. Open Course delivery and refresh student tabs afterwards.
The prepared onboarding session IDs are in the checkpoint JSON; a professor's
already open interview is a different session, so do not bind or approve that
blank session over the checkpoint. Film onboarding in the fresh workflow.

Runtime logs and inspectable verification/checkpoint JSON are under
`reports/generated/recording-workspace/` (ignored). The upload fixtures and
source generation script are durable; generated runtime state is disposable.

## Capture setup

- Target a 1920 × 1080, 16:9 output. Use a dedicated, wide browser window with
  browser chrome outside the recording area. The narrow Codex side panel clips
  the open inspector and is unsuitable as the capture region.
- Start at 100% browser zoom. If text is too small on playback, capture a closer
  view or zoom for that shot; do not shrink six complete product screens into
  one unreadable grid. The four-student overview is a separate chapter.
- Keep one scene per take. Hold two seconds before and after each action; move
  the cursor away from the result. Disable microphone for silent source clips.
- Set the recording area once and keep it fixed. Keep file chooser preparation,
  terminal windows, unrelated tabs and notifications outside the footage.
- Use English input and the supplied copy. Paste long answers; edit out typing
  and idle waits. Preserve the real status change and response.
- Before the full take, capture and replay a five-second sample to check crop,
  readable text and cursor. The completed film uses page-only capture.

See [input copy](input-copy.md) and [shot list](shot-list.md). The existing
[full-flow direction](../full-flow-video-direction.md) describes the whole film.

## Evidence labels

Product footage: **Synthetic classroom scenario · Deterministic demo**.
Overview: **Service-event replay · Deterministic baseline**.
Time jump: **Day 2 · Virtual clock advanced by one day**.

The old replay uses seeded source IDs and locators (for example page 2/page 4);
these one-page uploaded PDFs create new IDs and locators. Their text is aligned,
but their provenance is different. Do not splice the old trace into the PDF
workflow as one continuous execution. Rebuild the overview from the captured
release lineage, or explicitly introduce it as a separate synthetic replay.

## Preparation status

- Two readable, synthetic PDF fixtures and all six actor URLs prepared.
- API rehearsal: two real PDF imports, approved/published releases and four
  course-scoped cited turns verified. This is a recording check, not an evaluation.
- Product onboarding screen opened and first answer submitted in the browser.
- In the browser, the published Systems course returned the complete cache
  coherence sentence; its page-1 source region opened. Professor B's view listed
  only Release governance and its two assigned students. Student A1 was returned
  to a fresh chat after this check.
- The completed film combines browser-only recording, four actual conversation
  crops and an explicitly labelled visualization of the separate service replay.

During rehearsal, a standalone topic heading was retrieved instead of its
explanatory sentence. The final PDF layout uses neutral section labels and
complete explanatory sentences. The verifier now requires the relevant fact in
each answer, in addition to a course-scoped citation. This is fixture preparation;
the underlying title-only retrieval weakness has not been fixed or evaluated.
The narrow IAB viewport cropped the inspector. The completed recording instead
uses a dedicated Playwright page at 1600 × 900, composed into verified 1920 × 1080 output.

The later-scene checkpoint does not reconstruct the browser's inline upload
history. Course delivery can therefore show zero uploads alongside the valid
published release. Its next-draft controls may also be blocked by a separate
fresh interview. Use this checkpoint for student-entry retakes; capture import
and approval transitions in the fresh continuous UI workflow.
