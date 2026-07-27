# Cross-course portfolio v1

Decision date: 2026-07-27

Status: superseded partial-source inventory; retained for traceability

Superseded by:
[`cross-course-portfolio-v2.md`](cross-course-portfolio-v2.md)

This inventory was valid for the partial copy found at
`Downloads/academia_vault`, but that copy was not the canonical collection. On
2026-07-27 the source holder confirmed `Documents/academia_vault` as the exact
source. The canonical collection contains nine course folders and materially
more teaching material. Do not use v1 to author the cross-course benchmark or
make a portfolio-selection claim.

Machine-readable inventory:
[`cross_course_portfolio_v1.manifest.json`](../05_evaluation/cross_course_portfolio_v1.manifest.json)

## Historical decision

Keep all four courses in `academia_vault/semester_1`:

| Course | Role in study | Primary retrieval challenges |
| --- | --- | --- |
| IT5001 Software Fundamentals | Programming and algorithmic generalization | procedural explanations, code vocabulary, recursion/iteration distinctions |
| IT5002 Computer Systems and Applications | Primary development anchor | multi-evidence architecture questions, MIPS terminology, diagrams, caches |
| IT5004 Enterprise Systems | Narrative and requirements generalization | conceptual definitions, requirements/use-case language, long prose slides |
| IT5008 Database Design | Structured-query generalization | SQL syntax, aggregation, schema concepts, programming/database overlap |

The portfolio is intentionally heterogeneous. IT5002 remains the largest and
the pilot anchor, but every final aggregate must also report per-course results
so its 419 pages cannot hide failures on the smaller courses.

## Primary corpus

Use only the 17 PDFs directly under each course's `lecture/` directory:

| Course | Lecture PDFs | Pages | Extracted characters | Bytes |
| --- | ---: | ---: | ---: | ---: |
| IT5001 | 2 | 116 | 17,271 | 6,329,058 |
| IT5002 | 9 | 419 | 145,930 | 12,597,549 |
| IT5004 | 2 | 109 | 38,696 | 5,445,643 |
| IT5008 | 4 | 178 | 105,642 | 13,919,863 |
| **Total** | **17** | **822** | **307,539** | **38,292,113** |

Every PDF has selectable text. File hashes, sizes, page counts, and extracted
character counts are frozen in the manifest. The source PDFs remain outside
Git.

## Overlap policy

Overlap is part of the research design, but duplicate representations must not
bias ranking.

### Between courses

Bag-of-words cosine similarity over aggregated lecture and note text is low:

| Pair | Cosine similarity |
| --- | ---: |
| IT5001–IT5002 | 0.107 |
| IT5001–IT5004 | 0.066 |
| IT5001–IT5008 | 0.114 |
| IT5002–IT5004 | 0.092 |
| IT5002–IT5008 | 0.085 |
| IT5004–IT5008 | 0.132 |

This gives useful boundary cases without making the four courses near
duplicates. The strongest expected confusion is between enterprise/data
requirements and database concepts, followed by programming vocabulary shared
by IT5001 and IT5008.

### Within courses

IT5002 notes are derived from the matching lectures and have cosine similarity
of 0.538–0.721 for lectures 1–8. Indexing both would duplicate evidence and
could unfairly reward methods that retrieve repeated wording.

Therefore:

- lecture PDFs are the only primary indexed evidence;
- notes may help researchers author questions, misconceptions, and paraphrases;
- notes never count as gold evidence in portfolio v1;
- tutorials, practice, labs, midterm material, assignments, projects, and
  answer-bearing files are excluded from the index; and
- an auxiliary source may enter only through a versioned successor manifest
  with a deduplication and permission decision.

## Evaluation allocation

The approximately 100-case benchmark should not allocate questions in direct
proportion to pages. Use a stratified design:

| Slice | Target cases |
| --- | ---: |
| IT5001 answerable | 10 |
| IT5002 answerable | 25 |
| IT5004 answerable | 10 |
| IT5008 answerable | 15 |
| No-evidence | 15 |
| Cross-course confusion | 15 |
| Adversarial, permission, or integrity boundary | 10 |
| **Total** | **100** |

The 60 answerable cases cover all four courses. The 40 negative/boundary cases
test abstention, course isolation, misleading shared terminology, and prohibited
requests. At least 20 cases receive independent second review.

## Claim boundary

This inventory establishes corpus availability, permission, diversity, and
deduplication policy. It does not yet establish:

- benchmark validity;
- retrieval quality;
- provider selection;
- professor fidelity;
- student usability; or
- learning effectiveness.

Those claims require the prospective benchmark and evaluation steps in issues
#49, #50, #7, #24, and #25.
