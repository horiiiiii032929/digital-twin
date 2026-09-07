# paired-pedagogy-development-001-live-001

**Refine pending semantic and local-failure review; no candidate promotion.** All96 histories and168 turns completed, but delivered safe-graph-failure responses increased from8(v4) to29(v5). All216 provider calls completed successfully. Provider success must not be confused with successful teaching responses.

## Design and provenance

[Prospective plan](../04_experiments/2026-09-06-paired-pedagogy-runner-plan.md); [rubric](meaningful-continuation-rubric-v1.md). Development-v2 contains48 paired contexts acrossfour fictional courses and12forms. Both arms received identical explicit student inputs and approved profile/source data; actual tutor history was generated and persisted independently. Each arm completed84turns;20histories perarm restarted beforethe secondturn. Gold wasexcluded fromruntime/provider inputs. Confirmation wasnotopened.

Both arms usedLuna at3000outputtokens,reasoninglow,provider timeout30s; four independent histories maximum. Bounds800calls/USD20 were fixed beforepaid output. Actual constructed IDs matchedv4/v5. Revision `e441193c7fa1260ed327ebf43c59483f85817be8`,dirty=true; complete source/plan/rubric snapshot ZIP andpacket hash retained; endhashes unchanged. Raw output `reports/generated/paired-pedagogy-development-001-live-001`; [record](records/paired-pedagogy-development-001-live-001.json) contains exactmanifest,each history,case actionindex and ledger aggregates.

## Execution results

| Metric | v4 | v5 |
|---|---:|---:|
| Actual provider calls |108|108|
| Provider failures / unknown cost |0/0|0/0|
| Input tokens |132433|192215|
| Output tokens |25247|28677|
| Reported USD |0.056783|0.0728554|
| Answer |31|19|
| Question |28|20|
| No evidence |11|10|
| Clarify |2|2|
| Redirect graded work |4|4|
| Safe graph failure |8|29|

TotalUSD0.1296384; elapsed212.534s. Turn latency isretained percase andperarm intherecord,descriptive underfour-history scheduling ratherthan a throughput benchmark. All96 history records completed with40 actualrestarts. No budget stopped and no unknown-usage record wasconverted tofreeusage.

## Failed-case classification and decision

The8/29 safe-graph-failure actions are locally delivered graph/validation failures despite valid provider transport. They mustcount against usefulness where the rubric requires a useful response, and mustnot be omitted. Exactprovider proposals andsynthetic runtime SQLite state remainavailable for diagnosis. Free instructional question/feedback/explanation text with valid source bindings is not a semantic truth guarantee. Independent review must assess everytarget andall earlier critical boundaries,including answer leakage andfalsefeedback.

This isdevelopment evidence,not confirmation, instructorfidelity,human learning orauthenticated production deployment. There are48paired contexts,not168 independent qualitysamples. The initialfailed setupcontract001 andcorrectedcontract002 remainregistered. No default/selectedprofile changed. Further qualitygates and anysame-config authenticatedintegration remainpending.

## Subsequent semantic review

The [independent assistant review](paired-pedagogy-development-live-001-assistant-review.md) examined all168 turns and96 target responses, with root adjudication of borderline cases. Useful contexts were16/48 forv4 and30/48 forv5; primary instructional contexts were2/16 and8/16 respectively. Both usefulness gates failed; zero critical events were verified. Decision: **Refine**. This is assistant review, not instructor or human-study validation. Original execution metrics and raw outputs remain unchanged. Confirmation stays closed.

The [preserved local rendering audit](paired-pedagogy-live-001-local-rendering-audit.json) replayed all76 v5 proposals against matching source hashes and classified all29 failures:12 punctuation,3 hint mixed fields,3 ask mixed fields,10 full-answer hint guards and1 non-exact hint. This diagnosis does not revise the original scores.
