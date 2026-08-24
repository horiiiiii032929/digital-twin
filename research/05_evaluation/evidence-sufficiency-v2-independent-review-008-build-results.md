# Evidence-sufficiency independent review 008 build

## Decision

**Go Deeper.** Keep the deterministic source-linked draft authoritative and use
one bounded advisory review through the directly authenticated DeepSeek API.
Paid inference remains unauthorized.

## Why this successor exists

Reviews 002–004, 006, and 007 are preserved as invalid operational attempts.
They repeatedly stopped before useful review evidence because the OpenRouter
inference path did not produce a usable provider response. Review 008 changes
the provider path rather than tuning another prompt or router configuration.

## Frozen build

- Instrument: `evidence-sufficiency-v2-independent-review-008`
- Implementation revision: `8280d72a242bdba2218f13dbadd2455f111f2c61`
- Dataset: unchanged 120-case synthetic-public draft with 80 answer and 40
  abstain cases across nine slices and 40 source versions
- Packet: 12 blinded batches, six clean sensitivity controls, six planted
  defect controls, and at most 12 priority cases
- Reviewer: direct official `deepseek-v4-pro`, non-thinking JSON-object mode
- Bounds: 13 calls, zero retries, no fallback, USD 0.15834 maximum reservation,
  and USD 1.50 emergency ceiling

The [official model and pricing page](https://api-docs.deepseek.com/quick_start/pricing/)
listed the exact model, 1M context, JSON output, USD 0.435/M uncached input, and
USD 0.87/M output on 2026-08-24. The read-only official model-list preflight
also returned the exact model ID. The [official JSON-output guide](https://api-docs.deepseek.com/guides/json_mode/)
supports `json_object`; deterministic code still validates the complete
response schema and cannot be overridden by the reviewer.

## Verification

- Network-free simulation: 13/13 calls and 132/132 judgments accounted
- Sensitivity simulation: 6/6 clean controls and 6/6 defects classified
- Focused verification: 77/77 tests passed
- Live read-only preflight: model identity matched, credential present, and no
  provider/model inference occurred
- Current blockers: provider authorization, instrument freeze, bounded
  allowlisting, and the intentionally dirty build worktree

## Data boundary and limitations

Only synthetic-public content may be sent. DeepSeek's
[privacy policy](https://cdn.deepseek.com/policies/en-US/deepseek-privacy-policy.html)
does not provide a project-specific zero-retention or zero-training guarantee
and states that inputs may be retained under its policy and stored in the
People's Republic of China. This path is therefore unsuitable for private
course, professor, or student content without a later privacy decision.

The build proves orchestration, not reviewer quality or evidence-sufficiency
selection. A separate authorization checkpoint and one completed run are still
required. Even a passing advisory review cannot freeze the dataset or select a
product gate automatically.
