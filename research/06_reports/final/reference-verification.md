# Reference and software-link verification

Checked 6 September 2026. This is an editorial verification, not a new
experiment or a claim that cited software validates the project results.

## Scholarly references

- Existing author, title, venue, year and page metadata for [ALCE](https://aclanthology.org/2023.emnlp-main.398/), [pedagogical steering](https://aclanthology.org/2025.findings-acl.1348/), [ScaffoldLM](https://aclanthology.org/2026.acl-long.325/) and [the tutor-evaluation taxonomy](https://aclanthology.org/2025.naacl-long.57/) agree with the official ACL records. Their abstracts support the bounded comparisons used in the related-work section.
- [RAG](https://proceedings.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html) is now cited as the NeurIPS 2020 proceedings paper rather than only an arXiv preprint; the author list is unchanged.
- Added [Robertson and Zaragoza's BM25 reference](https://doi.org/10.1561/1500000019). The publisher reader returned HTTP 403. The [original article PDF](https://apollo.inf.upol.cz/~lastovicka/DATAB/BM25.pdf), pages 1 and 3, prints volume 3, issue 4, pages 333–389 (2009). The current Crossref response instead supplied volume 4, issues 1–2, pages 1–174. The article itself governs the citation; the conflicting registry fields were not copied.
- Qwen and Jina sources are publisher-maintained model cards, explicitly labelled as documentation rather than peer-reviewed evidence for this project's measured quality.

## Formatting and implementation attribution

Numeric citations use `natbib` with `unsrtnat`: references follow first citation,
with clickable DOI and URL fields. Acronyms are protected in BibTeX. Dynamic
software documentation is marked `n.d.` and has an explicit access date instead
of an invented publication year. Each bibliography item is actually cited;
there is no blanket `nocite` expansion.

This is a conventional numeric style supported by [natbib](https://ctan.org/pkg/natbib),
not a claim that the advisor has mandated a particular house style. Separating
software identity, versions and access information follows the specificity and
accessibility concerns in the [software citation principles](https://force11.org/post/software-citation-principles/).

The project URL was read from `git remote -v`:
[horiiiiii032929/digital-twin](https://github.com/horiiiiii032929/digital-twin).
Public accessibility was not established by the web reader. No repository was
published or changed to public, and no archive DOI or release was invented.

The software appendix uses actual dependency declarations, imports and deployment
configuration. Exact listed package versions come from `uv.lock` and
`package-lock.json` on the review date. They describe the current checkout,
not every historical experiment. Official documentation links identify API,
workflow, storage, transport, ingestion, frontend, optional retrieval, deployment,
test and build tools. The OpenAI adapter was verified to use HTTPX directly;
the report does not claim it uses the OpenAI Python SDK.

## References added for the final six-chapter revision

Checked on 6 September 2026 against primary sources:

- Horvitz, Principles of Mixed-Initiative User Interfaces, CHI 1999, pp. 159-166. [Author-hosted paper](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/11/chi99horvitz.pdf) and [Microsoft Research bibliographic listing](https://www.microsoft.com/en-us/research/articles/aaai-2020-tutorial-guidelines-for-human-ai-interaction/).
- Corbett and Anderson, Knowledge Tracing: Modeling the Acquisition of Procedural Knowledge, User Modeling and User-Adapted Interaction 4, 253-278. [Publisher metadata](https://link.springer.com/article/10.1007/BF01099821) explicitly gives the issue year as 1994; this is used despite later revision dates and some secondary indices using 1995.
- Pavlik, Cen and Koedinger, Performance Factors Analysis--A New Alternative to Knowledge Tracing, AIED 2009, pp. 531-538, IOS Press. [Author-hosted paper](https://pact.cs.cmu.edu/pubs/AIED%202009%20final%20Pavlik%20Cen%20Keodinger%20corrected.pdf) and the author's CMU publication list support the metadata.

These references explain design lineage, not empirical superiority of this
project. The BKT/PFA comparison uses local variants with forgetting/decay.
At that revision, there were 17 cited bibliography entries. The current
manuscript cites 19, including the two diagram-notation sources below.


## Diagram-notation sources — 6 September 2026

- Simon Brown, [C4 notation](https://c4model.com/diagrams/notation): responsibilities,
  explicit boundaries and labelled relationships. No publication year is inferred;
  bibliography uses n.d. with an access date.
- Object Management Group, [UML 2.5.1](https://www.omg.org/spec/UML/2.5.1), December
  2017: official normative PDF inspected for interaction, partition and state
  conventions. Activity partitions distinguish responsibility, not a different
  token flow. The project diagrams are original selective software views.
