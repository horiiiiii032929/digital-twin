# Evaluation architecture learning log

## Component

Repository-wide component evaluation records and a versioned system profile for
selecting, swapping, and rolling back algorithms, models, prompts, policies, and
agent behavior.

## Prediction

I expected a shared evidence envelope and component inventory to make future
comparisons consistent without forcing unrelated runtime components into one
generic interface. The main risk was over-engineering a meta-framework before
enough components existed.

## How it works

Runtime contracts remain component-specific. For example, a retriever still
accepts a query and returns ranked chunks, while a generator accepts a question,
retrieved evidence, and tutor policy. The shared evaluation models describe the
parts that comparisons have in common: implementation identity and version,
control versus candidate role, dataset, Git revision, metric thresholds, hard
gates, failure counts, limitations, and the final decision.

The component record validates its own claims. A metric's pass flag must agree
with its direction and threshold. Exactly one implementation is the control. A
selected implementation must be one of the evaluated candidates and must pass
every required metric and hard gate. This prevents an aggregate score from
overriding a privacy, integrity, provenance, or citation failure.

The system profile lists all 14 decision-bearing components exactly once. A
component can be selected, pending, or disabled. Selected components need an
implementation version, evidence, hard gates, and a decision. Pending components
cannot pretend to have a selected implementation. Only an experimental profile
may contain pending entries.

The profile validator checks referenced repository evidence and makes sure a
linked evaluation record selects the same implementation, dataset, and hard
gates as the profile. Swapping a component therefore means adding a candidate
behind its typed contract, evaluating it against the retained control, recording
the decision, changing the profile, and rerunning regressions.

## Evidence

- Experimental profile: 14 components, 5 selected, 9 pending, 0 disabled.
- Standard retrieval record: term overlap control versus BM25 candidate.
- Automated tests cover complete inventory, linked evidence, threshold
  consistency, hard-gate alignment, and hard-gate selection rejection.
- Reproducible command: `npm run verify:profile`.
- Real course materials and private evaluation outputs remain outside Git.

## What failed or surprised me

The most important design choice was what not to generalize. A universal
component execution interface would erase useful types and make invalid data
flows easier. Only evidence and selection metadata are shared; runtime behavior
stays in domain protocols.

The inventory also exposed a useful distinction between tutor policy and policy
enforcement. The structured professor policy already exists and is selected,
but its correct application during live generation is still pending. Treating
them as one component would have hidden that unfinished decision.

## What I learned

Swappability requires more than an interface. It needs the same inputs, a
retained control, versioned configuration, hard eligibility gates, metrics,
failure analysis, and a release profile that records the selected implementation.

I can also explain why "best" is contextual. The selected component is best for
a named dataset, policy, resource budget, and system profile. It is not a
permanent or universal SOTA claim.

## Next decision

Use this architecture in issue #24 without building additional generic runtime
machinery. Compare deterministic and live generator implementations, keep prompt,
policy enforcement, and citation validation separately measurable, then update
the profile only after their evidence exists.
