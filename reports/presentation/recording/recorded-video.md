# Recorded presentation film

Recorded and edited on 7 September 2026.

The MP4 at `reports/generated/recording-film/course-digital-twin-demo.mp4` is
2 minutes 50 seconds, 1920 × 1080, 30 fps, H.264 and silent, with English chapter
titles and captions. It is intended for narration during the online presentation.

## What appears

| Time | Chapter |
| --- | --- |
| 0:00 | Two synthetic instructors and four students |
| 0:07 | Professor A onboarding interview |
| 0:31 | Source metadata and permission |
| 0:45 | Synthetic preview and release checklist |
| 0:57 | Actual PDF upload, release checks and publication |
| 1:17 | Professor B's separate course |
| 1:22 | Student consent to private check-ins |
| 1:33 | Student A1's actual question and reply |
| 1:47 | Actual citation and source region |
| 1:55 | Four recorded conversations displayed together |
| 2:11 | Professor B's actual pause operation |
| 2:23 | Separately executed service replay: scheduled opportunities, virtual next day, delivery and retry |
| 2:44 | Closing scope |

## Capture and editing

Playwright CLI captured only the browser content at 1600 × 900. No desktop,
browser tab strip, address bar, notification or microphone is part of the
capture source. FFmpeg scales the product footage into a 1080p frame with
English titles and captions. The four-student view crops actual recorded
conversation regions and labels each actor. It does not establish concurrency.

This is an edited workflow rehearsal, not a single uncut execution. The original
Professor A interview session is retained in the release preparation. Some
review decisions, teaching-profile approval, course provisioning and enrollment
were completed through the real APIs between takes. The footage shows the
actual resulting review state, not a claim that every preparatory click was
filmed. The release uses a preparatory import of the same PDF bytes; a repeated
import exercises the actual upload UI during recording. The source checksum
and original release preparation are recorded in the raw capture's lineage JSON.

The final replay uses a separate temporary SQLite store, seeded synthetic
sources and explicitly scripted practice opportunities. The video calls it a
separate service-event replay. Its stored outcomes are checked before editing:
one delivery for Student A1, no delivery and a pending opportunity for Student
B2 while paused, and no additional delivery after retry. These are not measured
student learning outcomes or a new qualification of the current R1 profile.

## Files and reproduction

- Raw WebM clips, snapshots and lineage: `output/playwright/recording-film/`.
- Final film, chapter MP4s, edit manifest and replay JSON:
  `reports/generated/recording-film/`.
- Four student clips: `uv run python -m scripts.record_student_clips`, after
  opening a Playwright CLI session named `recording-film` at 1600 × 900 with the
  recording workspace and published courses available.
- Editing: `uv run python -m scripts.edit_recording_film`, after all raw clips
  named in the script are present. Requires FFmpeg and the local Arial fonts.
- The shared conversation view is a video composition; no product UI or
  professor access permissions were added to implement it.

## Verification

All final-video frames decoded without FFmpeg errors. Container inspection
confirmed the exact duration, dimensions, frame rate and lack of audio. Frames
from every chapter were inspected, including all four student regions and the
replay result table. Browser snapshots confirmed real cited answers, approved
published courses and the pause operation. Capture is inherently restricted to
page content rather than the desktop. No production-facing UI was modified.
