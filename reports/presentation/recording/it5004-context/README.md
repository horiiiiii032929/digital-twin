# IT5004 context-first demo revision

Three new edits of the saved real-application recordings. The existing presentation and previous videos are retained. This revision adds no model calls and makes no application or algorithm changes.

| Video | Duration | Presentation location |
|---|---:|---|
| Course setup and student answer | 40 s | Existing slide 4 |
| Continuing support | 35 s | Existing slide 39 |
| Instructor review | 38 s | Existing slide 60 |

Total: 113 seconds. These are reviewable replacement videos; the approved PowerPoint has not been replaced in this delivery.

## Editorial changes

- Each video opens with the full application for at least four seconds. Role changes return to a full view.
- Zoom is limited to 1.20–1.30 times the source frame, with surrounding UI retained. There is no white mask or isolated fragment of text.
- Citation opening, Reply in chat, and saving the professor's decision retain their recorded UI consequences. Cursor indications accompany those actions.
- English captions explain the reason to look at each screen. Course setup and publication show already saved settings, not a newly performed onboarding or publication.
- The source citation is shown for a shorter period. The first video now lasts 40 seconds, instead of 50.

## What the recordings establish

All accounts and student messages are synthetic. Responses are saved real-AI outputs; they have not been rewritten or regenerated. UI wording inside historical messages is preserved even where the old word “tutor” occurs. The registered recording provider remained at 28 calls before and after this edit.

The support video shows a saved event under virtual time and the resulting general check-in. It does not stage a new inactivity event or a newly submitted answer. Alex's existing explanation is visible in the conversation. The goal panel records two observations and zero assessed attempts; this is not a demonstrated learning gain or BKT update.

The professor video first shows Maya's specific question, her continued confusion and the withheld follow-up. It then switches explicitly to the professor's aggregate view. Five learners produced five confusion signals for the lecture, out of six active learners in the reporting window. This does not mean all five share Maya's exact difficulty, nor that the dashboard exposes her private chat. The actual proposal is a general rule-based suggestion to review the explanation or add an example; it does not diagnose a specific misconception.

The original professor recording replayed the saved pre-decision GET response from `reports/generated/it5004-final-demo/gaps.json`. That interception was removed before the real decision-save request. The resulting saved decision is retained. This edit makes no new save request and does not publish a course release.

## Reproduce

`shots.json` specifies original source times, duration, playback rate, camera keyframes, click indication and captions. `index.tsx` is the Remotion composition. `source-manifest.json` records SHA-256 hashes of the unmodified converted source recordings. Local source videos live under `output/playwright/it5004-cited/editor/public/`.

Use the existing Remotion environment in `output/playwright/it5004-context/editor/`, containing copies of these two source files, a `public/` directory of the source videos, and the existing node_modules. Run separately for `CourseSetup`, `ContinuingSupport`, and `InstructorReview`:

```sh
node node_modules/@remotion/cli/remotion-cli.js render index.tsx CourseSetup course-setup-render.mp4 --codec h264 --crf 18 --concurrency 2 --overwrite
ffmpeg -i course-setup-render.mp4 -an -c:v copy -movflags +faststart course-setup.mp4
```

Deliver the silent H.264, 1920×1080, 30 fps MP4s. No paid model generation is necessary. Validate full decoding and compare metadata with `validation.json`.
