# True-visual product checkpoint 001 results

## Decision

`completed-refine`. Retain `text-ocr-fallback` for Local R1.1.

## Result

The actual product completed all 120 durable responses before hidden gold was
opened: 30 answerable and 30 boundary cases for both control and candidate.
Both conditions reached 20/30 fully grounded visual answers. The candidate
therefore provided no product-level gain over text/OCR and missed the 27/30
gate. All 30 candidate boundary cases avoided an answer release, but one
answerable case cited the wrong region, producing one unsupported claim and one
invalid citation. Original-region lineage was complete for 20/30 cases.

The ten answerable failures comprised two tables, six equations, and two
diagrams. Nine safely abstained; one answered from the adjacent wrong equation
region. Only eight questions activated the visual route, which is a measured
method limitation rather than a post-result tuning target.

## Operations

- Jina calls: 8/60, all completed, zero retries/failures.
- Query tokens: 113; account total including imported use: 144,752/10,000,000.
- Candidate visual p95 latency: 2.743 seconds.
- Text-path regressions and wrong-course retrievals: 0.
- Private data and known 10,000+1,000 benchmark access: 0.

The same 60 cases will not be tuned or rerun. A future visual successor requires
new representative cases and a preregistered method comparison.

## Links

- [Machine-readable record](records/true-visual-product-checkpoint-001.json)
- [Issue #131](https://github.com/horiiiiii032929/digital-twin/issues/131)
- [Issue #210](https://github.com/horiiiiii032929/digital-twin/issues/210)
