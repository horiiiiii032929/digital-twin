# Source ingestion and dashboard completion plan

Decision question: can the existing approved PDF ingestion and source-level
cohort review workflow handle UTF-8 text/Markdown teaching material and let a
professor record an improvement decision through the product UI?

Baseline: PDF-only uploads; existing local text/Markdown parser; source-labelled
privacy-suppressed aggregates and review API without a review UI. Candidate:
reuse the exact parser, job leasing, approval/provenance, release preflight and
withdrawal paths for .txt/.md, and expose existing review decisions in the UI.
No new ranking, concept inference, automated anonymization or model is selected.

Prediction: all three formats retain stable checksum/version/source locators;
invalid UTF-8/empty/control-character inputs fail before storage; cross-course
access stays denied; withdrawn releases stop student use. Source summaries show
an explicit 30-day reporting window. No percentage is shown without a defensible
eligible learner denominator. This change reports source-level signals only.

Evaluation fixtures: fresh synthetic UTF-8 lecture text and anonymized forum-style
Markdown containing no real personal data, existing synthetic PDF control,
invalid UTF-8, empty text, idempotency MIME conflict, and five-student cohort
signals. Hard gates: all permission/provenance/withdrawal/privacy assertions pass;
zero provider calls. API journey tests and frontend API/render tests cover the
new paths. Local test duration is operational verification, not production
latency. Parent registers any named evaluation evidence separately.

Failure classification: encoding/parsing, source metadata/permissions, queue
integration, release authority, aggregation window, API/UI state. Keep only if
regressions pass; otherwise refine. Approval remains explicit professor upload;
real transcripts/forum content must already be approved and de-identified.

## Cross-component contract extension

Before the new integration test, predict that text bytes uploaded through the
product API can be published with an API-approved teaching profile, receive
explicit professor approval of its release-bound concept model, and reach
the opt-in question-specific generator with the exact release-bound profile
and source text. Its cited answer must retain the upload checksum; withdrawal
must deny a subsequent message before another provider call. Use a deterministic
structured-proposal client, existing selected retrieval and the real candidate
admission gate (no AnyHit replacement). This tests component composition,
not model quality, real instructor material or external-provider performance.

## Implementation findings and decision

The new integration journey found that text chunks had the source checksum only
in metadata, so queued ingestion and publication rejected them. The product
boundary now copies the verified source checksum into the same typed field used
by PDF. The existing parser and citation locator format remain unchanged.

Sensitive-name sources remain blocked unless the professor explicitly attests
permission and de-identification for text/Markdown. Migration 18 persists this
boolean, default false for old jobs; the exact reviewer/version/checksum remain
bound to the approval and chunk provenance. This is an attestation, not automatic
anonymization or a privacy classifier. Unapproved sources and missing processing
permission remain blocked. PDF sensitivity behavior is retained.

The repository can identify distinct learners with committed student messages in
an exact release and 30-day window, including learners without gap signals. The
API exposes this active-learner count only at five or more; the UI defines it as
participation, not enrollment, current consent, or mastery. No percentages are
shown. Numerator signals use the same inclusive reporting window; source grouping
is unchanged. The implementation uses existing repository reads and is not a
large-cohort performance claim.

Proposal review now appears in the UI and is read back from audit events. No
material/policy change is executed. A repeated API review previously collided
with its deterministic audit ID; unique audit event IDs preserve repeated
requests without a server error. The UI displays the recorded outcome.

Focused verification: synthetic txt/Markdown API ingestion→preflight→publication
→cited dialogue→withdrawal; queue/MIME idempotency; invalid encoding; permission
attestation negatives; migration default; six actual students (five gap signals
plus one without) → source aggregate and distinct active count; small-cell and
31-day suppression; repeat review; frontend request and rendered-state tests.
Parent records final combined counts and release qualification separately.

Decision: Keep for development integration; full staged/browser and scale
qualification still belongs to the shared completion gates. Audio transcription,
Canvas export connectors, automatic anonymization and concept diagnosis are not
implemented by this change.

Cross-component contract result: the real opt-in factory passed the upload,
profile approval, concept-model approval, cited response and withdrawal journey
in `tests/api/test_candidate_ingestion_composition.py`. The injected structured
client is deterministic; this adds no external-model quality evidence.
