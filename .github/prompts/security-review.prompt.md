---
name: 'REST API Security Review'
description: 'Comprehensive FastAPI security audit based on OWASP best practices.'
argument-hint: 'FastAPI codebase to review for security vulnerabilities.'
agent: 'agent'
tools: ['context7/*', 'read', 'edit']
---
# Task: REST API Security Review

Perform a comprehensive security review of this FastAPI REST API following OWASP API Security guidelines. **This is a read-only audit**—do not modify code unless explicitly requested.

## Required File Reads

Before analysis, read these files:
1. `app/main.py` - Application setup, middleware, and CORS configuration
2. `app/auth/firebase.py` - Firebase authentication implementation
3. `app/core/security.py` - Security headers middleware
4. `app/core/config.py` - Configuration and secrets handling
5. All files in `app/routers/` - Endpoint definitions
6. All files in `app/services/` - Business logic
7. `app/dependencies.py` - Shared dependencies

## Security Review Checklist

### 1. Authentication & Authorization
- [ ] All endpoints require authentication via `Depends(verify_firebase_token)` or equivalent
- [ ] Authorization checks verify user permissions before resource access
- [ ] Token validation handles all error cases (expired, revoked, invalid)
- [ ] `WWW-Authenticate: Bearer` header included in 401 responses
- [ ] No sensitive operations allowed without verified email (if applicable)
- [ ] OAuth2/Bearer scheme properly documented for OpenAPI

### 2. Input Validation & Data Sanitization
- [ ] All inputs validated via Pydantic models with strict types
- [ ] Path parameters have proper type constraints
- [ ] Query parameters validated with `Query()` annotations
- [ ] Request body limits enforced (check `body_limit.py` middleware)
- [ ] File uploads validated for type, size, and content
- [ ] No raw string interpolation in database queries (prevent injection)

### 3. Security Headers (OWASP Recommended)
Verify these headers are set in `SecurityHeadersMiddleware`:
```http
Cache-Control: no-store
Content-Security-Policy: default-src 'none'
Content-Type: application/json
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
```

### 4. Error Handling & Information Leakage
- [ ] Error responses use generic messages (e.g., "Unauthorized" not token details)
- [ ] Stack traces never exposed in production (`debug=False`)
- [ ] Internal exception details logged but not returned to clients
- [ ] 404 vs 403 responses don't leak resource existence
- [ ] Validation errors don't expose internal field names or structure

### 5. Logging & Monitoring
- [ ] Authentication failures logged with context (IP, endpoint, timestamp)
- [ ] Sensitive data (tokens, passwords, PII) never logged
- [ ] Security events use appropriate log levels (WARNING/ERROR)
- [ ] Request correlation IDs present for traceability
- [ ] Suspicious patterns (brute force, scanning) would be detectable

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
- [ ] Rate limiting configured (if applicable)
- [ ] Request body size limits enforced
- [ ] Timeouts configured for external service calls
- [ ] Pagination limits on list endpoints

### 9. Insecure Direct Object References (IDOR)
- [ ] Users can only access resources they own
- [ ] Resource ownership verified before read/update/delete
- [ ] UUIDs or non-sequential IDs used where appropriate
- [ ] Bulk operations validate all resource access

### 10. Dependency Security
- [ ] Dependencies up to date (`uv lock --upgrade`)
- [ ] No known vulnerabilities in dependencies
- [ ] Minimal dependency footprint

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
