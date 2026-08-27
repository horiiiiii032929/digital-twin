# Proactive Professor Digital Twin outreach

Date: 2026-08-27

Decision ID: `proactive-outreach-001`

Status: accepted as a core product direction; local deterministic vertical slice
implemented; external delivery, real-student use, and release selection remain
unauthorized

Implementation owner: [GitHub issue #134](https://github.com/horiiiiii032929/digital-twin/issues/134)

## Decision question

How can the Professor Digital Twin initiate a useful student interaction without
waiting for a student message, while preserving professor authority, student
control, grounding, privacy, bounded autonomy, and channel portability?

## Decision

Add an asynchronous outreach loop beside the existing student-turn graph. A
published Digital Twin may initiate a private message only after deterministic
code verifies a professor-approved trigger, explicit student channel consent,
quiet hours, frequency limits, current course membership, the current published
release, source permission, evidence lineage, and trigger freshness.

The model may propose natural-language wording. It cannot decide whether, when,
where, or to whom a message is sent. Deterministic code owns trigger eligibility,
suppression, recipient and channel binding, delivery state, retries, cancellation,
and audit.

Private in-app delivery is the core path. Channel adapters are optional:

- Discord is the first prospective external adapter because it can be integrated
  independently of the tutoring graph.
- Email, Teams, LMS, and push delivery may later implement the same contract.
- Shared destinations may carry course-wide notices only. They cannot receive an
  individual learner-state estimate, misconception, interaction history, grade,
  or student-specific practice recommendation.

## Product loops

```text
Student turn --------------------------> bounded T0/T1 response graph
                                               |
                                               v
                                    validated learner-state signal
                                               |
Professor schedule / student reminder request / course evidence recovery
                                               |
                                               v
                                      deterministic trigger
                                               |
                  +----------------------------+---------------------------+
                  | consent | quiet hours | frequency | membership | release|
                  +----------------------------+---------------------------+
                                               |
                                               v
                                  retrieve approved source evidence
                                               |
                                               v
                               bounded message composition + validation
                                               |
                                               v
                                    transactional delivery outbox
                                      |                    |
                                      v                    v
                               private in-app inbox   optional adapter
                                                          |
                                               private Discord destination
```

This is distinct from the privacy-preserving course-improvement loop. Outreach
acts for one consenting student; course improvement aggregates deidentified
signals for professor review.

## Versioned contracts

The initial implementation adds four durable contracts:

- `OutreachPreference`: per-student, per-course, per-channel opt-in, timezone,
  quiet hours, frequency ceiling, snooze state, and opaque destination reference.
- `ProactiveTrigger`: immutable recipient, course, release, source, trigger type,
  schedule, expiry, and idempotency binding.
- `ProactiveMessage`: materialized content and lifecycle state, separate from a
  student-initiated conversation turn.
- `DeliveryOutboxItem`: exclusive external-delivery record with bounded attempts
  and no embedded credential or webhook URL.

SQLite migration v10 stores these records. In-app materialization and its source
citation commit atomically. Discord materialization creates a pending outbox row;
it does not perform network delivery. Release withdrawal and replacement cancel
pending triggers and queued delivery records.

## Initial trigger policy

The first deterministic trigger vocabulary is intentionally small:

- professor-scheduled retrieval practice or spaced review;
- a follow-up explicitly requested by the student;
- a bounded misconception follow-up permitted by the published policy; and
- recovery from a previous no-evidence response after approved material changes.

The implemented vertical slice supports professor-scheduled, source-linked
practice. The other trigger types are contracts only until their event signals and
evaluation sets are frozen. No free-running model may invent a trigger.

## Consent and interruption controls

Consent is absent by default. A trigger fails closed unless the exact student,
course, and channel preference is enabled at delivery time. The student can
disable a channel, snooze it, mark a message read, or dismiss it. The initial
default is at most three messages per seven days with local quiet hours from
22:00 to 08:00.

A trigger is suppressed when consent is disabled, the student or membership is
inactive, the release changed, evidence disappeared, the trigger expired, the
student snoozed messages, or the frequency ceiling was reached. Quiet hours defer
rather than consume the trigger.

## Discord boundary

Official Discord documentation was rechecked on 2026-08-27:

- [Incoming webhooks](https://docs.discord.com/developers/platform/webhooks)
  post into a Discord channel and do not require a bot. They are suitable for
  one-way channel delivery, not automatically for private student tutoring.
- [Webhook execution](https://docs.discord.com/developers/resources/webhook)
  supports server-confirmed delivery with `wait=true`; content must suppress
  unexpected mentions with `allowed_mentions`.
- [OAuth2 and permissions](https://docs.discord.com/developers/platform/oauth2-and-permissions)
  are required for a bot or user-linked application. Bot tokens and user tokens
  are secrets and must never enter Git or ordinary logs.
- [Rate limits](https://docs.discord.com/developers/topics/rate-limits) are
  dynamic and must be read from response headers rather than hard-coded.

The repository therefore stores only an opaque `destination_ref`. The actual
webhook URL or bot token belongs in an environment-owned secret registry. The
adapter rejects non-Discord URLs, shared destinations, unexpected mentions, and
all delivery while disabled. A two-way Discord bot is a later adapter, not part
of this vertical slice.

## Evaluation plan

### Decision question

Does asynchronous outreach create relevant, grounded, non-intrusive tutoring
interactions more reliably than no outreach, without violating student control?

### Baseline and candidate

- P0 control: no proactive outreach.
- P1 baseline: deterministic rule-based trigger and deterministic/professor-
  approved wording.
- P2 candidate: the same deterministic trigger authority with bounded LLM wording.
- A learned trigger classifier may be considered only after P1 is evaluated; it
  can never override consent, course scope, release state, or suppression rules.

### Required synthetic cases

Cover eligible schedules, future and expired triggers, quiet-hour boundaries,
snooze, opt-out, inactive membership, release replacement, missing evidence,
frequency ceilings, duplicate workers, restart, delivery failure, Discord privacy,
cross-course attempts, academic-integrity prompts, and malformed provider output.

### Metrics and hard gates

- eligible-trigger precision and recall;
- inappropriate interruption rate and suppression correctness;
- message source support and citation validity;
- cross-course, unsupported, and policy-violating release count;
- duplicate delivery and idempotency failures;
- opt-out, snooze, withdrawal, and quiet-hours enforcement;
- delivery success, latency, retry count, and provider cost; and
- student usefulness/dismissal feedback only after an approved human pilot.

Before any real-student or external-channel pilot, require 100% consent,
suppression, release-withdrawal, citation-lineage, cross-course, privacy, and
duplicate-prevention gates on the frozen synthetic set. Trigger usefulness and
interruption cost remain `Go Deeper` until representative evidence exists.

## Current implementation boundary

Implemented now:

- versioned contracts and SQLite migration;
- opt-in private in-app preferences and inbox API;
- professor-scheduled, source-linked deterministic triggers;
- due-time, expiry, membership, release, evidence, quiet-hour, snooze, and
  frequency validation;
- atomic idempotent materialization and source citations;
- read/dismiss controls and release-withdrawal cancellation;
- disabled Discord request adapter and private-destination outbox; and
- network-free unit, repository, API, and frontend-client checks.

Not yet implemented or authorized:

- a production scheduler/worker;
- LLM-composed proactive wording;
- inferred misconception triggers;
- a real Discord bot/webhook secret registry or network call;
- professor/student configuration screens beyond the in-app opt-in panel;
- real-student, interruption-cost, or learning-outcome claims; and
- release-profile selection.
