# Hybrid Development Workflow

## Purpose

GitHub `main` is the source of truth. ChatGPT is the primary controller and
normal architecture, implementation, test, review, and documentation workspace.
ChatGPT Work may be used for heavier multi-step execution when available, but it
does not replace the normal ChatGPT workflow. Replit is fallback-only for a
specific interactive runtime/environment task that cannot be completed in
ChatGPT/Work. A Replit workspace never becomes an independent source-code
authority.

## Standard change path

1. Start from the latest `main`.
2. Read `REPLIT_RULES.md` and `PROJECT_STATE.md`.
3. Create a narrowly named branch such as `feature/...`, `fix/...`, or
   `chore/...`.
4. Inspect only files relevant to the authorized task.
5. Implement the smallest scoped change and its tests.
6. Run focused checks and relevant regressions locally; GitHub CI runs the full
   required suites.
7. Push the branch and open a pull request against `main`.
8. Require the GitHub Actions checks to pass before merge.
9. Use ChatGPT/Work for runtime, UI, or integration validation when supported.
   Use Replit only as a fallback for a concrete interactive environment blocker.
10. Merge only after review; do not develop directly on `main`.
11. After each material milestone, reconcile `PROJECT_STATE.md`,
    `docs/MASTER_BLUEPRINT.md`, `docs/CHANGELOG.md`, and any architecture,
    readiness, workflow, or operator documentation made stale by the change.

## Required automated checks

The `CI` workflow runs full validation on pull requests to `main` and on pushes
to `main`. Ordinary development-branch pushes do not start a second full run;
opening or updating the pull request provides PR validation, and merging
provides a separate post-merge main run. The Python and TypeScript job names and
validation commands remain unchanged, so they remain available as required
checks. Both jobs run independently in parallel.

The existing uv and pnpm dependency caches and locked installs are retained.
Existing concurrency cancels superseded runs on the same PR ref or branch ref;
it does not substitute PR validation for post-merge main validation.

- Python: locked `uv` environment on Python 3.13 and the full pytest suite.
- TypeScript: frozen pnpm 10.28.0 installation, workspace typechecks, and
  package builds with the required non-secret build environment.
- Repository hygiene: `git diff --check`.

Provider credentials are not required by CI. Tests that represent provider
behavior must remain deterministic and mocked unless a later specification
explicitly authorizes a separate protected integration workflow.

## Work-usage efficiency and continuation

Development uses one primary agent by default. Additional agents are justified
only when independent parallel work has a measured benefit; they are not the
default for routine inspection, implementation, testing, or documentation.

In WORK FAST MODE, one Work session produces one scoped deliverable. After
focused validation, publish one PR and stop as soon as its CI starts. Record
the exact head and run for the controller to check separately. Merge still
requires review and exact-head Python/TypeScript PASS, followed by verification
of the exact post-merge main run. Do not wait for CI completion in that Work
session or create an unnecessary closure PR.

To reduce repeated context and tool usage:

1. work on one governed gate at a time;
2. inspect only the current task's listed files;
3. batch related read-only checks when safe;
4. run focused tests and relevant regressions locally; let GitHub CI run the
   full required suites before code merge;
5. do not rerun the full suite for documentation-only changes unless CI or the
   changed workflow requires it;
6. update `PROJECT_STATE.md` as soon as a milestone changes; and
7. commit and publish a narrow checkpoint before available work usage becomes
   insufficient.

If a session stops, the next session resumes from GitHub `main`,
`PROJECT_STATE.md`, and the latest open pull request rather than repeating a
repository-wide audit. A checkpoint must state the completed work, remaining
work, verification already performed, current branch/commit, and explicit
scope exclusions.

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

Replit is a fallback execution environment, not the default development center.
Use it only when a concrete runtime/UI/environment task cannot be completed with
the available ChatGPT/Work tools. When used, Replit pulls the reviewed GitHub
branch and returns findings to that same branch as code, tests, or
documentation. Replit must not retain an unpublished divergent copy of the
project.

## Current development boundary

The bounded controlled-paper Operator Facade and Hunter Room chain is now the
active development boundary. The repository is merged through HR-FND-11:
authenticated readiness, no-I/O prepare validation, explicit prepare gating,
review, two-step run/persist confirmation, case-lifetime/provenance display,
stale-arm invalidation, durable readback gating, manual persisted history/detail,
and explicit browser-memory session cleanup.

Active cases remain process-local and require one stable application process;
no restart-safe or multi-worker active-case reconstruction is claimed. The next
operational verification remains one explicit provider-backed paper-only smoke
sequence when explicitly authorized and runtime secrets are intentionally
available.

No automatic discovery, polling, retry, worker/scheduler loop, wallet/signing,
broadcast, DEX execution, settlement, live trading, or G2/G3/G4/P09 authority
is opened by this workflow.
