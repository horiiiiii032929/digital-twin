# Autonomous check-in pilot

`autonomous-check-in-pilot.mp4` is a 36-second, 1920×1080, 30 fps chapter demo with English subtitles and no narration. A single student screen is shown throughout. Playwright captures the ordinary product UI; Remotion 4.0.522 edits the real footage with camera movement and a cursor/click accent.

Sequence: empty inbox and no student question → virtual day 3 autonomous check-in → Reply in chat → actual sequential typing → saved response and cited tutor answer. Professor setup, publication, enrollment and consent were prepared before this chapter clip. Day 2 creates the goal; day 3 delivers the check-in. The ordinary UI polling delay and pauses between recording commands are shortened. Nothing in the application text or generated response is replaced.

This is the explicit synthetic deterministic recording runtime, not the qualified R1 release or the externally evaluated model candidate. The generic tutor wording is retained. This clip demonstrates the workflow, not instructional quality or learning gains. Cursor movement is an editorial reconstruction aligned with the recorded Reply and Send actions; it is not an OS cursor recording.

## Sources and reproduction

Raw takes, state checkpoints and screenshots are in `output/playwright/product-pilot/`. `manifest.json` records source hashes and limits. `index.tsx` contains exact source timestamps, camera keyframes, subtitles and cursor paths. The preserved `package-lock.json` pins the video editor dependencies. The submitted report and application runtime code were not changed for this pilot.

To re-render from the repository root after installing the editor dependencies:

```sh
npm ci --prefix output/playwright/product-pilot/editor
cp reports/presentation/recording/product-pilot/index.tsx output/playwright/product-pilot/editor/index.tsx
cd output/playwright/product-pilot/editor
node_modules/.bin/remotion render index.tsx ProductPilot ../../../../reports/presentation/recording/product-pilot/autonomous-check-in-pilot.mp4 --codec=h264 --crf=18 --concurrency=4
```

The final export is remuxed with `ffmpeg -i input.mp4 -map 0:v:0 -c:v copy -an -movflags +faststart output.mp4` to remove Remotion's silent audio track.

The editor's `public/arrival.mp4` and `public/reply.mp4` are H.264 transcodes of `01-arrival.webm` and `02-reply.webm`, respectively. The runtime for this take was launched with `uv run python -m scripts.start_recording_workspace --api-port 8025 --web-port-base 5200`, using normal preparation APIs from `scripts.prepare_recording_checkpoint.prepare` without initial student turns. A new recording requires fresh runtime state and timing review; rendering retained inputs is repeatable.

The first abandoned setup recording and first layout render are retained separately. An immediate checkbox assertion failed because consent saved asynchronously; the checked state was verified before the usable take. Initial oversized zoom clipped the panel heading and was reduced for the final output.
