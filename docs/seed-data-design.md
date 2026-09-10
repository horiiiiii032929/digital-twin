# Synthetic pilot seed data

Status: designed and loaded into the AWS pilot on 2026-09-09. See the
[deployed demo guide](pilot-demo-accounts.md) for credentials location, verification
and limitations. The versioned manifest retains its original design-time status.
The default is a small walkthrough: two professors, three courses and six
students. All names and materials are fictional, visibly marked Demo, and use
`example.test` addresses. The existing AWS administrator is reused separately.

The versioned [manifest](../tests/fixtures/seed_data/pilot-v1/manifest.json)
contains account and membership inputs, source hashes, target course states and
nine acceptance scenarios. Its `target_release_status` is an intended outcome,
not a database field that an importer may use to bypass publication checks.

## Walkthrough

| Course | Professor | Intended state | Purpose |
| --- | --- | --- | --- |
| Demo · Data Systems | Maya Chen (Demo) | Published after gates pass | Keys, joins, worked examples and graded-work boundaries |
| Demo · Browser Security | Daniel Tan (Demo) | Published after gates pass | Sessions, cookie controls, misconception correction and course isolation |
| Demo · Release Governance | Maya Chen (Demo) | Draft, source review pending | Show incomplete onboarding and a blocked publication path |

Maya uses a short explanation, a worked example and a check question. Daniel
asks for a prediction, contrasts it with the source and checks understanding.
These are intended teaching-profile inputs, not claims that a model reliably
reproduces either style. The currently selected final R1 release profile remains
unchanged; the seed does not activate experimental components or outreach.

| Student | Membership | Walkthrough |
| --- | --- | --- |
| Alex | Data Systems | First visit, normal question, missing evidence, denied access to Browser Security |
| Bea | Data Systems | Graded lab request; receive bounded help |
| Chris | Both published courses | Switching courses preserves separate evidence and conversations |
| Dina | Browser Security | Cookie misconception and adversarial privacy request |
| Eli | Inactive Data Systems membership | Access denied despite an active account |
| Finn | Browser Security membership, revoked account | Revocation prevents access |

All students begin with no conversations, learning estimates, grades or
notifications. Create conversations through actual application flows during the
walkthrough. Do not fabricate learning progress, approvals, citation traces,
evaluation successes, consent or autonomous activity to fill dashboard panels.
A separate presentation fixture can illustrate historical states when clearly
labelled; it must not be imported as genuine activity.

## Sources and permissions

Five short Markdown files contain actual ingestible text: two sources for each
published-course candidate and one pending source for the draft. Each has a
stable ID, course binding, SHA-256 hash and synthetic provenance. The versioned
pack records permission to use this authored synthetic material; production
source review must still follow the application's workflow. The governance
source stays pending and outside student retrieval.

The small text-only baseline makes citations and isolation inspectable. Larger
random rosters, PDFs and long simulated histories add parsing and presentation
complexity without helping the first authenticated walkthrough. They can be
separate later packs. No real lecture material or learner data is needed here.

## Proposed importer contract

The importer is implemented in `scripts/seed_aws_pilot.py`; operational commands
and the limited SSM finalization step are in the deployed demo guide.
It should default to validation and a dry-run plan, with separate explicit
application of that plan. The manifest is a design schema, not an API payload.
Use an adapter into current domain services and authenticated admin/professor
workflows rather than direct inserts into SQLite tables.

1. Resolve the target environment and release profile; validate all IDs, source
   hashes and memberships. Display counts and additions before any writes.
2. Reuse the existing administrator without changing its password. Provision
   the eight demo identities through the identity service. Generate unique
   credentials privately and return them through an access-controlled local
   artifact or secret store, never source control, standard logs or the manifest.
   Do not send invitations or email as part of seeding.
3. Create courses and professor ownership, then student memberships. Seed keys
   use the `demo-pilot-v1-` namespace. Where services generate their own IDs,
   persist a private mapping from seed key to actual ID.
4. Ingest each source through the normal pipeline with its declared permission.
   Create onboarding sessions and teaching-profile drafts using course-specific
   policy inputs. Preserve the pending governance source.
5. Run real preview, approval, evaluation and publication gates for the two
   ready-course candidates. A failed gate leaves a draft and a failure record;
   never assign `evaluation_status=passed` merely because the manifest requests
   publication. Bound and separately report any provider calls and costs.
6. Validate access with the acceptance scenarios. Persist the applied seed
   version, source hashes and created-ID mapping privately for safe retries.

Repeat application must be idempotent: identical completed inputs produce no
new rows or password resets. An interrupted run resumes from verified mappings;
changed hashes or conflicting existing records stop that stage with a readable
diff. Never overwrite professor edits or student activity on a rerun. Use a new
seed version for intentional changes. Concurrent imports must be serialized.

For AWS application, take and verify a backup first and use the Singapore office
hours window, or explicitly arrange temporary access. Seeding must not change
the EventBridge schedules. A recovery operation uses the backup or scoped
service-supported deactivation of mapped demo accounts/courses; it must never
truncate the shared database or delete all records by an approximate prefix.

## Acceptance before loading AWS

Prediction: this small pack can demonstrate both professor onboarding and
student tutoring while preserving authentication, course isolation and honest
publication state. The main risks are bypassing release gates, unsafe retries,
leaking credentials and confusing simulated activity with measured outcomes.

Compare an empty disposable database plus existing admin (control) with the
same database after applying this pack (candidate). Use these hard gates:

- Eight new demo accounts, three courses and ten memberships; the original
  administrator and password are unchanged.
- Five source files match the manifest; only approved course-local sources are
  eligible for published retrieval.
- Two published releases only if their actual gates pass; the third stays draft.
- All nine manifest scenarios pass, plus draft invisibility, no cross-student
  conversation access and persistence across restart.
- Reapplying creates zero duplicates, does not reset credentials and preserves
  user edits; collision and interrupted-run recovery checks pass.
- Zero messages sent, no credentials in logs, and no changes to release selection
  or outreach configuration.

Record per-case outcomes, counts, elapsed time, provider calls/tokens/cost where
applicable, and failure classes (data, permission, ingestion, policy, publication,
authentication or operations). Register every named application acceptance run,
including failures, before deciding to keep the loaded pack. Manifest validation
alone is not evidence that importing, tutoring or publication works.

Run the read-only design validation with:

```bash
uv run python -m scripts.validate_pilot_seed
```

This checks domain compatibility, references and source hashes without touching
AWS, an application database, credentials or a model provider.
