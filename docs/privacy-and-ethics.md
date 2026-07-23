# Privacy and Ethics

This project may handle instructor materials, student questions, and learning
signals. Treat those inputs as sensitive by default.

## Defaults

- Do not commit raw course material, transcripts, student records, or private
  forum exports.
- Store local research data under `data/`, which is ignored by default.
- Keep consent records and data access notes under `research/03_data/consent/`.
- Prefer anonymized or synthetic examples in documentation and tests.
- Document source permissions before using a dataset in experiments.
- Use invited accounts only for the evaluated pilot and enforce professor,
  student, and course boundaries.
- Minimize stored student content and never place raw prompts, course documents,
  credentials, or personal identifiers in ordinary logs.
- Record the purpose, controller/processors, provider data use, processing
  location, retention, deletion, export, backup, and incident path before real
  user data enters staging or a model provider.
- Keep participation voluntary and unrelated to grades; provide a withdrawal
  and deletion path appropriate to the approved pilot protocol.

## Real-user pilot gate

The deployed application may use synthetic invited accounts before approval.
It must not use real professor, private course, or student data until #11 and #9
record:

- professor and institutional approval of the course, cohort, and provider data
  boundary;
- participant notice/consent or another documented institutional basis;
- source permissions and a retention/deletion schedule;
- authorization, log-redaction, backup/restore, and incident-response evidence;
- the support owner and pilot stop conditions; and
- whether provider prompts may be retained or used for model improvement.

If these gates are unavailable, run the usability study with synthetic accounts
and state that limitation rather than inferring permission.

## Review Questions

- Is this source approved for ingestion?
- Does this example contain personal information?
- Can this artifact be reproduced without private data?
- Does the tutor make course boundaries clear?
- Can the instructor audit or override the system behavior?
- Can a student access another student, professor, or course record?
- Does the external provider receive information not required to answer?
- Can the participant understand, withdraw, correct, or delete their data?
- Can the pilot stop and recover safely after a privacy, security, or integrity
  incident?
