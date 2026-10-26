---
name: edit-agent-instructions
description: Review, compact, align, or edit root and nested AGENTS.md files while preserving repository-specific guidance, approval boundaries, and a recommended 32,768-byte instruction budget.
---

# Edit agent instructions

Make instructions easier for agents to discover and execute without losing their
intent. Optimize for clear decisions and preserved constraints, not minimum size.

## Establish authority and scope

- Distinguish feedback from implementation. Keep feedback-only work read-only;
  edit only separately authorized artifacts. Editing instructions does not
  authorize implementation, commits, pushes, PRs, settings changes, or deployment.
- Inventory root and nested `AGENTS.md` files in the requested repositories,
  relevant overrides or configured fallback files, and locally referenced skills.
  Exclude dependency and build output trees unless explicitly in scope. Read
  applicable ancestors before changing a file. Preserve unrelated edits.
- Inspect the owning code, command definitions, configuration, and test layout
  before recommending structural changes. Distinguish checked-out facts from
  assumptions about upstream or deployed state.
- Keep each repository self-contained. Preserve its language, framework,
  architecture, commands, and operational boundaries. Essential repository rules
  must not rely on another repository's instructions or a user's global settings.
  Never expose private coordination identities, paths, or links in public repos.

## Approval before removing guidance

- Obtain explicit user approval before removing guidance, merging duplicate
  guidance, or relocating it out of an existing file. A request to compact or
  align instructions does not itself approve these actions.
- For each proposal, identify the source, retained destination or equivalent rule,
  reason, and risk. Approval may cover an explicitly identified list. Do not
  create a separate report or tracking ledger unless requested.
- Rephrasing and formatting may proceed when editing is authorized and every
  obligation remains intact. If a rewrite loses a condition, exception, rationale
  needed to avoid a known failure, or verification requirement, treat it as a
  proposed removal. Resolve uncertainty before applying it.
- Do not label guidance obsolete, redundant, or generic as a substitute for
  establishing its purpose and obtaining approval. Never weaken requirements to
  make broken code appear compliant.

## Format and compact

- Use ordinary Markdown headings, action-led bullets, and backticks for commands,
  paths, identifiers, and literal values. Use tables for command selection or
  comparisons. Bold labels are optional formatting, not instruction authority;
  do not claim they improve compliance without evidence.
- Align shared wording and notation where the intent is shared. Do not force
  identical headings or layouts onto different repositories. Wrap consistently
  for reviewable diffs; do not attribute reasoning benefits to a line width.
- Prefer one clear instruction per bullet. Preserve its force, trigger, scope,
  exceptions, ordering, and verification. Keep exact contract names and supported
  version policies. Avoid shorthand, cryptic abbreviations, and compressed prose
  that takes longer to interpret.
- Replace repeated explanations with direct phrasing when all intent survives.
  For example, "Prefer no scope; include one only when it materially improves
  clarity" becomes "Add a scope only when it materially improves clarity."
  "Keep each pull request focused. In the body, explain why the change is needed,
  what changed, how it was validated, and any remaining risk" becomes "Keep PRs
  focused; describe the problem, change, validation, and remaining risks."
- Keep agent-relevant setup and commands. Propose consolidating repeated human
  onboarding walkthroughs, feature inventories, exhaustive directory trees, and
  copied examples only after checking what decisions they support.
- Reference maintained local implementations or existing skills when they explain
  a procedure more reliably than copied code. Verify examples and pins against
  their owners; prefer links to pin files over duplicated incidental patch
  inventories when approved. Preserve meaningful minimums and compatibility
  constraints. Do not mechanically delete version numbers or code examples.

## Preserve substantive safeguards

- Retain honest failure reporting, inspection of accepted results for false
  positives, fixes for bug classes, protection against weakening requirements,
  and validation after the final change. Adapt examples to the repository without
  collapsing these obligations into "be honest" or "test thoroughly."
- Check guidance for semantic conflicts before shortening it: generic HTTP tables
  versus exact API behavior, operation IDs versus actual registrations, accepted
  media types versus examples, and forbidden transformations versus intentional
  normalization. Correct them against verified requirements, not assumptions.
- Distinguish test-only production branches and hooks from ordinary dependency
  injection. Preserve legitimate dependency boundaries and prohibit backdoors
  without an ambiguous blanket ban on testability.
- Preserve command semantics: mutating versus read-only, environment/toolchain
  loading, separate modules, optional emulators, and full validation gates. Do not
  replace canonical recipes with raw commands that bypass these properties.
- Keep independently usable automation instructions where applicable: required
  checks, ruleset verification in Chrome, workflow security policy, and deliberate
  upgrades of tools excluded from automation. Do not assume a public repository
  can discover private coordination rules.
- Keep authorization, privacy, migration integrity, write-freeze, backup, cleanup,
  and deployment safeguards discoverable before the affected action. Specific
  safety constraints are not expendable verbosity.

## Scope procedures to their owners

- Keep repository-wide priorities, honesty and scope rules, safety boundaries,
  primary commands, architecture invariants, and task routing in the root.
  Children inherit these rules; avoid copying the whole root into each child.
- Put specialized mechanics in an existing local skill or an appropriately scoped
  `AGENTS.md` when that improves discovery. Add an explicit root instruction to
  read it before relevant work, including production changes that require tests.
  Verify how the target agent discovers nested files; do not assume it does so.
- Follow the real layout: `test/` and `tests/` are different. Go and Rust unit
  tests may live beside production code, so a test-directory guide cannot own all
  testing rules. Do not reorganize code or create empty directories for symmetry.
- Keep independent applications or function modules independently documented and
  retain their complete validation gates. Do not import the main application's
  architecture into an intentionally minimal example.
- Put schema and infrastructure procedures near their owning source when useful.
  Do not place hand-maintained instructions inside generated-only directories.
  Prefer existing guides over a proliferation of new files.

## Recommended size budget

- Prefer fewer than 32,768 UTF-8 bytes per `AGENTS.md` and for the known combined
  applicable instruction chain. This is a portability recommendation, not a hard
  limit. Exceeding it is allowed and never authorizes deleting guidance.
- Count bytes, not words, lines, or characters. `wc -c` measures file bytes. For a
  combined estimate, count the files the loader actually selects, in order, with
  joining separators; include known applicable global or ancestor instructions.
  State the measured scope when the complete chain is unavailable.
- An overage calls for reviewing duplication and placement. Preserve useful,
  coherent guidance when a safe reduction is unavailable; report the size and
  tradeoff. Do not silently truncate, change agent configuration, or call a larger
  configured limit a reduction in instruction size.
- Moving text into a child reduces unrelated tasks' default context. A task under
  that child may still load both files, so check that combined chain too. Moving
  procedures to on-demand skills also does not make the task's needed context
  disappear.
- Different agents have different discovery behavior. For a concrete example,
  consult [Codex instruction discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md#how-codex-discovers-guidance).
  Do not present the recommended budget as a universal runtime restriction.

## Review and validate

- Compare each changed passage with its original. Check preserved obligations,
  approved removals and moves, correct local routing, and absence of private
  references. Read the result as an agent arriving in that repository alone.
- Use relevant local testing guidance when changing test instructions. Keep
  framework-specific behavior, data safeguards, and exceptional operational
  requirements explicit even when moving their detailed procedures.
- Verify referenced local paths and inspect command definitions without running
  mutating commands merely to validate documentation. Check the affected
  instruction-chain sizes, local Markdown links, and `git diff --check`.
- Report changes, per-file and relevant combined byte counts, validation,
  remaining conflicts, and proposals awaiting approval. For feedback-only work,
  report findings without implying the edits have been applied.
