# Academic factual-QA confirmation 002 build

## Decision

**Go Deeper.** The public-source confirmation package is ready for one
separately authorized blinded review. This is a build result, not a factual
quality or product result.

## Run identity

- Date: 2026-08-25
- Implementation revision: `7a4ed8b50f28eaf9556bddd1cd9684510a16dd51`
- Working tree: clean at the implementation commit
- Instrument: `academic-factual-qa-confirmation-002`
- Reproduction: the `verify:academic-factual-qa-confirmation-v2-*` commands and
  `npm run check`
- Provider calls, tokens, and cost: zero
- Private or held-out data read: no

## Data and construction

Four commit-pinned public educational repositories contribute 160 exact,
non-overlapping source sections under their recorded Creative Commons terms.
The full repositories remain ignored under `data/external/`; Git contains only
the source manifest, compact evidence excerpts, hashes, and attribution notice.

The deterministic package contains:

- 100 clusters and 200 cases: one answerable and one boundary case per cluster;
- 100 answerable cases across direct text, paraphrase, multi-source, code,
  table, diagram, and equation strata;
- 100 boundary cases across no-evidence, cross-course, ambiguity,
  stale-version, integrity, permission, and unsupported-premise strata;
- 40 source-disjoint calibration controls: 20 clean and 20 corrupted;
- zero normalized duplicate questions, selected source-range overlaps, or
  confirmation/calibration source overlap.

Evidence excerpts are exact contiguous source substrings with offsets and
hashes. Diagram cases bind either a public dependent asset or an embedded
notebook image.

## Review workflow verification

The blinded packet contains 40 calibration items followed by 200 confirmation
items. It omits case IDs, clusters, strata, gold labels, mutation labels,
generator identity, and other votes while exposing the candidate record and
the source material needed to assess it.

The network-free runner passed clean, calibration-failure,
disagreement-overflow, malformed-output, identity, accounting, interruption,
and resume tests. It requires three calibrated reviewer families and unanimity;
every disagreement plus a seeded 20-case unanimous sample enters the researcher
packet. More than 40 disagreements fails the panel instead of expanding the
audit indefinitely.

## Verification

- Repository correctness: 536/536 audited, zero pending findings
- Execution freeze: active; 71/71 protected entrypoints covered
- Python: 915 passed
- Frontend: 46 passed
- Frontend lint and production build: passed
- Markdown links and `git diff --check`: passed
- Review preflight: `blocked-not-authorized`

The full gate initially exposed that the Markdown checker traversed ignored
third-party snapshots. The checker now uses Git's tracked/untracked,
exclude-standard file set, and two regressions verify that ignored external
content is excluded without hiding reviewable untracked Markdown.

## Validity and limitations

The source and control structure is independently sourced relative to the old
synthetic template pipeline, but semantic correctness has not yet been judged.
LLM-panel agreement will remain advisory silver evidence, not human ground
truth. The current Codex task has seen the controls, so the actual Codex vote
must run in a fresh isolated task that receives only the blinded packet.

No reviewer binding is current, no review is authorized, and no product,
Professor Digital Twin, staging, or release claim follows from this build.

## Next checkpoint

Refresh and freeze exact reviewer/model/provider bindings, then request one
explicit authorization covering the isolated Codex review and the bounded
provider reviews. After the panel, the researcher audits at most 60 cases and
records `Keep`, `Refine`, or an invalid result before any T0 product comparison.
