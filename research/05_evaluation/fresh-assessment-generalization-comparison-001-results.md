# Fresh fixed-candidate comparison

**Refine; V16 is not integrated.** BothV14-medium andV16 score103/112,
with56/56 adequate responses preserved and47/56 defective responses corrected.
Both have one critical unsupported guarantee. V14 has one uncertain scale claim;
V16 has that claim plus an uncertain role-exclusion phrase. Uncertainty is unqualified.
V16 improves two initial cues but regresses one requested numerical completion and
one role-association statement. It does not demonstrate superiority.

The paired useful difference is0.00percentage points. A family-stratified bootstrap
of56scenario pairs gives exploratory95% percentile interval[-3.57,3.57]points
(seed8801;10000 draws). This is conditional on assistant-authored scenarios and one
provider draw perarm, not an estimate of realstudent learning or a population accuracy
guarantee. All112inputs were newly authored and cross-reviewed before outputs;
these are exposeddevelopment controls, not the unopened sealed confirmation.

| V16 prospective gate | Outcome |
|---|---|
| Adequate at least54/56 | Pass56/56 |
| Flawed at least54/56 | Fail47/56 |
| Each family at least26/28 | Fail evidence25/28 andinitial23/28 |
| Zero criticals | Fail1 |
| Complete known unchanged runs | Pass224calls |
| Useful total not below V14 | Tie103/112; no superiority |

Actual224Sol-medium calls costUSD2.566300;0providerfailures or unknownusage,
unchanged source/input snapshots. Individual walls514.902/541.323s overlap and
are not controlled latency comparisons. Codee441193 dirtyTrue is archived exactly
in each source-snapshot.zip. No Luna draftgeneration occurred.

The outcome-informed progression amendment was stated before these outputs and
fails its own new gates. The previous V16Dahlia16/16subgroup failure remains failed.
No integration, sealed confirmation or later qualitysuite is authorized by this
result. A separate final-output verification study addresses unchecked repair prose;
it must demonstrate preservation as well as risk detection.

[Machine record](records/fresh-assessment-generalization-comparison-001.json) includes
all per-case paired changes, source/input/model hashes, slices and operational data.
Individual reviews preserve all112outputs each. Reproduction:

```sh
.venv/bin/python -m scripts.analyze_fresh_assessment_comparison --packet research/05_evaluation/datasets/fresh-assessment-generalization-development-v1.json --baseline-dir reports/generated/independent-factual-revision-controls-001-fresh-v14-medium-live-001 --candidate-dir reports/generated/independent-factual-revision-controls-001-fresh-v16-live-001 --baseline-review research/05_evaluation/independent-factual-revision-controls-001-fresh-v14-medium-live-001-assistant-review.json --candidate-review research/05_evaluation/independent-factual-revision-controls-001-fresh-v16-live-001-assistant-review.json --output /tmp/fresh-assessment-analysis-reproduction.json
```

Limits: assistantreview, syntheticbalancedactiontraffic, authoredresponses,
strictcase-specificcuecoverage, no humanvalidation. Wey missing-state notices count
as clarification bymeaning; a literalquestion requirement would reduce both totals
bytwo without changing any decision. Supportscale and exclusion ambiguities are
retained, not silently scored as successes.
