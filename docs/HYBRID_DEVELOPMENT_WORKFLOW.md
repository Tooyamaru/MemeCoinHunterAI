# Hybrid Development Workflow

## Purpose

GitHub is the source of truth, ChatGPT/Codex is the architecture, implementation,
test, and review workspace, and Replit is the interactive runtime and preview
environment. A Replit workspace may be replaced without becoming a separate
source-code authority.

## Standard change path

1. Start from the latest `main`.
2. Read `REPLIT_RULES.md` and `PROJECT_STATE.md`.
3. Create a narrowly named branch such as `feature/...`, `fix/...`, or
   `chore/...`.
4. Inspect only files relevant to the authorized task.
5. Implement the smallest scoped change and its tests.
6. Run focused checks locally, followed by the applicable full checks.
7. Push the branch and open a pull request against `main`.
8. Require the GitHub Actions checks to pass before merge.
9. Use Replit for runtime, UI, and integration validation when the change needs
   an interactive environment.
10. Merge only after review; do not develop directly on `main`.

## Required automated checks

The `CI` workflow runs on pull requests to `main` and on pushes to maintained
development branch families.

- Python: locked `uv` environment on Python 3.13 and the full pytest suite.
- TypeScript: frozen pnpm 10.28.0 installation, workspace typechecks, and
  package builds with the required non-secret build environment.
- Repository hygiene: `git diff --check`.

Provider credentials are not required by CI. Tests that represent provider
behavior must remain deterministic and mocked unless a later specification
explicitly authorizes a separate protected integration workflow.

## Branch and merge policy

- `main` represents the stable, reviewable baseline.
- Feature work does not write directly to `main`.
- One pull request should represent one authorized scope.
- A failing required check blocks merge.
- Real-money trading, wallet signing, broadcast, and live execution remain
  disabled unless separately specified, reviewed, and authorized.
- Secrets belong in environment/hosting secret storage and never in commits,
  test fixtures, screenshots, or logs.

## Replit responsibility

Replit pulls the reviewed GitHub branch, runs the application, and provides UI
or runtime validation. Runtime-only findings return to the same branch as code,
tests, or documentation. Replit must not retain an unpublished divergent copy
of the project.

## Current development boundary

The canonical evidence producer is present and tested with offline fixtures.
Live application integration remains blocked until the project approves both:

1. an authoritative historical market-evidence source with identity,
   timestamps, and provenance; and
2. a deterministic, versioned market-to-signal policy that can produce the
   canonical P04 signal evidence without browser-supplied authority.

G2 realization/settlement remains a separate blocked governance decision. This
workflow change does not authorize G2, wallet integration, signing, broadcast,
live execution, or P09 behavior.
