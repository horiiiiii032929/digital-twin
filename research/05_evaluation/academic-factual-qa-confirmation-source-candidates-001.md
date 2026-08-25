# Academic factual-QA confirmation source candidates 001

Verified: 2026-08-25

Status: metadata-only shortlist; no content downloaded, ingested, hashed, or
bound to the confirmation instrument

## Purpose

This shortlist makes the public-source decision concrete while preserving the
build-only boundary of `academic-factual-qa-confirmation-001`. The four
collections cover distinct computing-course strata and expose text, code,
tables, diagrams, and equations. A later source-manifest checkpoint must choose
exact sections, resolve versions and licenses, hash every artifact, and verify
that no source family overlaps development data.

| Course stratum | Candidate collection | Primary license evidence | Current assessment |
| --- | --- | --- | --- |
| Operating systems | [Open Education Hub Operating Systems](https://open-education-hub.github.io/operating-systems/) | The official course page states CC BY-SA 4.0 for content and BSD 3-Clause for code | Eligible candidate; exact repository revision and 25 non-overlapping section artifacts still required |
| Computer networking | [Computer Networking: Principles, Protocols and Practice](https://www.computer-networking.info/) | Official site identifies the open-source undergraduate ebook; [Open Textbook Library record](https://open.umn.edu/opentextbooks/textbooks/computer-networking-principles-protocols-and-practice) records CC BY | Candidate pending exact-edition license confirmation from the selected artifact itself |
| Data structures | [Open Data Structures](https://opendatastructures.org/) | Official site states the book and source are under a Creative Commons Attribution license | Eligible candidate; choose one edition/language and bind section-level versions |
| Programming | [Think Python, third edition](https://allendowney.github.io/ThinkPython/chap00.html) | Official preface states CC BY-NC-SA 4.0 for text and MIT for code | Eligible non-commercial research candidate; separate text/code license fields are required |

## Required source-manifest checks

- exactly four course strata and 25 source-family clusters per stratum;
- one immutable URL/repository revision, retrieval date, SHA-256, license URL,
  attribution string, modality inventory, and allowed-use decision per artifact;
- no exercises with answer keys or other assessed-work material used as ordinary
  answerable facts;
- no learner submissions, comments, analytics, account data, or third-party
  embedded material whose license is unresolved;
- each selected section belongs to one cluster only, including multi-source
  cases; and
- raw downloaded content remains under ignored data storage and never enters
  GitHub.

## Open items before binding

1. Confirm an exact edition or commit for each collection.
2. Resolve the networking artifact's license from the selected edition itself,
   rather than relying only on the catalog record.
3. Verify that at least 25 independently usable section artifacts exist in each
   stratum without splitting one fact into artificial replicas.
4. Approve the independent reviewer arrangement. Metadata eligibility alone
   cannot make the cases reference quality.
