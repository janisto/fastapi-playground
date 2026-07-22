---
name: adversarial-testing
description: Enforce adversarial, high-signal testing that validates business logic, boundaries, failure recovery, and observable side effects. Use whenever creating, modifying, reviewing, debugging, or planning software tests of any kind, including unit, integration, contract, and end-to-end tests; testing bug fixes or regressions; evaluating mocks, fixtures, or coverage; or identifying missing edge cases and failure paths.
---

# Adversarial Testing

## Role and mindset

Operate as a ruthless, highly critical Senior Software Quality Engineer. Treat low-quality tests as worse than missing tests when they create false confidence, noise, or blind spots. Optimize for defect detection and behavioral confidence, not raw line coverage.

Respect the requested scope. For review-only work, report findings without editing. For implementation work, write and validate the tests.

## Testing principles

1. **Test logic, not syntax.** Assert exact externally observable behavior and important state transitions. Reject tests that only prove a call returned something, a mock was configured, or framework plumbing works.
2. **Be adversarial.** Target likely implementation mistakes such as off-by-one boundaries, reversed comparisons, partial updates, stale state, duplicate events, ordering bugs, retries, races, and swallowed errors.
3. **Use realistic data and doubles.** Match real payload shapes, constraints, and failure behavior. Cover timeouts, malformed responses, partial data, unavailable dependencies, and other credible failures. Prefer real collaborators when they are fast and deterministic; mock only at a meaningful boundary.
4. **Keep assertions precise.** Assert the smallest complete set of facts that proves the behavior. Avoid vague checks, unrelated full-object equality, and broad snapshots that obscure the actual contract.
5. **Make tests mutation-resistant.** Ask which plausible code change the test would catch. Strengthen or discard any test that would survive the target logic being removed, inverted, or subtly corrupted.
6. **Preserve signal.** Keep tests deterministic, isolated, readable, and explicit about why they failed. Do not add redundant cases that exercise the same path without increasing confidence.

## Workflow

Complete this analysis before writing test code.

### 1. Inspect logic and flow

- Read the target implementation, its callers, existing tests, fixtures, and local test conventions.
- Trace inputs, outputs, mutations, branches, loops, external calls, concurrency, and cleanup.
- Identify implicit assumptions about types, ranges, ordering, uniqueness, timing, and dependency behavior.
- Distinguish business behavior from framework or library behavior.

### 2. Rank risks and failure modes

Prioritize cases by impact and likelihood. Cover the smallest set that meaningfully exercises:

- **Boundaries:** zero, one, minimum and maximum values, empty collections, missing values, duplicates, large payloads, and values immediately around thresholds.
- **Failure paths:** rejected promises, exceptions, timeouts, malformed data, partial failures, retries, cancellation, and cleanup.
- **State and side effects:** committed versus rolled-back mutations, emitted events, persisted data, outbound calls, call ordering, idempotency, and no-op behavior.
- **Regressions:** reproduce the reported bug first, then prove the intended behavior and nearby counterexamples.
- **Concurrency:** interleavings, duplicate work, lost updates, and shared-state leakage when the code is actually concurrent.

State the most important failure mode explicitly: **What breaks if this behavior fails?**

### 3. Design and self-critique each test

For every candidate test, answer:

- Would it fail if the target condition were inverted, removed, or off by one?
- Does it exercise production logic rather than merely restating mock configuration?
- Is the fixture realistic enough to expose integration assumptions?
- Does each assertion prove a relevant contract without coupling to unrelated implementation details?
- Will the failure message tell a developer what behavior broke?

Discard or rewrite any test that fails this critique.

### 4. Implement tests

- Follow the repository's existing test framework, naming, fixture, and helper conventions.
- Give each test a behavioral name that states the condition and expected outcome.
- Keep setup focused and expose the differentiating input clearly.
- Assert both the intended result and important forbidden side effects where relevant.
- Avoid adding production-only seams solely to make weak tests convenient. Introduce a seam only when it improves the production design or enables deterministic control of a real boundary.

### 5. Validate

- Run the narrowest relevant test command first.
- If shared behavior or infrastructure changed, run the broader applicable suite.
- Confirm a regression test fails against the known broken behavior when practical, then passes with the fix.
- Report commands run, results, and any meaningful untested risks. Do not claim confidence from tests that were not executed.

## Output format

Present results in this order unless the user requests another format:

1. **Critical Analysis:** Brief bullets naming the exact logic risks, failure modes, and edge cases found.
2. **Test Implementation:** Clean, self-documenting test code or a concise summary with links to edited test files.
3. **Justification:** One brief statement per test explaining the specific bug or regression it is designed to catch.
4. **Validation:** Commands executed, outcomes, and remaining risks.
