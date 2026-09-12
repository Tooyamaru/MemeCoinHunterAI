# P08 — Risk/Capital Authority Remediation Authorization

**Status:** PROSPECTIVE LIMITED REMEDIATION AUTHORIZATION / ACTIVE FOR FUTURE EDITS ONLY  
**Phase:** P08 — Outcome Learning  
**Authorization date:** 2026-09-12  
**Precondition:** Failed `docs/P08-RISK-CAPITAL-AUTHORITY-IMPLEMENTATION-AUDIT.md`

## 1. Purpose and authorization effect

This document authorizes a narrow, prospective remediation of the failed
Risk/Capital Authority Safe V1 implementation audit.

This is a new authorization for future remediation edits only. It does not
retroactively authorize the earlier implementation, earlier tests, earlier
runtime behavior, or any earlier result. The prior implementation remains
subject to the failed implementation audit and cannot be treated as closed,
approved, or authorized by this document.

This authorization does not close the Risk/Capital Authority, change
`PROJECT_STATE.md`, or grant any live, economic, provider, execution, or
settlement authority.

## 2. Exact authorized files

Future remediation edits are authorized only in these two files:

1. `core/risk/paper_risk_capital_authorization.py`
2. `tests/test_paper_risk_capital_authorization.py`

No other source, test, documentation, configuration, dependency, workflow,
API, schema, or runtime file is authorized by this document. In particular,
this authorization does not authorize edits to:

- P05, P06, P07, G1, G2, G3, G4, P08-T07, or P09;
- `PROJECT_STATE.md`;
- `.replit`;
- package manifests, lockfiles, or dependency configuration;
- exports, workers, services, routes, databases, migrations, or persistence;
- provider adapters, network clients, or integration configuration; or
- any existing specification, audit, re-audit, or governance document.

## 3. Required remediation

The authorized remediation must address every failed or blocked finding in the
implementation audit while preserving the already approved Safe V1 boundary.

### 3.1 Unsupported policy evaluator versions

Unsupported policy evaluator versions must fail closed and must never produce
`APPROVED`.

The implementation must validate the supported Safe V1 policy and evaluator
versions before applying approval predicates or paper-limit formulas. Focused
tests must prove that unsupported versions cannot produce approval.

### 3.2 Complete canonical provenance

Provenance must be complete, canonical, immutable, and bounded according to
the Safe V1 specification.

The remediation must:

- require the specified reproducibility references;
- preserve the relevant P05/P06 versions and digests;
- preserve policy, Risk Governor, capital-authorization, and evaluator
  references;
- preserve risk, capital, and exposure state identities and digests;
- reject floating-point values;
- reject opaque, executable, credential-bearing, unbounded, or otherwise
  non-canonical values; and
- ensure provenance participates in the verified canonical digest.

Incomplete or malformed provenance must fail closed and must not produce
`APPROVED`.

### 3.3 Deterministic duplicate and contradiction handling

Duplicate and contradiction handling must be deterministic and fail closed.

The remediation must validate the exact Safe V1 identity, digest, scope,
timestamp, status, and duplicated-field relationships that are represented by
the two supplied immutable inputs and the result. It must not resolve a
conflict using insertion order, caller preference, freshness, result magnitude,
or any ambient state.

Where the contract represents a duplicate or replay conflict, the implementation
must emit the applicable closed reason code in the fixed precedence order:

- `DUPLICATE_LIFECYCLE_CONFLICT`; or
- `REPLAY_IDENTITY_CONFLICT`.

If the current contract cannot represent a required conflict explicitly, the
remediation must not invent external state or a registry. It must keep the
behavior stateless and document the contract-preserving validation used within
the two authorized files.

### 3.4 Independent result identity and digest validation

Result identity and the SHA-256 result digest must be independently recomputed
and validated.

The remediation must validate all result cross-field identity relationships,
including the lifecycle identity inside `scope_identity`, the linked P06 and
policy digests, required result provenance, fixed contract/evaluator versions,
and the fixed paper-lifecycle-entry effect.

A result must not be accepted merely because it was produced by one factory
path. Direct construction and handoff-compatible result material must remain
immutable, canonical, internally consistent, and digest-bound.

### 3.5 Focused negative tests

The focused test file must add negative coverage for every audit finding,
including at least:

- unsupported policy evaluator versions;
- incomplete provenance;
- floating-point provenance;
- opaque or otherwise non-canonical provenance values;
- contradictory lifecycle and scope identity;
- contradictory linked digests or result fields;
- duplicate and replay conflict behavior;
- deterministic reason-code precedence for the corrected cases; and
- preservation of paper-only P07 handoff behavior.

Tests must remain focused on the two authorized files and must not broaden into
provider, wallet, live-order, settlement, accounting, classification, G2, G3,
G4, or P09 behavior.

### 3.6 Python 3.13 verification

Before any closure claim or implementation re-audit request, verification must
run with the project's declared Python 3.13 runtime:

```text
uv run pytest -q tests/test_paper_risk_capital_authorization.py
uv run python -m compileall -q core/risk/paper_risk_capital_authorization.py
```

An alternate interpreter, supplemental environment, or passing result under
another Python version is not a substitute for the required Python 3.13
verification. `git diff --check` and `git status --short` must also be recorded.

## 4. Preserved Safe V1 boundaries

The remediation must preserve all existing Safe V1 constraints:

- exactly one validated P06 `DecisionIntent` and one immutable
  `PaperRiskCapitalPolicySnapshot`;
- only `APPROVED` or `REJECTED`;
- only the `BUY` plus `WAIT` paper-entry scenario;
- only the
  `PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY` effect;
- explicit caller-supplied timestamps and no ambient clock;
- deterministic canonical serialization, identity, reason ordering, and
  digest behavior;
- virtual paper budget and exposure only;
- provider-neutral, simulation-only, fail-closed behavior; and
- no mutation, resizing, repair, substitution, inference, or re-evaluation of
  P05, P06, or P07 material.

The Risk Governor remains independent from and higher authority than the
Decision Engine. Execution must not bypass the Risk Governor.

## 5. Explicit exclusions

This authorization does not authorize or imply:

- providers, exchanges, venues, RPC, network access, or external APIs;
- wallets, custody, keys, signers, or credentials;
- live orders, execution, broadcast, retries, or settlement;
- accounting, balances, valuation, realized P&L, cost basis, ROI, numeraire,
  or economic classification;
- G2 realization or settlement;
- G3 accounting or economic-result calculation;
- G4 performance classification;
- P09 live execution;
- G1 authority or any later P08 authority;
- database, cache, queue, registry, filesystem, or persistence behavior; or
- any Node/Vite/esbuild recovery, repair, upgrade, installation, or tooling
  change.

Node/Vite/esbuild recovery is explicitly outside this remediation scope.

## 6. Re-audit and closure gate

A fresh formal implementation re-audit is required after the authorized
remediation. The re-audit must review the two authorized files, their focused
tests, the Safe V1 specification and re-audit, the predecessor P05/P06/P07
contracts, and the exact Python 3.13 verification results.

This authorization alone:

- does not authorize closure;
- does not authorize a new runtime release;
- does not authorize updating `PROJECT_STATE.md`;
- does not convert the failed implementation audit to a pass; and
- does not authorize any work outside the two named files.

`PROJECT_STATE.md` must remain open and must not be changed to a closed or
audited-pass state by this authorization. Only a later successful formal
implementation re-audit may support a separately governed project-state
decision.

## 7. Change control

This authorization creates no implementation or test change. It authorizes
future edits only to the two files listed in Section 2.

No commit or push is authorized by this document.