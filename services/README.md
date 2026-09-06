
### Approved text and Markdown sources

The existing professor course-source PUT route also accepts `text/plain` and
`text/markdown` UTF-8 bodies. Staging uses the same recoverable ingestion queue;
PDF remains supported. Text/Markdown transcripts and forum material require the
explicit `deidentified_reviewed=true` permission/de-identification attestation
when sensitive names are detected. It is persisted with the job and source
provenance, and never substitutes for source approval or processing permission.
The UI provides this review checkbox. This does not anonymize uploaded material.
