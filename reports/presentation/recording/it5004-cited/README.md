# IT5004 cited-final recording

These three silent recordings reuse saved real-AI responses and synthetic learners. No new model response was requested. The registered demo provider remained at 28 calls. This revision changes presentation and user-facing wording, not assessment or planning algorithms.

- `course-setup.mp4`: 50 seconds; instructor configuration, published release, student question, saved answer and source viewer.
- `continuing-support.mp4`: 35 seconds; recorded inactivity-event check-in, saved reply and actual goal state. This is virtual-time event replay, not evidence of unrestricted autonomy. The general notification and unassessed reply remain visible as actual behavior.
- `instructor-review.mp4`: 35 seconds; Maya's saved question, five-learner/five-signal aggregate, actual suggestion, instructor action and saved result. Six active learners is the larger denominator. The pre-decision GET response replays the original saved learning-gap response; interception was removed before the real save request. Saving the review does not publish a new course version.

The actual application was captured with Playwright after the UI labels changed to Digital Twin. The original AI-response text was not rewritten; historical wording inside those responses is retained. Cropping and zooming isolate actual UI regions; no classification, counts, answers or controls were invented. Source recordings are under `output/playwright/it5004-cited/` (local generated data). `shots.json` and `index.tsx` specify the cuts, zooms, cursor indication and subtitles.

## Reproduction

Use the existing Remotion 4.0.522 environment at `output/playwright/it5004-cited/editor/`. Copy `index.tsx` and `shots.json` there. Its `public/` directory contains the converted local recordings. Run the following separately for CourseSetup, ContinuingSupport and InstructorReview, with the corresponding output name:

```sh
node node_modules/@remotion/cli/remotion-cli.js render index.tsx CourseSetup course-setup.mp4 --codec h264 --crf 18 --concurrency 2
ffmpeg -i course-setup.mp4 -an -c:v copy -movflags +faststart course-setup-silent.mp4
```

Use the silent file for delivery. Do not run model generation to reproduce this presentation revision.

## Presentation pipeline

Canonical authoring for this revision is `reports/generated/it5004-cited/build.mjs` and `narration-source.json`, followed by `embed.py`, `citations.py`, `finalize.mjs` and `package.py`. The earlier one-time `prepare.py`, `media.py` and `rename-ui.cjs` are migration helpers, not rebuild steps; they must not overwrite the finalized source. Each finalization requires a fresh final path, preserving previous releases.

Final deck: 70 slides, six chapter dividers, 3,951 spoken words and 120 seconds of video. Notes, source footers and HTML reader are synchronized by the pipeline. Timing is estimated, not a new measured rehearsal. PowerPoint is not installed on the recording Mac; native slideshow playback cannot be certified here.

A final crop cleanup masks the trailing line from the preceding paragraph above the check-question shot (32–38 seconds), without changing any answer text. After CourseSetup rendering, apply `drawbox=x=208:y=380:w=1504:h=65:color=white:t=fill:enable='gte(t,32)*lt(t,38)'` with FFmpeg, H.264 CRF 18 and `-an`. The complete answer is shown in the preceding shot. `finish-media.py` removes audio tracks and validates format and full decoding.
