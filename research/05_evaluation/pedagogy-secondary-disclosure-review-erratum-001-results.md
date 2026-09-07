# Secondary-concept disclosure: adverse review correction

Run ID: `pedagogy-secondary-disclosure-review-erratum-001`. **Refine.** This read-only reanalysis corrects two missed assistant-review violations using the existing rule that an attempt on one concept does not authorize the complete solution of a new concept. It changes no original output, rubric, source, model or frozen gate. Original reviews remain intact as historical records; subsequent claims should use these corrected interpretations.

| Source run and arm | Affected target | Original → corrected useful | Original → corrected critical |
| --- | --- | --- | --- |
| V5 main candidate | Kestrel repeated stuck, stage3 | 30→29 /48 | 0→1 |
| V6 main control | Kestrel repeated stuck, stage3 | 15→15 /48 | 0→1 |

Both responses supply the full recovery rule—restore the last committed stamp and recheck held items—after a question and attempt only about relay forwarding. The information is source-supported but premature for the distinct recovery concept under the actual Socratic profile. The V5 target had previously been called useful because it also correctly applied6≠7. That classification missed the critical secondary disclosure. The V6 control target was already inadequate for the requested application, so its useful count does not change. V6 candidate43/48,13/16 and zero verified critical events remain unchanged; its separate boundary failure remains.

The [machine record](records/pedagogy-secondary-disclosure-review-erratum-001.json) records exact synthetic excerpts, raw hashes, original-review hashes, code/dirty provenance, inspected-turn count and corrected paired aggregates. All Socratic ANSWER turns in the two prior runs were screened for secondary-concept vocabulary; both matches were manually checked against current/prior messages, source rules and profile. Earlier full-turn reviews remain the basis for other dimensions; this is a targeted adverse correction, not a newly independent complete relabel. Root assistant confirmed the same interpretation on a newly observed V7-control Willow disclosure and adjudicated these prior cases consistently.

This evaluation used zero new provider calls and costUSD0. No confidence interval is meaningful for the two purposively investigated reviewer errors. Neither an assistant author nor an assistant reviewer is a human evaluator. The correction shows why structural citation checks and a first assistant reading cannot establish reliable teaching-quality qualification. Confirmation remains unopened, and neither the previously failed V5 nor the boundary-failing V6 is promoted.
