# Revised IT5004 product demos

Three silent real-UI recordings: course setup 70s, continuing support 45s, instructor review 35s. Embedded on slides 3, 35, 52 of the 61-slide deck.

Existing Playwright footage and real-AI responses from `../it5004-final/` are reused; response text is not rewritten. Remotion shot definitions are in `index.tsx` and `shots.json`. Virtual time and shortened waits are disclosed. No additional paid inference was performed.

Recording preparation and provenance: `reports/generated/it5004-final-demo/verification.json`. Revised build helpers: `reports/generated/it5004-polished/`. Render with the existing locked Remotion editor at `output/playwright/it5004-polished/editor`, then run `finish_media.py` and `media_qa.py`. Build slides with `prepare.py`, `build.mjs`, `embed.py`, `finalize.mjs`, and `package.py`, using the bundled runtime. Validation receipts are in the same generated directory.

The support message is a general lecture reminder. The student's subsequent reply returns to their earlier shopping-site question. The actual attempt detector did not recognize an assessed attempt; the goal remains active. The demo proves delivery and persistent observation, not a closed mastery-assessment loop.
