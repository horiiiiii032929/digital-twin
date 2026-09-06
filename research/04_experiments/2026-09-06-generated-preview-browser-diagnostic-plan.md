# Generated preview browser operational diagnostic

Run ID: `generated-professor-preview-browser-development-001-live-001`.
This separately authorized operational diagnostic uses the existing unselected
V14-medium experimental composition. It does not depend on a final-verifier
quality pass and cannot qualify that candidate, professor fidelity or learning.

Compare expectation-only guidance with actual generated, saved and reviewable
responses in the same local professor interface. Use an isolated loopback HTTPS
server provisioned by the existing load runner's `--serve` fixture, synthetic
professor/student accounts, and permitted synthetic lecture/transcript/forum
sources. No production deployment, real student data or professor contact.
Freeze copied source/frontend build, candidate configuration, this plan and input
cases before any provider call. The server shares a hard maximum60 calls and
USD9.60 with USD0.16 reservation per call across this entire diagnostic; no reset
of the budget for a second artifact or retry. Use existing V14-medium roles and
caps, record actual provider identity, effort, usage, failures and latency.

The primary UI case asks “After how many ticks does Glimmer lease expire?” under
an explanation-first synthetic profile, with optional second turn “Explain the
condition from the source.” A contrasting Socratic draft may use the same first
question if needed to exercise stale profile/source review. At most two generated
artifacts, each one fictional case of one or two turns; retain all outcomes.
Unknown usage or provider failure stops further generation. Approval of a synthetic
artifact tests binding only, not a judgment of genuine instructor quality.

Required checks: browser login, course/profile navigation, clearly distinct static
expectations, actual generate/save operation, displayed source/provenance/hash,
explicit case decision submission bound to the exact saved artifact, refresh/GET
persistence without new calls, and no student conversations/outreach/learning-gap
writes from preview processing. Capture before/after database counts through a
read-only connection. Inspect response bytes and approval request/response binding.
Attempt stale approval after changing a synthetic draft or source through existing
APIs/UI when accessible; if this cannot be exercised without changing the approved
artifact's experiment scope, record it as untested rather than claiming a pass.
Use screenshots, browser console/network observations and exact artifact hashes.

Pass requires all executed operation checks to match their explicit contracts;
any binding/privacy/persistence defect fails the corresponding gate. Safe generated
failure is an observed operational failure, never a quality pass. Report incomplete
checks and the model's actual answer separately. This small local journey is not
load, deployment, human-fidelity or educational evaluation. If a bug appears,
report it before expanding scope; any narrow fix needs relevant regression checks
and a separately identified rerun. Preserve the original failed evidence.
