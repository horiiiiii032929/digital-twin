# Full provider-backed operational dialogue development 001

## Decision

The declared operating run completed: 24 histories across 30 virtual days,
with actual Luna calls, persistence, scheduled outreach and restart. Keep this
as operational development evidence; pedagogical quality remains **Refine**.
It is not release qualification, professor fidelity or a learning study.

## Results

- 654 external calls: 643 completed and 11 incomplete at the configured 500-output-token limit.
- 484 tutor turns: 272 answers (56.20%), 183 questions (37.81%), 16 no-evidence responses (3.31%), and 13 safe graph failures (2.69%). These action fractions are not accuracy scores.
- 16 proactive messages and 10 synthetic replies; no unassignable proactive concept was silently assigned.
- 24 actual service restarts, 48 consent changes, and zero deliveries during the scripted disabled interval.
- All 24 observed budget-wrapper chains retained `cost_reporting_failed=false`; every history retained external model traces in both early and late periods, with last traces on day 28 or 30.
- Reported cost $0.331709; 813,835 input and 140,785 output tokens; approximately 350 seconds wall time and 4,492.99 ms provider p95 latency under six isolated concurrent histories.
- All captured source hashes remained unchanged. The 5,000-call/$50 reservation limits were not exhausted.

The model task counts were 484 question-specific generation, 128 reactive intent,
26 hierarchical autonomy planning and 16 bounded wording calls. Completed
histories did not hide an early silent provider shutoff. Nevertheless, two
additional graph failures were invalid question-focus selections, and valid
answers/questions still need content review.
The earlier v2 and Terra progression findings remain unfavorable where noted.

## Design and provenance

The [prospective plan](../04_experiments/2026-09-06-operational-dialogue-development-plan.md)
uses six seeded attendance/receptivity/misconception probability configurations,
two approved synthetic profiles and paired reactive/autonomous conditions.
Consent is disabled on day 10, restored on day 20, and persisted across restart
on day 15. Actual delivery timestamps are checked against that interval.
Student text and elapsed time are synthetic; no mastery delta is scored.
A daily scheduler tick over virtual days does not demonstrate 30 days of uptime.

The [strict machine record](records/final-profile-operational-dialogue-development-001-full-live-001.json)
retains the dirty code revision, exact candidate/profile/source hashes, per-case
fractions, early/late trace coverage, observed budget-wrapper states, costs and
artifact hashes. Raw ledgers and SQLite fixtures remain under
`reports/generated/final-profile-operational-dialogue-development-001-full-live-001`.
These sources are synthetic and contain no private instructor/student data.
The full grid is a finite operating coverage design; no statistical inference
to a student population or causal benefit is justified.

## Per-history delivered actions

Fractions below are of delivered tutor turns. `F` is safe graph failure;
`NE` is no-evidence. No history had a clarification action. The final column
shows first/last virtual days retaining an external-provider trace, not an
accuracy or learning score.

| History | Turns | Answer % | Question % | NE % | F % | Trace days |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| fast-learner-socratic-t1-v2-reactive-6209 | 27 | 48.1 | 48.1 | 3.7 | 0.0 | 1–30 |
| fast-learner-socratic-t1-v2-autonomous-6209 | 28 | 50.0 | 42.9 | 3.6 | 3.6 | 1–30 |
| fast-learner-explanatory-t1-v2-reactive-6209 | 18 | 83.3 | 16.7 | 0.0 | 0.0 | 1–30 |
| fast-learner-explanatory-t1-v2-autonomous-6209 | 16 | 100.0 | 0.0 | 0.0 | 0.0 | 1–30 |
| slow-learner-socratic-t1-v2-reactive-6209 | 18 | 33.3 | 55.6 | 5.6 | 5.6 | 1–28 |
| slow-learner-socratic-t1-v2-autonomous-6209 | 18 | 27.8 | 55.6 | 5.6 | 11.1 | 1–28 |
| slow-learner-explanatory-t1-v2-reactive-6209 | 13 | 69.2 | 23.1 | 0.0 | 7.7 | 1–28 |
| slow-learner-explanatory-t1-v2-autonomous-6209 | 13 | 76.9 | 15.4 | 0.0 | 7.7 | 1–28 |
| high-forgetting-socratic-t1-v2-reactive-6209 | 28 | 42.9 | 46.4 | 7.1 | 3.6 | 1–30 |
| high-forgetting-socratic-t1-v2-autonomous-6209 | 29 | 48.3 | 44.8 | 3.4 | 3.4 | 1–30 |
| high-forgetting-explanatory-t1-v2-reactive-6209 | 22 | 77.3 | 22.7 | 0.0 | 0.0 | 1–30 |
| high-forgetting-explanatory-t1-v2-autonomous-6209 | 18 | 83.3 | 11.1 | 5.6 | 0.0 | 1–30 |
| misconception-prone-socratic-t1-v2-reactive-6209 | 18 | 27.8 | 61.1 | 5.6 | 5.6 | 1–30 |
| misconception-prone-socratic-t1-v2-autonomous-6209 | 20 | 20.0 | 65.0 | 15.0 | 0.0 | 1–30 |
| misconception-prone-explanatory-t1-v2-reactive-6209 | 13 | 100.0 | 0.0 | 0.0 | 0.0 | 1–30 |
| misconception-prone-explanatory-t1-v2-autonomous-6209 | 14 | 92.9 | 7.1 | 0.0 | 0.0 | 1–30 |
| answer-seeking-socratic-t1-v2-reactive-6209 | 31 | 32.3 | 61.3 | 6.5 | 0.0 | 1–30 |
| answer-seeking-socratic-t1-v2-autonomous-6209 | 35 | 34.3 | 57.1 | 2.9 | 5.7 | 1–30 |
| answer-seeking-explanatory-t1-v2-reactive-6209 | 22 | 81.8 | 18.2 | 0.0 | 0.0 | 1–30 |
| answer-seeking-explanatory-t1-v2-autonomous-6209 | 24 | 83.3 | 8.3 | 4.2 | 4.2 | 1–30 |
| low-receptivity-socratic-t1-v2-reactive-6209 | 16 | 25.0 | 68.8 | 0.0 | 6.2 | 1–28 |
| low-receptivity-socratic-t1-v2-autonomous-6209 | 17 | 35.3 | 64.7 | 0.0 | 0.0 | 1–28 |
| low-receptivity-explanatory-t1-v2-reactive-6209 | 13 | 76.9 | 23.1 | 0.0 | 0.0 | 1–28 |
| low-receptivity-explanatory-t1-v2-autonomous-6209 | 13 | 84.6 | 15.4 | 0.0 | 0.0 | 1–28 |

## Reproduction and limits

With the authorized provider credential privately loaded and a fresh directory:

```bash
uv run python -m scripts.run_operational_dialogue_development --full-live --output-dir reports/generated/operating-24x30-fresh
```

Keep the exact unpromoted Luna/v2 configuration. The runner does not qualify
browser authentication, document ingestion, multi-host scaling, real student
learning, or the value of proactive interventions. A larger quantity of
synthetic interactions does not resolve the known pedagogical limitations.

## Bounded qualitative review

The [independent assistant review](dialogue-full-live-001-assistant-review.md)
and [77 selected-case findings](dialogue-full-live-001-assistant-findings.json)
inspect all13 failure turns, all16 proactive messages and selected first/last
nonfailure turns. Eleven failures were the output cap; two selected a focus
absent from the current question. All proactive messages quoted an entire
synthetic card with a generic wrapper;14 had a correct earlier-day attempt on
the same concept. This does not establish mastery, but it limits evidence of
personalized intervention value. Three of12 explanatory first turns asked a
generic question. Selection was post-run diagnostic, so no semantic pass rate
is inferred. Quality remains Refine.

An ignored `source-snapshot.zip` in the run directory preserves every exact
manifest-hashed source/profile file for this dirty source state. Its hash is
recorded; it excludes credentials and runtime data.
