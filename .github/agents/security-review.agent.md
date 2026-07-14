---
name: security-review
description: Read-only FastAPI and Firebase security audit based on OWASP API Security guidance
---
# Task: REST API Security Review

Perform a comprehensive security review of this FastAPI REST API following OWASP API Security guidelines. **This is a read-only audit**—do not modify code unless explicitly requested.

## Required File Reads

Before analysis, read these files:
1. `app/main.py` - Application setup, middleware, and CORS configuration
2. `app/auth/firebase.py` - Firebase authentication implementation
3. `app/middleware/security.py` - Security headers middleware
4. `app/middleware/body_limit.py` - Request body size limiting
5. `app/core/logging.py` and observability middleware wiring in `app/main.py` - Structured logging with trace correlation
6. `app/core/config.py` - Configuration and secrets handling
7. `app/core/content_negotiation.py`, `app/core/cbor.py`, `app/core/exception_handler.py`,
   `app/core/schema_links.py`, and `app/core/validation.py` - Negotiation, CBOR, Problem Details, schema links, and
   validation-error redaction
8. `app/api/health.py`, `app/api/hello.py`, `app/api/items.py`, `app/api/profile.py`, and `app/api/schemas.py` - Endpoint
   definitions
9. `app/services/profile/service.py` - Business logic
10. `app/dependencies.py` - Shared dependencies and DI aliases
11. `app/exceptions/profile.py` - Domain exception definitions
12. `firebase.json`, `firestore.rules`, `storage.rules` - Emulator, deployment, and data-access policy
13. `pyproject.toml`, `uv.lock`, `functions/pyproject.toml`, `functions/uv.lock` - Dependency boundaries
14. `Dockerfile` and `.github/workflows/` - Build and automation security
15. `functions/main.py` - Vertex AI function, error handling, logging, and runtime limits

## Security Review Checklist

### 1. Authentication & Authorization
- [ ] Public endpoints (`/health`, `/v1/hello`, `/v1/items`, schema and documentation routes) expose no protected data
- [ ] Profile endpoints require the `CurrentUser` dependency backed by `verify_firebase_token`
- [ ] Authorization checks verify user permissions before resource access
- [ ] Token validation distinguishes credential failures (401) from Firebase dependency failures (503)
- [ ] `WWW-Authenticate: Bearer` header included in 401 responses
- [ ] HTTP Bearer scheme properly documented for OpenAPI
- [ ] The model-backed `dad_joke` function remains GET-only and private, with `roles/run.invoker` granted only to
      intended callers

### 2. Input Validation & Data Sanitization
- [ ] Request bodies, path parameters, and query parameters use appropriate Pydantic or FastAPI validation and constraints
- [ ] Path parameters have proper type constraints
- [ ] FastAPI query parameters use `Query()` or equivalent constraints; the Function topic is validated with `JokeTopic`
- [ ] Request body limits enforced (check `body_limit.py` middleware)
- [ ] If file uploads are introduced, type, size, and content are validated
- [ ] Firestore document paths and query values are derived from validated inputs

### 3. Security Headers (OWASP Recommended)
Verify the configured behavior in `SecurityHeadersMiddleware`:
```http
Cache-Control: no-store
Content-Security-Policy: frame-ancestors 'none'
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Resource-Policy: same-origin
Permissions-Policy: accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()
Vary: Accept
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
```

HSTS applies only to HTTPS responses outside debug mode. CSP is intentionally omitted from `/api-docs`, `/api-redoc`,
and `/openapi.json`; other security headers must remain. Content type varies between JSON, CBOR, schema documents, and
HTML documentation.

Cloud Run terminates TLS before proxying HTTP to the container. Verify the image runtime trusts the platform's
forwarded headers and that a deployed HTTPS `/health` response includes HSTS; do not infer this from local plain HTTP.

### 4. Error Handling & Information Leakage
- [ ] Error responses use generic messages (e.g., "Unauthorized" not token details)
- [ ] Stack traces never exposed in production (`debug=False`)
- [ ] Internal exception details logged but not returned to clients
- [ ] 404 vs 403 responses don't leak resource existence
- [ ] Validation errors redact sensitive input values while retaining public field locations
- [ ] Missing-field errors cannot reflect a complete request body, and compound secret field names remain redacted

### 5. Logging & Monitoring
- [ ] Authentication failures use appropriate warning/exception records without token or profile data
- [ ] Sensitive data (tokens, passwords, PII) never logged
- [ ] Security events use appropriate log levels (WARNING/ERROR)
- [ ] Request IDs and access records include status and route metadata for correlation
- [ ] Trace fields represent incoming correlation only; the middleware does not claim to create spans
- [ ] External alerting requirements are reported separately from code findings

### 6. Secrets & Configuration
- [ ] No hardcoded secrets, API keys, or credentials in code
- [ ] Secrets loaded via environment or Secret Manager
- [ ] `pydantic-settings` used for configuration
- [ ] Service account files excluded from version control
- [ ] Debug mode disabled in production configuration

### 7. CORS & Origin Policy
- [ ] CORS origins explicitly defined (no wildcards in production)
- [ ] Credentials allowed only from trusted origins
- [ ] Preflight requests handled correctly
- [ ] Methods and headers properly restricted

### 8. Rate Limiting & DoS Protection
- [ ] Absence of application rate limiting is documented as a deployment control, not automatically reported as a vulnerability
- [ ] Request body size limits enforced
- [ ] Timeouts configured for external service calls
- [ ] Pagination limits on list endpoints

### 9. Insecure Direct Object References (IDOR)
- [ ] Users can only access resources they own
- [ ] Resource ownership verified before read/update/delete
- [ ] Resource identifiers do not substitute for ownership checks
- [ ] Bulk operations validate all resource access

### 10. Dependency Security
- [ ] Root and Functions lockfiles match their manifests and resolve (`uv lock --check` and
      `uv lock --project functions --check`)
- [ ] Vulnerability-scanning evidence is reported when available; freshness alone is not treated as proof
- [ ] Runtime dependencies exclude test-only packages
- [ ] `functions/requirements.txt` pins only direct runtime packages from `functions/uv.lock`

## Output Format

Provide findings in this structure:

### Critical Issues
Issues requiring immediate attention (authentication bypass, data exposure, injection).

### High Priority
Significant security gaps (missing authorization, weak validation).

### Medium Priority
Best practice violations (logging gaps, incomplete headers).

### Low Priority / Recommendations
Enhancements for defense in depth.

### Security Strengths
Patterns implemented correctly that should be maintained.

For each finding include:
- **Location**: File path and line number
- **Issue**: Clear description of the vulnerability
- **Risk**: Potential impact if exploited
- **Recommendation**: Specific remediation steps

If a severity has no findings, state `None`. Separate confirmed vulnerabilities from deployment or monitoring controls
that cannot be proven from the repository.
