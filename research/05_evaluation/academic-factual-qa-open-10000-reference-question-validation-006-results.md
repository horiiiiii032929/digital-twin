# Independent reference-question validation 006

## Outcome

`completed-refine`. The provider-resilient execution was operationally valid,
but the complete-five-question-cluster selection rule produced only 63 of the
required 100 clusters.

## Result

- 106/107 provider calls completed; one isolated batch was quarantined.
- 1,028/1,920 authored question candidates passed every deterministic and blind
  review check.
- 449/640 answerable targets had at least one accepted wording.
- 71/160 source clusters contained five accepted questions; exact modality
  quotas selected 63 clusters and 315/500 cases.
- Fifteen duplicate candidates were rejected.
- Reported completed-call usage was 288,644 input tokens, 210,875 output tokens,
  USD 3.19243675, and 1,249.875 seconds total provider latency.

Overlapping candidate rejections comprised 668 answer-span mismatches, 135
unnatural wordings, 104 action mismatches, 82 ambiguous wordings, and 142
gold-hint leaks.

## Interpretation

The valid result does not justify selecting the complete-cluster method. It also
shows that the all-five rule is the limiting selection unit rather than a lack of
individually valid questions: accepted questions cover substantially more than
the 400 answerable cases needed for a balanced development evaluation when the
question—not the source cluster—is the sampling unit.

The prospective aggregate-007 package therefore preserves only individually
accepted, source-linked questions, balances courses and question positions, and
retains source cluster as the uncertainty unit. It does not reinterpret attempt
006 as a pass, change any accepted vote, or open the product or final split.

## Limitations

- Both model roles are OpenAI configurations, not independent provider families
  or external human annotation.
- The isolated failed provider batch reduced available candidates but did not
  invalidate completed evidence.
- Exact span recovery can reject semantically equivalent answers.
- No product response, private source, or sealed 10,000-case final split was
  opened.
