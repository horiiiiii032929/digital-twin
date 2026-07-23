# Privacy and Ethics

This project may handle instructor materials and synthetic student-role
questions. Treat private course inputs as sensitive by default. Real student
data and human-participant recruitment are out of scope for the final
evaluation.

## Defaults

- Do not commit raw course material, transcripts, student records, or private
  forum exports.
- Store local research data under `data/`, which is ignored by default.
- Keep data access and permission notes under `research/03_data/consent/`.
- Prefer anonymized or synthetic examples in documentation and tests.
- Document source permissions before using a dataset in experiments.
- Use synthetic invited accounts only for the evaluated deployment and enforce
  professor, student-role, and course boundaries.
- Minimize stored student content and never place raw prompts, course documents,
  credentials, or personal identifiers in ordinary logs.
- Record the purpose, controller/processors, provider data use, processing
  location, retention, deletion, export, backup, and incident path before real
  user data enters staging or a model provider.
- Do not collect participant, grade, or real student interaction data.

## Human-use exclusion and future gate

The evaluated deployment uses synthetic invited accounts. It may use approved
professor and private course material locally, but it must not use real student
or participant data. Any later human deployment is future work and requires a
new protocol plus explicit records for:

- professor and institutional approval of the course, cohort, and provider data
  boundary;
- participant notice/consent or another documented institutional basis;
- source permissions and a retention/deletion schedule;
- authorization, log-redaction, backup/restore, and incident-response evidence;
- the support owner and pilot stop conditions; and
- whether provider prompts may be retained or used for model improvement.

These records are not needed for the current no-participant evaluation because
real users are excluded. Synthetic-account completion is an operational
acceptance result and must not be called human usability.

The current data classes, evaluator roles, trust boundaries, threats, and stop
conditions are defined in the
[evaluation data-flow and threat model](evaluation-data-flow-and-threat-model.md).

## Review Questions

- Is this source approved for ingestion?
- Does this example contain personal information?
- Can this artifact be reproduced without private data?
- Does the tutor make course boundaries clear?
- Can the instructor audit or override the system behavior?
- Can a student access another student, professor, or course record?
- Does the external provider receive information not required to answer?
- Does any artifact accidentally contain real participant or student data?
- Can the pilot stop and recover safely after a privacy, security, or integrity
  incident?
