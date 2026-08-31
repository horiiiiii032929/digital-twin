# Whole-system architecture development freeze 001 results

## Outcome

**Build-only qualified — Go Deeper.** Three immutable architecture-development
folds are now available without provider calls or paid cost. They contain 495,
497, and 481 cases respectively (1,473 total) across 300 source clusters.

## Data isolation

- The source ranges used by the three folds have zero pairwise overlap.
- Public product inputs and hidden gold are stored in separate files.
- Normalized questions have zero overlap within or across folds.
- Twenty-seven duplicate questions were excluded in a deterministic,
  order-preserving pass. The source datasets were not modified and every
  excluded case ID remains in the freeze manifest.
- Each fold retains its full course-scoped source corpus. A product may retrieve
  from the corpus but receives no expected action, answer, claim, citation, or
  required-source field.

## Decision

Keep the three folds as the only architecture-development datasets for rounds
1–3. Each round uses one fold once for method selection. These folds cannot be
used as the later fresh confirmation tranche.

## Limitations

- The folds use the same four open educational source collections as prior
  work, although their canonical source ranges are disjoint from one another.
- This checkpoint evaluates dataset construction only; it makes no product,
  professor-fidelity, usability, or student-learning claim.
- The final fresh 1,000-case confirmation tranche remains unopened and must use
  a separately frozen source allocation.

## Reproduction

```bash
npm run verify:whole-system-architecture-evolution
```

Provider calls: **0**. Paid cost: **USD 0**.
