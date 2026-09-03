# Persona wording bank 022 attempt 002

## Outcome

`completed-go-deeper`. GPT-5.4 nano produced 46/46 structured batches with
zero retries, identity drift, transport failures, or private data. Deterministic
semantic validation accepted 1,008 of 1,104 utterance variants (91.30%). The
remaining 96 semantic frames are not silently accepted: selection 022 will use
their original canonical wording and report that 8.70% fallback rate.

## Accounting

- Input/output tokens: 128,050 / 70,994.
- Reported cost: USD 0.1143525.
- Maximum batch latency: 107,389.91 ms.
- Provider calls: 46/46; retries: 0; failed calls: 0.

## Analysis correction

The initial runner output labelled coverage below 95% as `Refine`, but no such
threshold existed in the preregistered instrument. The instrument explicitly
defined rejected or missing wording as a recorded canonical fallback. The
durable record therefore corrects the decision to `Go Deeper`; provider output,
accepted bank entries, rejections, requirements, and accounting are unchanged.

This is only an input-variation artifact. It does not select an agent or support
a product-release claim.
