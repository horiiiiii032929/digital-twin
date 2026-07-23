# Claim-to-evidence matrix

Status: living index; no claim is accepted until its named evidence exists and
passes the frozen gates.

| Report claim | Primary dataset or evidence | Primary outcome | Required diagnostics and gates | Planned figure or table | Current status |
| --- | --- | --- | --- | --- | --- |
| The system retrieves complete approved evidence for course questions | `course-tutor-v1` sealed test | Complete-evidence success@3/5 | Recall, precision, graded nDCG, MRR, permission/version violations, scenario slices | Retrieval comparison with 95% intervals | Pending dataset |
| The generated tutor is grounded and abstains safely | `course-tutor-v1` C1-C3 outputs | Unconditional safe grounded task success | Atomic claim support, contradiction, citation correctness/completeness, false answer/abstention, hard gates | Paired condition comparison and failure flow | Pending protocol freeze |
| Professor policy changes tutoring behavior | Blinded C1 versus C2 outputs | Professor-policy pedagogical success and win/tie/loss | Per-dimension rubric, assessed-work gate, reviewer agreement | Policy-effect forest or dot plot | Pending anchor review |
| Retrieval is justified relative to simpler context controls | C2-C4 paired comparison | Safe grounded success difference | Retrieval loss, latency, tokens, cost, complexity, rollback | Quality-latency-cost trade-off plot | Pending candidate freeze |
| Invited professors and students can use the deployed pilot | Supervised task records | Role-specific task completion | Time, errors, intervention, failed turns, citation comprehension, privacy incidents | Task completion and failed-turn plot | Pending deployment |
| The deployed pilot is operationally controlled | Staging and pilot operational records | Reliable turn completion | p50/p95 latency, timeout/error rate, recovery, backup/restore, rollback, cost, authorization and deletion gates | Reliability and recovery table | Pending deployment |

## Use rules

- Link each accepted row to a stable result ID and registry entry.
- Generate every numeric figure from machine-readable per-case records with a
  committed script.
- Preserve rejected, narrowed, inconclusive, failed, and invalid claims.
- State the dataset, profile, model, prompt, revision, sample size, uncertainty,
  limitations, and participant boundary beside every result used in the report
  or slides.
- Do not convert a benchmark-specific or synthetic result into a universal SOTA,
  production-readiness, or learning-improvement claim.
