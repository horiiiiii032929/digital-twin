# Thirty-day demo storyboard

Status: proposed storyboard after inspection of historical logs; no new recording or evaluation run.

## Purpose

Opening question: **What does the tutor do over 30 days without a new student question?**

Show actual scheduled actions, student responses, governance and operating continuity, then expose the limits of the delivered support. Fast-forward elapsed time; hold readable evidence at events. Target approximately 3 minutes 30 seconds. Do not accelerate chat text continuously.

## Evidence and cast

Historical run: [full operational dialogue development](../../../research/05_evaluation/final-profile-operational-dialogue-development-001-full-live-001-results.md).

Raw source: `reports/generated/final-profile-operational-dialogue-development-001-full-live-001/`.

Use four diagnostic histories, selected to show reply and nonreply under both profiles. Selection is illustrative, not representative sampling or a profile-effect comparison.

| Display label | Exact history directory | Delivered follow-ups | Synthetic replies |
| --- | --- | --- | --- |
| A1 / Socratic | answer-seeking-socratic-t1-v2-autonomous-6209 | Days 5, 6 | Days 5, 6 |
| A2 / Socratic | low-receptivity-socratic-t1-v2-autonomous-6209 | Days 2, 3, 3 | None |
| B1 / Explanatory | answer-seeking-explanatory-t1-v2-autonomous-6209 | Days 5, 6, 7 | Days 5, 6, 7 |
| B2 / Explanatory | low-receptivity-explanatory-t1-v2-autonomous-6209 | Days 2, 3, 4 | None |

These were isolated histories with reused synthetic account identifiers. A/B and A1–B2 are presentation aliases for two profile groups and four histories, not evidence of four concurrent accounts or two separate professors operating together. Scope every event by history ID as well as event ID.

## Screen arrangement

Persistent top bar: `30 virtual days · Recorded simulation replay`, current day and progress to Day 30. Two profile columns with two student cards each. Cards show only observable events: last interaction, delivered follow-up count, reply count, outreach preference. Never label inferred mastery or motivation as measured state.

At a focus event, enlarge one conversation and show a compact adjacent evidence panel: recorded decision reason, permission checks, delivery, linked response. Other students remain as small cards. Highlight one event at a time. This is an editorial replay view, not a professor dashboard or a new product feature.

## Timed sequence

| Video time | Virtual time | Visual and narrative | Evidence |
| --- | --- | --- | --- |
| 0:00–0:10 | Preview | Show a follow-up arriving before a new question. Ask the opening question, then visibly rewind to setup. | Selected proactive message timestamp and runner ordering |
| 0:10–0:30 | Setup | Fast-forward existing onboarding footage; hold approved materials, teaching style and permission. Then explicit transition: `Historical 30-day simulation · Separate recorded run`. | Existing recording; historical configuration is a separate provenance |
| 0:30–0:50 | Days 1–4 | Introduce four history cards; show one short exchange. Day counter advances. B2 receives follow-ups on Days 2–4 without replying to those messages. | B2 turns and proactive ledgers |
| 0:50–1:25 | Day 5 | Focus A1: previous Day 4 parcel-window attempt; scheduler runs before today's student question; action checks pass; check-in arrives; student replies; tutor returns its recorded safe failure. Hold this result rather than conceal it. | A1 Day 4/5 turns; proactive message; autonomous action linked by trigger ID |
| 1:25–1:55 | Days 6–7 | A1 receives repeated support on Day 6 and replies correctly; compare B2's three deliveries without proactive replies. B1's counter advances through Day 7. Show `Delivery does not guarantee engagement`. | Four selected ledgers; reply links |
| 1:55–2:20 | Days 10–19 | Mark outreach preference disabled on Day 10. Show Day 15 service restart and continuing history. Fast-forward routine questions through Day 19. | Consent ledgers; daily restart counter; later turns |
| 2:20–2:40 | Days 20–30 | Preference restored on Day 20; continue to Day 30. Explicitly show no new proactive deliveries in this interval, while ordinary tutoring continues. | Consent, proactive and turn ledgers |
| 2:40–3:10 | Review | Four selected histories: 11 proactive deliveries, 5 synthetic proactive replies. Highlight one repeated message and prior correct attempt. Explain that operational autonomy worked but personalization remained weak. | Selected-history counts and exact content; published qualitative review |
| 3:10–3:30 | End | Hold three conclusions: `Scheduled support executed`; `Preferences and restart were exercised`; `Intervention quality still needs improvement`. | Historical result scope |

## Exact focus evidence

A1 Day 4: the student gave a correct parcel-window attempt before the next day's follow-up. Do not describe the Day 5 check-in as proof that the system detected a genuine knowledge gap.

A1 Day 5 action: `send-in-app-check-in`; structured reason `architecture-selected:incomplete_objective_with_sufficient_uncertainty_and_attempts_remaining`. Show an accessible paraphrase labelled “Recorded decision reason”, retaining the exact value in replay metadata. It is a recorded architecture reason, not a model chain of thought.

A1 Day 5 message begins “Pause and connect the next step to this approved course evidence” and quotes the parcel-window source. The synthetic student responds with the incorrect “skips every check” attempt. The tutor's actual response is: “I could not validate that tutoring response. Please restate the step you are working on or ask the instructor.”

A1 Day 6 repeats the same check-in text; the student gives a correct synthetic attempt and the tutor returns the parcel-window facts. This is evidence of a response path, not demonstrated learning or successful adaptation.

## Claims to avoid

- All 16 proactive deliveries in the full 24-history run occurred before Day 10. Absence during disabled days alone does not establish a counterfactual blocked delivery. Do not animate a rejected message unless its rejection is directly evidenced.
- Restoring consent did not produce a new proactive delivery. Do not invent a resumption event.
- The run records an actual restart and conversation continuity. It did not populate the optional before/after restart snapshot checks; do not claim an exhaustive equality check.
- Virtual days and synthetic student behavior are simulation inputs. Actual service/model outputs are recorded results. Playback does not call a provider or rerun decisions.
- A1's safe failure and repetitive support remain visible. The four histories are a diagnostic selection, not an intervention-quality score.
- Onboarding footage uses different materials/runtime from these historical histories. Keep the visible chapter boundary; never splice them as one end-to-end execution.

## Next production step

Build a read-only, history-scoped replay dataset from these ledgers with source file hashes, day/event ordering, action-to-message trigger links, and reply-to-message links. Then render a short Day 4–6 preview for review before producing the complete recording. No new model calls or changes to product behavior are needed for replay.

## Day 4–6 preview produced

Command: `uv run python -m scripts.build_thirty_day_preview`.
Output: `reports/generated/thirty-day-preview/day-4-to-6-preview.mp4` (63 seconds,
1920 × 1080, silent English captions). This is a first editorial layout and pacing
preview, not product screen footage. Four cards retain fixed positions; counters
explicitly refer to the displayed end-of-day cutoff, while the focus panel advances.

Inspection correction: historical turn ledgers do not contain the newer explicit
`responding_to_delivered_message_id` field. The preview associates the selected
reply using its `proactive-reply` reason and matching day/timestamp; it does not
claim a directly retained message-ID link. Action-to-message linkage is explicit
through `proactive_trigger_id` / `trigger_id`. Source file hashes and the selected
action are retained in the generated manifest. Before full replay, use the same
historical distinction rather than assuming today's runner schema was recorded.
