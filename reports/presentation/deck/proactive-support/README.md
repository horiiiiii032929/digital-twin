# Scheduled support: slides 27–29

Current artifact: `slides-27-29-v2.pptx`.

27 shows an actual React inbox article captured through the actual FastAPI service in an isolated recording runtime. An authored IT5004 practice prompt is scheduled before a new synthetic student sends any question. This is professor-scheduled in-app delivery, not model-generated text or autonomous discovery of a learning need. No provider call or student reply occurred.

28 shows the implemented successful delivery sequence in editable draw.io. `schedule_trigger`, `process_due`, `process_trigger`, `list_inbox` and repository materialization correspond to code in `src/digital_twin/student/proactive.py`. The recording invoked `process_trigger` at controlled timestamps; `process_due` is the implemented due-list wrapper. No production timer, push subscription or external delivery is claimed. Step5 includes atomic message/citation/status persistence. Shared error branches are summarized on29.

29 gives branch-order-preserving pseudocode. Terminal status reuses prior outcome, future time waits, expiry/access/consent/snooze suppress, quiet hours defer, frequency/source checks can suppress, atomic persistence rechecks conflicts. Snooze and quiet hours have different effects. Recorded08:59not-due,09:00delivered,09:01duplicate atSingapore time. The retained profile selects professor schedules and keeps evidence-recovery detection observation-only. Broader governed-autonomy experiments are distinct and not presented as selected delivery.

## Recording provenance and reproduction

`reports/generated/proactive-support-batch/runtime.py` copies the saved IT5004 runtime to read its published lecture chunks and approved synthetic profile, then seeds a fresh local database with a new synthetic student, membership and course. The new recording release binds to the actual default local runtime component profile. Source text is unchanged; readable locator derives from the excerpt title's PDF page. Source experiment and selected profile files remain unchanged. Initial rehearsal found a release/profile mismatch; fresh release creation under the recording profile fixed the setup rather than weakening application checks. Screenshot is the delivered article only, captured from DOM, with no substituted text or mocked API.

Use `PYTHONPATH=. uv run python reports/generated/proactive-support-batch/runtime.py` for loopback API8024. The runtime deliberately resets its own `recording.sqlite3`; it does not modify the source database. UI uses isolated Vite config `apps/web/node_modules/.cache/chapter04-recording.mjs` on5194 and new synthetic student header. Run Node Vite with that config, then Playwright CLI to capture the actual Check-ins article. No external model is configured for this capture.

Delivery outcomes and exact prompt are in `delivery-evidence.json` in the build directory. This is an illustrative operating trace, not a new comparative quality evaluation or release-selection result. Data comes from `reports/generated/it5004-presentation-teaching-live-002`. No real student data.

Author `build.mjs`, diagram author `diagram.py`, editable source `reports/presentation/diagrams/chapter04/28-scheduled-outreach.drawio`. Final validation receipt `validation-v2.json`. Individual renders inspected. No PowerPoint-app verification or new demo video claimed. User review pending.
