# IT5004 presentation demos

Three silent, single-screen recordings of the actual application: course setup and an answer (70 seconds), event-driven continuing support (45 seconds), and instructor review (35 seconds). They are embedded on slides 3, 35, and 51 of the final 60-slide deck.

## Data and scope

The authorized source is Professor Lek’s IT5004 Lecture 5, `5_introduction_to_enterprise_system.pdf`, SHA-256 `a61a81c0c5e0017e7dd974dd09b29a29c5320ea6fc36f4a1ceae2619e3843418`. Six synthetic students interact with a locally isolated course. The configured teaching preferences do not claim to reproduce the professor’s personal voice.

The actual run made 28 completed calls to `gpt-5.6-luna`, with reported total cost US$0.0276988 and no unknown-cost calls. Drafting used low reasoning and review used medium reasoning through the existing recorded generation roles. The shared budget ledger was closed after the run. This is a product demonstration, not a new quality evaluation or a profile promotion.

Five distinct learners generated five confusion signals. There is no repeated-help group in this recording. The repeated-help example on slide 54 explains a hypothetical threshold separately. The inactivity demonstration used a three-day virtual clock advance, an actual planning call, bounded wording, delivery, and a saved student reply. Observations increased; mastery was not assessed. A professor review decision was saved without rewriting course content.

## Reproduce the edit

Run from the repository root. Local capture files and authorized source material must already be present. Do not regenerate model responses merely to rerender the video.

1. `python3 reports/presentation/recording/it5004-final/prepare_edit.py` converts the 14 existing Playwright captures and writes the shot list.
2. Copy `index.tsx` and `shots.json` into `output/playwright/it5004-final/editor/`. Use that editor’s existing locked Remotion 4.0.522 installation and local `package.json`.
3. In the editor directory run `./node_modules/.bin/remotion render index.tsx CourseSetup course-setup-render.mp4 --public-dir=public --codec=h264 --fps=30`. Repeat with `ContinuingSupport` and `InstructorReview`.
4. Remove the silent audio stream and enable fast start: `ffmpeg -i course-setup-render.mp4 -map 0:v:0 -c:v copy -an -movflags +faststart course-setup.mp4`. Repeat for the other two clips.

The final opening clip also received an editor-header annotation, “Synthetic accounts / real AI / waits shortened”, using an image overlay. This wording is now in the Remotion source for future renders. No answer, classification, or application display text was replaced. English captions and cursor indicators are editorial layers outside or over the actual captured UI. Input and waiting are shortened; readable answers have longer holds.

## Evidence and verification

Local inspectable evidence is in `reports/generated/it5004-final-demo/verification.json`, including provider tasks, action lineage, source hash, cohort counts, code revision, dirty state, and preserved failures. Raw captures are under `output/playwright/it5004-final/`. The initial failed draft and a withheld later answer remain recorded; neither is counted as a successful model-quality result.

`reports/generated/it5004-final-deck/media_qa.py` checks full video decoding and format. `prepare_build.py`, `embed.py`, `finalize.mjs`, and `package.py` in the same build directory create, finalize, render, and package the deck. Use the bundled Python runtime for `embed.py` and the bundled Node runtime for the artifact-tool build. `finalize.mjs` also requires `RUNTIME_NODE_MODULES` and `RUNTIME_NODE` pointing to the bundled dependency paths. Finalization writes a new output path; do not overwrite a previously finalized presentation.

All clips are H.264, 1920×1080, 30 fps, with no audio track. The MP4 bytes inside PowerPoint are checked against the standalone backups. All 60 note bodies are checked against the reader, including the three silent-video cues. PowerPoint is not installed on this Mac; native slide-show playback has not been verified. Browser playback of all three videos passed.
