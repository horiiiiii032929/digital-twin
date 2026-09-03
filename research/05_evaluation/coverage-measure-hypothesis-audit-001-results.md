# Coverage-measure hypothesis audit

## Outcome

**No change shipped.** One mechanism inside `_coverage` was named, two
corrections to it were measured, and both were discarded before implementation.
The audit closes the coverage measure as a source of remaining gain and, with
its two predecessors, bounds what public inputs can achieve on this corpus.

## Why the coverage measure was the next candidate

`tie-resolution-hypothesis-audit-001` closed tie-breaking. `wrong-region-selection-audit-001`
closed the coverage threshold. Both converged on the same remaining surface: the
measure itself. In 31 of the 44 incomplete-evidence cases the gold region is
retrieved and scored **below** the threshold, so the question is not which
candidates are admitted but how a region is scored against a target.

## The mechanism

Targets are parsed from the question and mix two kinds of term:

```
target   = 'main void in the operating-systems source section "defs: Exhibit 2"
            (development source example 0065)'
required = [0065, 2, defs, development, example, exhibit, main,
            operating-systems, section, source, void]
gold claim tokens = [int, main, void]        <- every content term present
missing  = [0065, 2, defs, development, example, exhibit,
            operating-systems, section, source]
```

All nine missing terms are **locator terms**: they say where the region lives,
not what it states. Measured across the corpus, 68 of the 108 missing required
terms are carried by the chunk's own provenance and 40 appear nowhere in it.

The locator half is already enforced once, by `_scope`, which uses the source
path and section anchors to reach these candidates at all. `_coverage` then
demands the canonical claim text repeat those same terms — text that by
construction cannot contain them. The gold region carries the entire content of
the target and scores 0.182.

That is a real defect in the measure. Neither available correction to it helps.

## Correction B — credit locator terms from provenance

A required term counts as covered when the chunk's own provenance carries it
(title, locator, source path, course, document id). Threshold, scoping,
dominance scoping and corpus unchanged.

| | A (shipped) | B (locator credited) |
| --- | --- | --- |
| Targets | 554 | 554 |
| **Single leader** | **238** | **226** |
| **Single leader is gold** | **231** | **226** |
| Single leader is wrong | 1 | 0 |
| Single leader on a boundary case | 5 | 0 |
| Tied | 196 | 242 |
| Gold inside the tie | 185 | 208 |

B lifts 18 of the 32 sub-threshold gold targets over the threshold and removes
every wrong and every boundary-case single leader. It still **loses**: correct
single leaders fall by five and ties grow by 46.

The reason is decisive. Locator terms are shared by construction across every
region in the same section, so crediting them raises the gold region and its
siblings by exactly the same amount. The lifted golds arrive inside ties rather
than at the front of them. Adding a term with no discriminating power to the
numerator cannot separate candidates.

## Correction C — remove non-discriminating terms from the requirement

If locator terms cannot discriminate, the alternative is to stop requiring them:
drop from the requirement set every term already carried by all candidates in
scope, and score coverage on the terms that can actually tell them apart. Same
threshold, same scoping, same corpus; the requirement set is the only variable.

| | A (shipped) | C (requirement narrowed) |
| --- | --- | --- |
| **Single leader** | **238** | **234** |
| **Single leader is gold** | **231** | **227** |
| Single leader is wrong | 1 | 1 |
| Single leader on a boundary case | 5 | 5 |
| Tied | 197 | 197 |
| Gold inside the tie | 185 | 189 |

C is also a net loss with no compensating gain, and the transition table says
exactly what it did:

| Transition | Targets |
| --- | --- |
| single leader (gold) → tied (gold) | 4 |
| tied → unresolved | 3 |

The scoped candidate set spans several documents, so the terms every candidate
shares are nearly none, and the requirement barely narrows. Where it narrows, it
only dissolves decisions that were already correct.

## What three measures establish together

| Measure | Correct single leaders | Tied | Gold inside the tie |
| --- | --- | --- | --- |
| A — shipped | 231 | 196 | 185 |
| B — locator credited | 226 | 242 | 208 |
| C — requirement narrowed | 227 | 197 | 189 |

Three different definitions of coverage land within five of one another. The
requirement set is not what limits this system.

What limits it is visible in the last column: in roughly 185 targets **the gold
region is already inside the tied leader set**. The system retrieves the right
sentence, admits it, and ranks it first — tied with a sibling that says
something else. `tie-resolution-hypothesis-audit-001` measured every tiebreaker
constructible from the question and the candidate text and found the best one
wrong in 61 of 184.

So the constraint is not detection and not scoring. It is that the tie cannot be
broken from the inputs a public question makes available.

## Consequence for the release

None. The shipped configuration is unchanged: `dominance-scoped-ambiguity-safe-v3`,
50.00% fully grounded factual success, zero severe unsupported releases,
qualified under `local-r1-governed-v2-1-release-qualification-004`.

## Consequence for the claims

The 183 answerable questions refused as `clarify` were previously an open
defect. Across three audits they are now characterised: the gate refuses them
because two admissible regions genuinely disagree and nothing in the public
input selects between them. Refusing is the correct behaviour under that
information. This is a property of the task, not a deficiency of the gate, and
it should be reported as a measured bound rather than as remaining work.

## Method

Zero provider calls. Zero cost. The sealed package was not read, rerun or
rescored. Both corrections were measured by simulation over the 500-case
development region corpus with the shipped adapter, retriever, generator, policy
and gate; no source file was modified and no result was recorded before the
comparison ran.
