# GitHub public-history purge closure

Date: 2026-08-14

Status: Closed

## Incident boundary

Superseded public commit
`02dbf8dedf9e5728a3c765b1e6e8616366fc3721` contained private,
source-derived course authoring content. The active branch and draft PR were
rewritten to remove that commit, but the remote privacy boundary remained open
while the unreferenced object was still retrievable by SHA.

GitHub Support request `4659958` asked GitHub to clear cached views and
pull-request references and garbage-collect the unreferenced object.

## Closure evidence

On 2026-08-14, the authenticated Support portal showed request `4659958` as
closed. GitHub Support reported that its reference check found no remaining
references and that server-side garbage collection and cached-view clearance
had completed.

Two read-only checks then confirmed the remote object was no longer
retrievable:

```text
gh api repos/horiiiiii032929/digital-twin/commits/02dbf8dedf9e5728a3c765b1e6e8616366fc3721
exit: 1
response: HTTP 422, no commit found for the SHA

GET https://github.com/horiiiiii032929/digital-twin/commit/02dbf8dedf9e5728a3c765b1e6e8616366fc3721
response: HTTP 404
```

The private Support conversation and any screenshots remain outside Git. This
durable record retains only the minimum closure facts needed for auditability.

## Decision and limitations

The remote privacy boundary is closed, and the GitHub purge no longer blocks
creation of the course-tutor authoring seal. This administrative closure does
not approve the authoring dataset or change any model-review result. The
blinded independent-human audit and its validation remain mandatory before
sealing.

Local ignored artifacts and any local unreachable Git objects remain governed
by the repository's private-data boundary. They must not be pushed, attached to
issues or pull requests, or included in committed generated output.
