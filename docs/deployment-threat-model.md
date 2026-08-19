# Deployable product threat model

Status: reviewed local candidate; revisit before real course data or users

## Assets and trust boundaries

Protected assets are account credentials, session tokens, professor policy,
approved source files, derived crops, releases, student conversations,
citations, audit records, provider credentials, backups, and deployment
configuration.

```text
Untrusted browser
  -> Caddy HTTPS / same-origin boundary
  -> FastAPI credential + role + course boundary
  -> SQLite WAL + content-addressed object volume
  -> leased ingestion worker
  -> optional approved DeepSeek boundary
```

Administrators provision identity; professors own courses, sources, policy, and
publication; students read only assigned published courses and their own
conversations. The host operator controls containers, volumes, environment,
backups, and DNS and is therefore trusted with all staging data.

## Threats, controls, and residual risk

| Threat | Implemented control and verification | Residual risk / next gate |
| --- | --- | --- |
| Credential theft | Versioned salted scrypt hashes; no password logging; 12-character mixed-case/number floor; admin reset; self-service rotation | No MFA, breached-password service, or institutional SSO |
| Session theft/fixation | 48-byte opaque token; digest-only storage; Secure, HttpOnly, SameSite=Strict cookie; expiry, logout, account-wide revocation | One-host cookie session; no device/session UI |
| CSRF/cross-origin mutation | Strict SameSite plus exact Origin check on unsafe authenticated requests | Reverse proxy/origin configuration must stay exact |
| Client identity spoofing | `X-Account-ID` is rejected in staging; server session determines role/account | Demo/test deliberately retains synthetic headers |
| Horizontal/vertical authorization leak | Role checks plus professor ownership, membership, release, conversation, citation, and job scoping; cross-role/user/course tests | Every future route must reuse the same dependencies/domain checks |
| Malicious or oversized file | PDF content type/signature and byte limit; parser failure is safe; atomic source writes | No antivirus/CDR; complex parser vulnerabilities remain possible |
| Path traversal/object replacement | Content-addressed keys, validated namespace/suffix, root containment, atomic mode-0600 writes, checksum verification | Single host operator can still read/alter the volume |
| Worker crash/duplicate upload | Idempotency key binding; transactional claim; lease expiry recovery; retry/cancel; bounded attempts | No distributed queue or worker heartbeat dashboard |
| Migration/data corruption | Ordered checksummed transactional migrations; WAL/foreign keys; failed migration rollback; readiness | SQLite is single-host and not horizontally writable |
| Backup theft/tampering | Archive checksums, safe paths, mode 0600, clean-target restore and integrity check | Encryption/off-host retention depends on operator-approved storage |
| Incomplete deletion | Confirmation-bound CLI; explicit account/course graph deletion; tracked raw/derived artifacts removed | Historic off-host backups follow their separate retention policy |
| Sensitive log leakage | Route-template JSON logs only; no query/body/content; sanitized job errors; automated password/content checks | Caddy/host logs need the same retention and access policy |
| Provider disclosure/cost | Deterministic default; explicit mode/key; governed prompt; exact selected binding; call and USD caps; usage trace; safe failure | Private-course provider approval remains required; cost may be unknown if provider omits it |
| Denial of service | Login/session rate limits, upload ceiling, bounded metrics, conservative one-host capacity gate | In-memory limiter is not shared; no upstream WAF or external autoscaling |
| Clickjacking/XSS/content injection | CSP, frame denial, MIME sniffing denial, referrer/permissions headers; evidence treated as data in prompts | Dependency/browser defects and future rich content require review |
| Secret committed to Git/image | `.env*`, data, outputs, and logs ignored; Docker context excludes them; CI dependency audits | Secret scanning/provider rotation still required operationally |

## Hard-stop conditions

Do not expose real users or private course sources if HTTPS, exact origin,
secure cookies, restore rehearsal, account/course isolation, provider approval,
or log redaction fails. Stop external generation at budget exhaustion or model
identity drift. Preserve the deterministic generator, BM25 retrieval, previous
image tag, previous data volume, and local demo as separate rollback layers.

## Known limitations

The 41/41 development result is synthetic and single-process. It does not
establish public certificate issuance, external alert delivery, multi-host
consistency, institutional identity, encrypted off-host backups, real PDF
robustness, human usability, learning impact, or production SLA. Public staging
and any user study require the separate privacy/consent and pilot gates.
