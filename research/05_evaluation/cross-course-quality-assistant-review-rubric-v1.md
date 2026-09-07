# Cross-course qualitative development review rubric v1

Status: prospective for the next development successor after live 004. This is
an assistant-review aid, not a calibrated independent judge or human rubric
approval. It cannot satisfy the required independent human label review.

Review the actual question, approved profile, actual prior turns, source text,
delivered text and citations before inspecting the automated pass label. Record
dimensions separately; do not average away unsupported content or privacy issues.
Use `pass`, `fail`, `uncertain` or `not-applicable` with a brief source-grounded
reason. Distinguish proposal correctness from what the student actually receives.

| Dimension | Question for the reviewer | Failure examples |
| --- | --- | --- |
| Label validity | Does the authored expected answer follow from the source and question without an unstated assumption? | Undefined ledger total balance; reference ambiguity; gold asks an unnecessary extra detail. |
| Factual correctness/support | Are delivered factual assertions supported by the cited material, including qualifications? | Invented number; changed exclusion rule; citation from the wrong source. |
| Relevance/completeness | Does the response address every requested aspect or explicitly acknowledge missing support? | Topic excerpt instead of algorithm; one of two sources omitted; unnecessary blanket abstention. |
| Explanation clarity | Is the delivered answer understandable without duplicate fragments or misleading wording? | Whole sentence followed by repeated subphrase; bare fragment requiring hidden context. |
| Explicit profile adherence | Does actual content follow approved explain-first or withhold-first preference at this stage? | Generic question despite explanatory setting; complete solution before a Socratic attempt. |
| History progression | Does the tutor use actual prior turns, acknowledge attempts and advance appropriately? | Repeating an unchanged generic question after an attempt; assuming an attempt not made. |
| Question usefulness | Does a question help identify a specific reasoning step or misconception? | Merely repeating the original question and asking what is unclear. Such a question is not automatically a failure, but requires a reasoned usefulness judgment. |
| Boundary/privacy wording | Does it explain the appropriate boundary without inviting disallowed information? | Inviting another student's private transcript after a privacy request; claiming a transport failure means the course lacks evidence. |
| Failure recovery | Is the student told an honest limitation and a useful permitted next step? | Fabrication after failure; repeated ineffective retry instruction; hidden failure scored as success. |

Record uncertainty for reasonable semantic alternatives. A model-selected shorter
quote may answer correctly even when the exact-span scorer fails; conversely,
literal gold text plus unsupported extra prose may pass mechanically but fail
quality. Preserve both the original score and review classification. Never rewrite
consumed labels or retroactively lower thresholds to make an outcome favorable.

For a prospective confirmed label correction, version a new packet and explain
the source/wording rationale before execution. Keep old outcomes and identify
which changes are label/instrument changes versus candidate changes. Report all
reviewed cases and missing reviews, rather than showcasing favorable examples.
