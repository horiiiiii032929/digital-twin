# Decision-preserving coding repair: slide-codefix-002

The user explicitly prohibits any change to application decisions. Preserve all
contracts from the prior slide-aligned plan and the 70-slide deck fingerprint.
Control is the deployed dirty manifest retained in
`output/browser-qa/slide-codefix-002/deployed-manifest.json`.

Investigate two metadata defects only: (1) draft usage lost when audit history/input
adaptation fails after a successful draft, and (2) bounded schema error locations
already known to the transport are dropped at the audit boundary. No validation,
model, prompt, retry, state-transition, policy, consent or scheduling change.

Prediction: invalid input still produces the exact same failure text, action and
citations, with the same provider requests and call counts; only accounting and
sanitized diagnostics change. Valid inputs and all audit decisions remain identical.
Synthetic cases cover failed history adaptation after one draft, valid histories,
missing/extra fields, unit/dimension model-validator errors, malformed repairs,
unknown/private field names, excessive/untrusted diagnostic values and existing
18 contract controls. Provider calls for local fixtures are zero. First reproduce
the accounting failure before editing. Compare the candidate with the actual
control file and record all outcomes under slide-codefix-002. Live checks, if needed,
use at most four fresh synthetic turns; do not alter existing user conversations.

No decision-changing workaround is permitted even if it lowers observed failures.
Unknown provider causes remain unresolved. Deploy only after relevant component,
API and unchanged-decision gates pass; preserve data and 03:00 Singapore shutdown.
