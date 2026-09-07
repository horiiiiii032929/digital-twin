# Provider usage integrity repair

Decision: **Keep fail-closed parsing of missing usage**. No selected model change.

The [prospective plan](../04_experiments/2026-09-06-provider-usage-integrity-plan.md)
tested a concrete parser defect: missing usage became zero, and a missing input
or output count produced a partial apparently known cost. The baseline's three
missing-field examples reproduced this behavior before modification. Explicit
zero remained a separate valid control.

The repaired transport requires a usage object and both nonnegative integer
token counts. Missing or malformed usage raises a usage-validation failure with
unknown cost. Tests through the actual response parser and both serial/concurrent
budget wrappers verify that subsequent calls stop; the concurrent reservation
remains retained. Explicit zero and normal counts still pass.

Eleven new partition tests and58 focused provider/budget/semantic-review tests
passed; Ruff passed. These are deterministic contract checks, not58 independent
provider trials. External calls and cost were zero. Before/after source copies,
baseline observations and test output are retained at
`reports/generated/provider-usage-integrity-development-001/`.

The inspected recent operating/cap/contract ledgers contain954 completed/failed
outcome rows with positive input and output counts; admission rows were excluded.
Those positive values cannot originate from the defective missing-to-zero rule.
Thus this discovery does not justify retroactively changing those run costs.
It is not an invoice audit or a recertification of every historical run.

The [record](records/provider-usage-integrity-development-001.json) retains exact
source hashes, revision/dirty state, before observations, scope and reproduction.
