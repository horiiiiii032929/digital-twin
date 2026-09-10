# Two-exchange demo review cut

`two-exchange-demo.mp4` extends the previous concrete cache example to two student–tutor exchanges after the automatic check-in. Duration: 31.4 seconds, 1920×1080, 30 fps, no audio. The first answer's hold is shortened to keep the extra exchange within the agreed 28–32-second target. Typing remains 25 ms per character, with the same single-screen zoom and cursor treatment.

The second student message is: “So CPU B must use the updated value of x, rather than its stale cached 0?” This is sent through the actual app in the same saved conversation. The tutor repeats its evidence with a changed introductory instruction. It does not directly confirm the interpretation. The exported subtitle makes that limit visible. This is a review cut of actual deterministic behavior, not a demonstration of successful understanding assessment. No app text was rewritten for the video, no model calls were made, and no application or report code was changed.

`conversation.json` preserves all four delivered messages. `manifest.json` identifies the recording and review finding. The previous arrival and first-reply recordings remain in `output/playwright/product-pilot-v2/`; the new take is `output/playwright/product-pilot-v3/follow-up.webm`. `index.tsx` specifies source timestamps, captions, camera movement and the reconstructed cursor. Dependencies are the same locked Remotion 4.0.522 environment used for the first pilot.

To re-render the prepared editor:

```sh
cd output/playwright/product-pilot-v3/editor
node_modules/.bin/remotion render index.tsx ProductPilot render.mp4 --codec=h264 --crf=18 --concurrency=4
ffmpeg -i render.mp4 -map 0:v:0 -c:v copy -an -movflags +faststart two-exchange-demo.mp4
```

Review: check that both exchanges concern the same concrete example, second typing is readable, camera follows the new message rather than the old answer, citations remain visible, and no subtitle implies assessed learning or a direct confirmation that the app did not produce. The usefulness of the second response remains a product limitation; adding a turn alone does not resolve it.
