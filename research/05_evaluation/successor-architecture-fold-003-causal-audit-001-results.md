# Successor architecture Fold 003 causal audit

- **Status:** `completed-keep`
- **Decision:** preserve Fold 003 as `completed-refine`; close SA8–SA10 prospectively and evaluate one coherent successor on fresh evidence.
- **Provider use:** none.
- **Open audit findings:** zero.

## What the valid result showed

All 600 graph cells were durable before gold opened, and all conditions preserved scope, citations, authority, and safe fallback. The failure was therefore not a safety collapse. It had three causes:

1. Five otherwise usable planner responses carried non-authoritative `reason_code` text longer than the local contract.
2. Exact agreement with one preferred action was treated as transition validity, even when another action remained inside the professor-approved event envelope.
3. The provisional ordering used exact-action agreement but omitted the preregistered continuous policy utility; deterministic A had the best mean utility (`0.7830`) and lowest mean regret (`0.0057`).

C recovered much of B's model-only degradation, but A beat C on hidden utility in 30 cases while C beat A in 11. The C+V reject-only verifier over-rejected valid moves and materially regressed C.

## Closed findings

| Finding | Closure |
| --- | --- |
| SA8 | Normalize only the non-authoritative reason string before local validation; retain the readable prefix and a deterministic hash. |
| SA9 | Report utility/regret and apply the complete paired decision rule; no past selection is changed because Fold 003 selected nothing. |
| SA10 | Use the deterministic event/action envelope as the hard validity gate; retain preferred-action agreement as a diagnostic. |

The fresh successor begins with deterministic A and permits a model-proposed replacement only when an inspectable value model independently agrees and predicts at least the existing `0.04` utility margin. Provider or semantic failure returns deterministic A; identity drift remains fatal. This successor uses 150 fresh cases and does not rescore or tune Fold 003.
