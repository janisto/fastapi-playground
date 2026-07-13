---
name: readme-maintenance
description: Audit or update fastapi-playground README.md when routes, configuration, development commands, middleware, observability, Firebase, containers, Cloud Run, Cloud Functions, or CI guidance changes.
---

# README maintenance

Read `AGENTS.md`, then verify every affected `README.md` claim against the current repository. Keep the README focused
on software engineers and new contributors; keep agent execution rules and detailed coding patterns in `AGENTS.md` or
task-specific skills.

## Sources of truth

- application and middleware: `app/main.py`, `app/core/config.py`, and affected `app/api/` modules;
- public contracts: response models, `app/core/cbor.py`, `app/core/exception_handler.py`, and integration tests;
- persistence and authentication: `app/core/firebase.py`, `app/auth/firebase.py`, and `app/services/`;
- commands and containers: `Justfile`, `Dockerfile`, `.env.example`, and `firebase.json`;
- separate function project: `functions/main.py`, `functions/pyproject.toml`, and `functions/README.md`;
- automation and versions: `.github/workflows/`, `pyproject.toml`, `uv.lock`, and `functions/uv.lock`.

## Accuracy rules

- Require every named path, command, route, default, and environment variable to exist.
- Describe `/health` as dependency-free liveness, not Firebase readiness.
- State that JSON is the default and CBOR requires explicit `Accept` negotiation.
- Describe request observability according to `fastapi-request-observability`; do not document deleted local helpers.
- Keep the root app and `functions/` dependency environments distinct.
- Do not claim deployment, production readiness, rate limiting, tracing creation, or CI coverage that the repository
  does not implement.
- Remove stale material instead of preserving an old README structure.

Keep project layout concise. Mention `.agents/skills/` as portable workflows and `.github/agents/` as GitHub Copilot
profiles, then point to `AGENTS.md` for the working rules.

## Verification

Dry-run named recipes where practical, search route registration and settings directly, validate links and paths, and
run `git diff --check`. For documentation accompanying application behavior, run `just lint`, `just typing`, and
`just test`. Reread the complete README for contradictions and duplicated guidance before finishing.
