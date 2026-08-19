# Browser security field notes

## Session lifecycle

The application rotates the session identifier immediately after successful
authentication. A logout invalidates the server-side session before the browser
is redirected.

## Request forgery

The course uses a synchronizer token tied to the active session for
state-changing form submissions. SameSite cookies are treated as an additional
defence, not as a replacement for the token.

## Content Security Policy

A report-only Content Security Policy records violations but does not block the
violating resource. Enforcement begins only after the policy is deployed without
the report-only mode.
