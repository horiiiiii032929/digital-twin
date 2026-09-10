# Concrete, faster product demo

`concrete-cache-demo.mp4` is the revised 24-second, 1920×1080, 30 fps video. It uses the original deterministic recording runtime with a concrete synthetic Systems lesson: both CPUs cache zero, CPU A writes one, and coherence prevents CPU B from reusing its stale zero. The student's actual question asks what CPU B reads next and why. The actual tutor response includes the relevant course statement and citation. This remains a deterministic workflow demo, not evidence of adaptive teaching quality.

Compared with the 36-second pilot: 33% shorter; typing delay reduced from 65 ms to 25 ms per character; faster camera transitions; idle pauses shortened. One screen throughout. Application messages are not rewritten or replaced in the edit. The cursor is a reconstructed editorial overlay aligned to recorded clicks. Synthetic accounts and virtual time are disclosed onscreen. Onboarding, source approval, publication, enrollment and consent are prepared before this chapter clip.

## What the retakes found

A bounded attempt to use existing experimental V4 generation with Luna low did not produce a reliable demonstration. All attempts are retained in `output/playwright/product-pilot-v2/`:

- Initial PDF: source-specific planning and proactive excerpt delivery worked; the attempted misconception-check reply was withheld. Its proposed evidence differed from the PDF's line-wrapped text.
- Revised paragraph PDF: the observer selected a short definition chunk rather than the full worked example; the planning result fell back to the bounded policy control. This take was not selected for the final video.
- Single-paragraph Markdown: the proactive excerpt contained the concrete CPU example. The misconception-check reply was still withheld. The model proposed a hint identical to its entire proposed answer span, which the existing V4 contract rejects.
- A subsequent fresh-chat reply to the same check-in returned HTTP 500. Its cause has not been fully diagnosed; it must not be presented as a working recovery path.

These are recording QA observations, not a controlled model comparison. Changing the PDF formatting alone did not resolve the candidate's limitations. No validation rules, model prompts or selected release profile were weakened or changed. The final take uses a separate student and the original deterministic runtime, with the concrete Markdown source. This establishes that particular workflow, not that the experimental misconception/recovery paths are complete.

External recording trial: 12 calls to `gpt-5.6-luna`, low reasoning, 3000-token output cap, US$0.0048518 reported cost from a US$1.92 reservation. No Sol calls. The trial API process was stopped after capture. Costs are in the cumulative budget ledger. `experimental-failed-traces.json` preserves recorded reactive traces; full provider inputs/outputs remain in the raw directory.

## Reproduction and verification

The editable composition is `index.tsx`. The private editor is `output/playwright/product-pilot-v2/editor/`, using Remotion 4.0.522 and the original pilot's locked dependencies. Its `public/arrival.mp4` and `public/reply.mp4` are H.264 transcodes of `baseline-arrival.webm` and `baseline-reply.webm`. Source timestamps and camera coordinates are explicit in the composition.

```sh
cd output/playwright/product-pilot-v2/editor
node_modules/.bin/remotion render index.tsx ProductPilot fast-final.mp4 --codec=h264 --crf=18 --concurrency=4
ffmpeg -i fast-final.mp4 -map 0:v:0 -c:v copy -an -movflags +faststart concrete-cache-demo.mp4
```

Recording-only controls gained an explicit model-backed sandbox identity while retaining the old default and local-only control header. `uv run pytest tests/test_recording_virtual_clock.py -q`: 3 passed, including rejection of unnamed/production runtimes. The submitted report and selected application defaults are unchanged. The retained `recording_app.py` and `prepare_retake.py` document the experimental composition and retake preparation; they are run-specific helpers, not release entrypoints, and should not be run against an already-used trial directory.
