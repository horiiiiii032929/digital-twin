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

## Review Questions

- Is this source approved for ingestion?
- Does this example contain personal information?
- Can this artifact be reproduced without private data?
- Does the tutor make course boundaries clear?
- Can the instructor audit or override the system behavior?
