# Repository consolidation and outstanding checks

The September 9–10 AWS pilot, application repairs, bug investigations, synthetic tests and supporting research records were consolidated through PR 220. Earlier dependent post-report changes are included. Presentation planning, diagram sources and recording/editing source files are included where suitable for the public repository.

Private lecture-derived media, unreviewed generated decks/screenshots/videos and archives, the comparison DOCX containing lecture-derived screenshots, browser captures and private outputs remain local and excluded from Git. Ignoring these files does not back them up remotely. No local source material was deleted.

## Outstanding findings

- GitHub CI run `34441369781` failed dependency audit: `httpx2==2.10.0`, advisories `CVE-2026-84379`, `CVE-2026-84380`, `CVE-2026-84382`; the audit reported fixes in 2.11.0 and 2.12.0. These are recorded tool findings, not a completed exploitability assessment or dependency repair.
- Local `npm run check` stopped at missing pre-evaluation freeze guards in `scripts/build_professor_evidence.py` and `scripts/finalize_professor_evidence.py`. No guard bypass was applied.
- PR preparation passed 116 frontend tests, frontend lint/build and 118 targeted Python/API/infrastructure tests. These do not establish full application readiness.
- The [application testing summary](application-test-summary-2026-09-10.md) retains the functional failures and blocked scenarios. The [deployment state](../reports/aws-pilot/deployed-state-2026-09-10.md) records the latest known stopped state; consolidation does not activate AWS or check-ins.

The user's latest scope is infrastructure readiness, with application walkthroughs to be performed by the user using instructions still to be supplied. The broader slide-completeness record remains a target/gap record, not evidence that those workflows are operational.
