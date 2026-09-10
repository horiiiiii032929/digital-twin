# Post-report tooling and change audit

Scope: execution boundaries and changed product behavior, not approval of the
old slide narrative or a new semantic-quality qualification.

The existing untracked presentation tools were inspected for imports, process
execution, network access, output destinations and handling of submitted
report inputs. They author local draw.io/XML, JSON, PPTX packages, renderings,
captions and script HTML. Their outputs are in presentation/generated areas;
submitted report and final manuscript paths are references, not write targets.
The HTML script blocks implement local navigation and font-size controls.
The packaging utilities rewrite ZIP members without extracting arbitrary
archive paths. They require the already-installed local artifact runtime,
draw.io and, for films, FFmpeg; these are local authoring tools, not portable
deployment commands. Their historical narrative and visual quality remain
subject to the requested slide redesign.

Static syntax checks covered 46 new Python files, 14 JavaScript modules and
four inline HTML scripts at the time of this review. All 16 existing PPTX
archives passed ZIP integrity and required-content-type presence checks.
These checks do not establish slide layout quality or regenerate old decks.
Detailed validation counts are in `/tmp/post-report-tooling-validation.json`.

Recording code uses temporary synthetic SQLite databases and explicit demo
settings. Added recording-factory verification, origin checks on the main
recorder, selectable nonoverlapping launcher ports, response-based onboarding
waits, and finally-based video closure. Tested real browser-only recording;
the first origin check failed on an unsupported URL constructor and was
corrected before the successful 1600×900 onboarding capture. The earlier
question-led helper remains legacy tooling, not the accepted final demo.

Product changes reviewed: account/course/release-scoped conversation discovery
and resumption, message association and retry state, active-goal visibility,
independent professor section loading, whitelisted observed runtime identity,
atomic worker heartbeat records and strict assessed-observation scope.
The experimental adapter is not wired into the incumbent planner. No new
generation provider, scoring threshold or selected profile was substituted.

Focused verification: 67 Python API/adapter/recording/worker/freeze tests,
80 frontend tests, frontend lint and production build. Professor activity
read failure and Retry loading were verified in the actual synthetic UI.
See `../tests/manual-post-report-continuity-2026-09-08.md` for scope and remaining
browser checks. This is the basis for refreshing the mutable correctness
inventory; frozen evaluation result records are not rewritten.
