# Firebase Function agent instructions

The root `AGENTS.md` also applies. This is an independent Python 3.15 project;
do not merge its dependency environment with the FastAPI app.

## Invocation and output

- Keep `dad_joke` GET-only and `invoker="private"`: successful calls consume
  Vertex AI quota. Callers need `roles/run.invoker` on the backing Cloud Run
  service and an ID token.
- Validate model output strictly; return sanitized 503 or 500 responses. Logs may
  include stable status or exception type, never prompts, generated output,
  exception strings, credentials, or user data.
- Verify `result.output` is the expected Pydantic model; Genkit's `output_schema`
  alone is insufficient. Map schema/output-type failures to retryable, sanitized
  `INVALID_MODEL_OUTPUT` 503. Keep topic parsing in a narrow exception boundary so
  downstream `ValueError` failures remain generic 500 responses.
- Keep deployment region `europe-west4` separate from Vertex AI location `global`
  and model alias `gemini-pro-latest`. The alias may change behavior, latency, or
  cost without a code change. Preserve output validation, tests, quota/spend
  monitoring, and explicit production verification when changing model settings.

## Dependencies and deployment

- Python 3.15 is a local and future deployment target, not a claim of current
  Firebase support. Check official runtime and Firebase CLI support before
  deployment or emulation. Keep `firebase.json` aligned; do not substitute 3.14.
- Keep `functions/requirements.txt` limited to direct runtime packages pinned
  from `functions/uv.lock`. Do not hand-edit it or export transitive dependencies;
  use `just sync-functions-requirements`. Follow the root exporter instructions
  when adding or removing dependencies.

## Tests

Use the local `adversarial-testing` and `pytest-testing` skills. Test handler
behavior and deployment-manifest controls with `just test-functions`. Isolate
Genkit reflection infrastructure and never call Vertex AI in unit tests.
