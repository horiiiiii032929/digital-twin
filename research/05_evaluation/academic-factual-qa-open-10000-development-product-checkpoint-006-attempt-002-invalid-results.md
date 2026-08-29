# Product checkpoint 006 — attempt 002

Result ID: `academic-factual-qa-open-10000-development-product-checkpoint-006-attempt-002-invalid`

Decision: **Invalid execution / stop checkpoint 006**

The sole harness-corrective execution started from clean revision `6ba1a2d`.
It loaded the exact four AFQC-068 immutable retrieval indexes, then durably
completed all 500 candidate and 100 fixed-control responses before hidden gold
opened.

Operational accounting is complete:

- candidate: 500 responses, 445/445 successful provider calls, 847,250 input
  tokens, 36,635 output tokens, 625.022 seconds aggregate provider latency, and
  USD 0.800295;
- control: 100 responses, 95/95 successful provider calls, 325,869 input
  tokens, 8,068 output tokens, 136.320 seconds aggregate provider latency, and
  USD 0.28070775;
- total: 600 responses, 540/540 successful provider calls, zero failed calls,
  1,173,119 input tokens, 44,703 output tokens, and USD 1.08100275.

After both response ledgers were complete, deterministic scoring opened the
hidden package and stopped with `public and hidden packages are not paired`.
The scorer required equal dataset IDs and split labels, while the frozen public
and hidden packages intentionally use distinct IDs and `*-gold` split labels.
This is an evaluation-harness contract defect. It prevents authoritative metric
calculation even though the case identities themselves were validated earlier.

The raw response distribution is retained only as a descriptive diagnostic:
the candidate emitted 475 abstentions and 25 academic-integrity refusals; the
control emitted 95 abstentions and five refusals. Neither condition released an
answer. That strongly suggests a product-method problem in addition to the
scoring defect, but it is not presented as a registered accuracy result because
the preregistered scorer did not complete.

The ignored artifacts are preserved by these SHA-256 hashes:

- terminal state: `baaa34bbfbe89ae3245ccb2f3a76acf2dea026d2239df4bece738b366c6e60a3`;
- candidate responses: `fcc21868f495b52d16fb1580e27f51040c5b2a8d5e36852ef744af31100923d5`;
- candidate provider ledger: `55766e1dc7242df99afa39a5dfeee885bb01deb1d922afc715ed1f52cfa9651c`;
- candidate state: `52d7be76b56b6f4316a2de7be72480a748c570cc0a27e9716d4e9c4ad074d950`;
- control responses: `5ecddae990e70987fe87e391101139d163e0a61b38b1e1cef67873bc85d5ff24`;
- control provider ledger: `04e581571aff3fe8a901f0fcec2ddc1ee3733c1fc2c02c78963c292fe57b4797`;
- control state: `67503e0c6db335213e0916a1dc0d14cc13424b3943e60f01c031e5fecb6bad64`.

Per the finite plan, this second invalid execution stops checkpoint 006. All
provider and method authority is revoked. There is no third correction, no
advisory audit, no product promotion, no Sunday release claim, and no sealed
10,000-case execution. A new successor requires an explicit method-level
decision that addresses both package-pairing semantics and the all-answer
abstention diagnostic before spending again.
