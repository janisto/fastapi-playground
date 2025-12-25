---
mode: agent
name: readme-review
description: Update README.md documentation for FastAPI Playground
---
# Task: Update README.md Documentation

You are tasked with reviewing and updating the README.md file for this FastAPI-based REST API project. This file provides guidance to VS Code Copilot when working with code in this repository.

## Your Mission

Conduct a comprehensive analysis of the entire codebase and update the README.md file to ensure it is 100% accurate, complete, and helpful for future VS Code Copilot interactions.

## Required File Reads

Before making any updates, read these files in order:
1. `pyproject.toml` - Dependencies, scripts, tool configuration
2. `uv.lock` - Locked dependency versions
3. `app/main.py` - FastAPI app factory and lifespan
4. `app/core/config.py` - Settings and environment configuration
5. `.github/copilot-instructions.md` - Coding guidelines
6. All files in `app/routers/` and `app/services/`
7. `Justfile` - Task automation commands

## Analysis Requirements

### 1. Project Overview Verification
- Verify the project description matches the FastAPI REST API implementation
- Check if the stated purpose aligns with actual routers, services, and middleware
- Identify any missing key features (authentication, logging, error handling, etc.)
- Verify OpenAPI/Swagger documentation endpoints are accurate (`/api-docs`, `/api-redoc`)

### 2. Tech Stack Analysis
- Verify all frameworks and their versions by checking:
  - `pyproject.toml` for dependencies (FastAPI, Pydantic, Firebase Admin, etc.)
  - `uv.lock` for exact locked versions
  - Configuration files (`ruff.toml` sections in pyproject.toml, etc.)
- Check Python version requirement (3.14+)
- Verify Firebase/Google Cloud integrations (Admin SDK, Firestore, Secret Manager)
- Identify any packages used but not documented
- Remove any technologies listed but not actually used
- Verify folder structure: `app/`, `functions/`, `tests/`

### 3. Version Verification
- Check `pyproject.toml` for version constraints
- Verify `uv.lock` for actual resolved versions
- Ensure Ruff version aligns with configured rules
- Check `ty` (type checker) version if relevant
- Cross-reference pytest and coverage versions

### 4. Commands Verification
- Verify all commands in `Justfile`:
  - `serve` (dev server with hot reload)
  - `test`, `cov` (pytest and coverage)
  - `lint`, `typing` (Ruff and ty)
  - `check-all` (combined checks)
  - `install`, `update`, `fresh` (dependency management)
  - `clean`, `modernize`
- Document any Firebase-related commands if applicable
- Ensure command descriptions match actual behavior
- Add any missing commonly-used commands

### 5. Architecture & Directory Structure
- Scan the directory structure in `app/`:
  - `main.py` (FastAPI app factory with lifespan)
  - `dependencies.py` (shared dependency wiring)
  - `auth/` (Firebase token verification)
  - `core/` (config, firebase, logging, security, body_limit middlewares)
  - `models/` (Pydantic models: error, health, profile)
  - `routers/` (route handlers)
  - `services/` (business logic, Firestore operations)
- Verify all documented paths exist
- Check that middleware files match documentation
- Verify router files and their endpoints
- Document test file organization (`tests/unit/`, `tests/integration/`)
- Note FastAPI dependency injection patterns

### 6. Automation
- Check for GitHub Actions workflows in `.github/workflows/`
- Document any CI/CD pipelines
- Verify Firebase deployment scripts if present
- Document any build or deployment automation (Dockerfile, Cloud Run)

### 7. Configuration Files
- Document all configuration files and their purposes:
  - `pyproject.toml` (dependencies, Ruff, ty, pytest, coverage config)
  - `Justfile` (task runner commands)
  - `Dockerfile` (container build)
  - `firebase.json`, `firestore.rules`, `storage.rules` (Firebase config)
  - `.editorconfig` if present
  - Environment variables via `pydantic-settings`
  - `.env` pattern (gitignored)

### 8. Development Guidelines
- Extract coding conventions from:
  - `.github/copilot-instructions.md`
  - Ruff rules (line length 120, ANN, FAST rules)
  - Type hints everywhere (avoid `Any`)
  - `async def` for I/O-bound endpoints
  - Pydantic v2 models for validation
- Document FastAPI patterns:
  - Dependency injection via `Depends()`
  - Response models and status codes
  - HTTPException usage
- Identify test patterns (pytest, pytest-asyncio, fixtures)
- Note coverage requirements (aim 90%+)

### 9. Integration Points
- Document FastAPI integrations:
  - Firebase Authentication (ID token verification)
  - Firestore persistence
  - CORS configuration (deny-by-default)
  - Security headers middleware
  - Request body size limiting
  - JSON structured logging with trace correlation
- Note any external APIs or Firebase Cloud Functions integration

### 10. Environment Variables Verification
- Document all required/optional environment variables by checking `app/core/config.py`:
  - `ENVIRONMENT` - development/production
  - `DEBUG` - debug mode toggle
  - `HOST`, `PORT` - server binding
  - `FIREBASE_PROJECT_ID` - Firebase/GCP project
  - `FIREBASE_PROJECT_NUMBER` - optional, project number reference
  - `FIRESTORE_DATABASE` - optional, Firestore database ID (defaults to `(default)`)
  - `GOOGLE_APPLICATION_CREDENTIALS` - service account path
  - `CORS_ORIGINS` - allowed origins
  - `MAX_REQUEST_SIZE_BYTES` - request body limit
  - `SECRET_MANAGER_ENABLED` - enable/disable Secret Manager
- Search for `Settings` class usage across all source files
- Verify `.env.example` or `.env` patterns if present

### 11. OpenAPI Endpoints Verification
- Verify these endpoints are documented and accurate:
  - `GET /api-docs` - Swagger UI
  - `GET /api-redoc` - ReDoc
  - `GET /openapi.json` - OpenAPI JSON spec (if exposed)
- Verify the OpenAPI version in use (3.1.0 typical with FastAPI 0.100+)

### 12. Test Count Verification
- Run `just test` to get current test count
- Do NOT assume a specific test count - always verify with actual execution
- Update test file count by checking `tests/unit/`, `tests/integration/` directories
- Verify coverage thresholds in `pyproject.toml` or coverage config

## Output Requirements

Create an updated README.md file that:

1. **Maintains the current structure** but updates all content for accuracy
2. **Adds new sections** for any significant findings not currently documented
3. **Removes outdated information** that no longer applies
4. **Uses clear, concise language** appropriate for AI assistance
5. **Includes specific examples** where helpful (FastAPI patterns, test examples)
6. **Prioritizes information** most useful for FastAPI development and Copilot

## Markdown Quality Guidelines

- Use consistent heading levels (h2 for sections, h3 for subsections)
- Add a table of contents for README > 200 lines
- Use collapsible sections (`<details>`) for lengthy content like full command lists
- Ensure all code blocks have language identifiers (```python, ```bash, etc.)
- Verify all internal links work
- Use badges sparingly and only for meaningful metrics (build status, coverage)

## What NOT to Include

- Firebase Cloud Functions content if `functions/` is minimal/placeholder
- Dependencies that are only dev dependencies unless relevant to development workflow
- Deprecated features or removed endpoints
- Speculative or planned features not yet implemented
- Hardcoded version numbers that will become stale (prefer constraints or ranges)
- Duplicate information already in copilot-instructions.md

## Monorepo Awareness

- This is a monorepo with `app/` (FastAPI) and `functions/` (Cloud Functions) directories
- README.md is at root level and should primarily document `app/`
- Always clarify which directory commands should be run from
- Document shared vs separate dependency management (`pyproject.toml` vs `functions/pyproject.toml`)
- Note if `functions/` is a placeholder or active

## Important Notes

- Be thorough but concise - every line should provide value
- Focus on FastAPI-specific patterns and async architecture
- Document test coverage requirements (aim 90%+ overall, 100% on critical paths)
- Include "gotchas" specific to this project:
  - Firebase Admin SDK initialization patterns
  - Firestore async operations
  - Pydantic v2 model patterns (`model_validate`, `model_dump`)
  - CORS deny-by-default (must configure `CORS_ORIGINS`)
  - Security headers middleware (HSTS behavior varies by environment)
  - Request body size limit enforcement
- Document both what exists AND how it should be used
- If you find discrepancies between documentation and reality, always favor reality
- Update router/service list to match actual files

## Process

1. First, analyze the entire codebase systematically:
   - List all files in `app/routers/` and `app/services/`
   - Check `app/core/` for middleware and configuration
   - Check `tests/unit/`, `tests/integration/` structure
   - Verify all Justfile commands
   - Review configuration in `pyproject.toml`
   - Check `.github/copilot-instructions.md` for coding guidelines
2. Run `just test` to get actual test count
3. Check `uv.lock` or run `uv pip list` to verify dependency versions
4. Compare your findings with the current README.md
5. Create an updated version that reflects the true state of the FastAPI project
6. Ensure all paths, commands, technical details, and endpoint names are verified and accurate
7. Update test count and coverage metrics to match current state
8. Document any new routers or services that have been added
9. Remove references to deleted files or deprecated features

## Final Verification Checklist

After generating the updated README, verify:
- [ ] All file paths mentioned actually exist
- [ ] All Justfile commands listed are valid
- [ ] Test count matches actual test run output
- [ ] Dependency versions are current (or described generically)
- [ ] No orphaned sections documenting non-existent features
- [ ] Router list matches files in `app/routers/`
- [ ] Service list matches files in `app/services/`
- [ ] Environment variables match actual `Settings` class
- [ ] OpenAPI endpoints are accurate (`/api-docs`, `/api-redoc`)

## FastAPI-Specific Considerations

- Document all middleware with their purposes (security headers, body limit, logging)
- Explain the dependency injection pattern used for Firebase/Firestore
- Detail the Pydantic models and their validation rules
- Document route schemas and OpenAPI integration
- Explain test patterns for FastAPI (TestClient, pytest-asyncio, fixtures)
- Document lifespan events and graceful shutdown if present
- Explain error handling with HTTPException and structured responses
- Detail Firebase Authentication flow and token verification

Remember: The goal is to create documentation that allows VS Code Copilot to work effectively with this FastAPI codebase, understanding the async patterns, dependency injection, Pydantic validation, and testing patterns without confusion or errors.
