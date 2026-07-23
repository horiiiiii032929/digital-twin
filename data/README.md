# Data

Local data folders are ignored by default because course material, transcripts,
and student interactions may be sensitive.

## Buckets

- `raw/`: original source exports
- `interim/`: cleaned or normalized intermediate files
- `processed/`: experiment-ready datasets
- `external/`: third-party public datasets or references

Commit schemas and synthetic fixtures instead of private data.

## Current local course snapshot

`raw/course_materials/it5002_full/lecture/` contains the ignored local snapshot
of all 13 official IT5002 lecture PDFs. The sanitized hashes, page counts,
extraction profile, source boundary, and permission states are committed in
[`it5002_lectures_v1.manifest.json`](../research/05_evaluation/it5002_lectures_v1.manifest.json).
Local inventory is user-authorized; tutoring, student-pilot, and external-
provider permissions remain separate approval gates.
