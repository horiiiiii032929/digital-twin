# Cross-course quality development live 004

## Decision

**Refine the conditional response contract and quotation behavior.** Of 44 actual
external calls, 27 succeeded and 17 failed schema validation. Four deliberate
timeouts are separate. The incumbent/candidate mechanical counts were 28/44 and
30/44, but the incomplete model path still prevents a quality qualification.

The same open development packet was used, with revised explanatory rendering
and expanded schema diagnostics. All 88 product cases completed without history
exceptions; frozen file hashes remained unchanged. The 27 successful calls were
all final questions, while all profile-history model calls failed schema checks.

## Newly identified causes

The retained diagnostics locate every unexpected schema failure:

| Field / validation | Calls | Interpretation |
| --- | --- | --- |
| `question_focus` / `string_too_short` | 7 | An always-nonempty field is enforced even for explanatory or boundary outputs. |
| `aspects` / `too_short` | 10 | Unknown-task history clarification can yield no source aspects. |

All failures had HTTP 200 and completed provider status, without refusal or
incomplete-output indication. These are not network outages or token truncation.
The next contract must distinguish required answerable evidence from fields
needed only for a question. Do not weaken the nonempty supported-aspect rule
for an answerable response or the exact source-span rule.

Assistant inspection of successful proposals and delivered content also found:

- The ecology paraphrase and Socratic finals proposed “Seedlings within a fixed
  square boundary”, which is not an exact source substring. Both failed closed.
- The ledger explanatory response contained a supported full sentence followed
  by a redundant subphrase. It passed mechanical coverage but was less clear.
- The ledger Socratic proposal treated the question's unchanged “total balance”
  requirement as unsupported. The source specifies equal debit/credit entries
  without defining the balance aggregate. This is an ambiguity in the authored
  requirement that needs independent review, not an unambiguous model error.
  The existing labels and results remain unchanged.
- Generic Socratic reflection questions show withholding, not demonstrated
  instructional usefulness or adaptation across successful history turns.

These observations are assistant review, not human, instructor or blinded
validation. They identify model, schema, rendering and label-quality causes
separately rather than converting a mechanical pass into semantic certainty.

## Accounting and evidence

Input/output/total tokens: 30,739 / 7,595 / 38,334. Reported cost: **USD 0.0152618**.
The run used the same finite 500-call/USD 5 bounds and two concurrent cases.
The [machine record](records/cross-course-quality-development-001-live-004.json)
contains the dirty revision, captured configuration/hashes and all sanitized
schema-error locations/types. Raw outputs remain unchanged under
`reports/generated/cross-course-quality-development-001-live-004/`.

Register any successor separately. Reusing open development cases may diagnose
the general contract correction but cannot produce independent held-out evidence.
