# P08 — Risk/Capital Authority Implementation Audit

**Status:** IMPLEMENTATION AUDIT / FAIL — NOT CLOSED  
**Phase:** P08 — Outcome Learning  
**Audit type:** Formal implementation audit  
**Audit date:** 2026-09-12  
**Implementation under review:** `core/risk/paper_risk_capital_authorization.py`  
**Focused tests under review:** `tests/test_paper_risk_capital_authorization.py`

## 1. Audit scope and guardrails

This audit reviews the Safe V1 implementation against:

1. `REPLIT_RULES.md`;
2. `PROJECT_STATE.md`;
3. `docs/P08-RISK-CAPITAL-AUTHORITY-SPECIFICATION.md`;
4. `docs/P08-RISK-CAPITAL-AUTHORITY-SPECIFICATION-REAUDIT.md`;
5. `docs/P05-T03_SPECIFICATION.md`;
6. `docs/P06-SPECIFICATION.md`;
7. `docs/P06-T02_SPECIFICATION.md`;
8. `docs/P07-SPECIFICATION.md`;
9. `docs/P07-T01-SPECIFICATION.md`;
10. `core/decision/decision_intent.py`;
11. `core/opportunity/opportunity_risk.py`;
12. `core/execution/paper_simulation_input.py`;
13. `tests/test_decision_intent.py`;
14. `tests/test_paper_simulation_input.py`; and
15. `tests/test_paper_risk_capital_authorization.py`.

The audit is limited to the two implementation paths named above and their
direct P05/P06/P07 contracts. It does not authorize changes to source code,
tests, dependencies, APIs, P07, G1/G2/G3/G4, P09, providers, wallets,
signers, execution, settlement, persistence, or runtime behavior.

## 2. Executive verdict

**Final verdict: FAIL — implementation closure is not permitted.**

The implementation has useful Safe V1 structure and the existing seven focused
tests pass under an isolated Python 3.14 supplemental environment. However,
the implementation audit does not pass because:

1. unsupported policy evaluator versions are accepted and can produce
   `APPROVED`;
2. required bounded provenance is not validated and incomplete provenance can
   produce `APPROVED`;
3. finite binary floating-point values are accepted inside provenance despite
   the canonical-input prohibition;
4. the focused tests do not cover those specification-critical negative cases,
   duplicate/conflict handling, or the complete output identity contract;
5. the exact required Python 3.13 test and compile commands are blocked by the
   current environment; and
6. governance records conflict: the specification and re-audit say
   implementation is `NOT AUTHORIZED` and require a separate limited
   authorization, while `PROJECT_STATE.md` says the implementation is
   complete/tested. No separate limited implementation authorization record was
   identified in the targeted project search.

The failures are implementation and governance blockers, not permission to
repair the code. `PROJECT_STATE.md` was not changed.

## 3. Criterion-by-criterion findings

### Criterion 1 — Authorization, file scope, and governance state

**Result: FAIL**

**Evidence:**

- The specification states `Implementation status: NOT AUTHORIZED` and requires
  a separate limited implementation authorization naming exact files.
- The specification's implementation gate names the two reviewed paths, but
  does not itself grant authorization.
- The re-audit repeats `Implementation status: NOT AUTHORIZED` and says a
  separate limited authorization is required before code may be created.
- `PROJECT_STATE.md` instead says the Risk/Capital Authority limited
  implementation is complete/tested.
- A targeted search of the project governance documents found no separate
  Risk/Capital Authority implementation-authorization record.

The repository therefore does not provide one consistent, auditable
authorization state for the implementation.

### Criterion 2 — Boundary remains strictly between P06 and P07

**Result: PASS**

**Evidence:**

- The implementation accepts one `DecisionIntent` and one
  `PaperRiskCapitalPolicySnapshot`.
- It evaluates the P06 action, posture, P05 viability, policy scope, and
  paper limits without re-running P05 or P06.
- `PaperRiskCapitalAuthorizationResult.to_authorization_observation()` maps
  approval to P07 `PASS` and rejection to P07 `FAIL`.
- The existing focused approval test verifies the observation status and scope
  linkage.

No implementation path was found that creates a P07 fill, position, ledger
entry, reconciliation result, or later authority.

### Criterion 3 — Exact immutable input and version contract

**Result: FAIL**

**Evidence:**

- The dataclasses are frozen and nested mappings are frozen.
- Policy and nested state digests are calculated and verified.
- `contract_version` is checked for the policy and result.
- The policy `evaluator_version`, however, is only checked as non-empty text.
  It is not required to equal the supported Safe V1 evaluator version.
- The implementation therefore accepts:

  ```text
  evaluator_version = "unsupported"
  ```

  and the behavioral probe produced `APPROVED` for that policy.

This violates the specification requirement that the policy use supported Safe
V1 policy and evaluator versions.

### Criterion 4 — Canonical, bounded, provenance-aware inputs

**Result: FAIL**

**Evidence:**

- The specification requires provenance to contain the references needed to
  reproduce the snapshot, including P05/P06 versions and digests, policy and
  evaluator versions, risk/capital/exposure identities and digests, and any
  supplied observation-packet identity.
- `_mapping()` only checks that provenance is a mapping and that its values can
  be passed through `_canonicalize()`.
- It does not require the specified provenance references.
- `_canonicalize()` accepts finite `float` values.
- The behavioral probe showed both of these invalid cases can approve:

  ```text
  provenance = {"source": "fixture"}
  provenance = {"source": 1.25}
  ```

The first is incomplete provenance. The second violates the canonical
representation rule that binary floating-point values must not be accepted as
canonical material.

### Criterion 5 — Deterministic temporal and freshness behavior

**Result: PASS**

**Evidence:**

- The evaluator uses the explicit `simulation_reference_time` and
  `policy_cutoff_time`; no system clock is read.
- Freshness is calculated from each state's explicit `as_of_time` and the
  corresponding maximum age.
- Equality at the maximum-age boundary is preserved by the strict `>` stale
  comparison.
- Future and stale focused tests pass in the supplemental run.
- The implementation checks state availability against the supplied
  simulation reference time.

This criterion is limited to the implemented positive and negative paths; the
environment-blocked exact Python 3.13 run remains recorded in Section 4.

### Criterion 6 — Approval predicate and paper-only capital/exposure limits

**Result: PASS WITH A BLOCKING COVERAGE GAP**

**Evidence:**

- Approval requires P05 `ELIGIBLE`, P06 `BUY` plus `WAIT`, no uncertainty or
  invalidation, a passing risk state, matching units, and all three paper-limit
  formulas.
- Amounts are `Decimal`/integer values and are not treated as account balances
  or economic capital.
- The approval and risk-block focused tests pass.

The implementation has no explicit status/quality field for paper capital or
paper exposure analogous to the risk state's `UNKNOWN` status. The reason
codes `PAPER_CAPITAL_STATE_UNKNOWN` and `PAPER_EXPOSURE_STATE_UNKNOWN` are
declared but are not produced by the evaluator. Unknown capital/exposure
material therefore cannot be represented as a stable rejected result with the
specified reason; it can only fail during construction if malformed.

### Criterion 7 — Closed reason vocabulary and deterministic precedence

**Result: PASS WITH A BLOCKING COVERAGE GAP**

**Evidence:**

- Reason codes are closed, deduplicated, and ordered through
  `REASON_PRECEDENCE`.
- The focused precedence test verifies future-state, risk-block, and
  unavailable-observation ordering.
- Unsupported reasons are rejected by result construction.

The declared duplicate and replay-conflict reasons are not generated by any
input validation path. The implementation has no explicit conflict material
or duplicate-field validation path that can produce
`DUPLICATE_LIFECYCLE_CONFLICT` or `REPLAY_IDENTITY_CONFLICT`. The current tests
also do not cover those cases.

### Criterion 8 — Result identity, digest, immutability, and P07 handoff

**Result: FAIL**

**Evidence:**

- Normal evaluator results are frozen, carry an authorization identity, and
  produce stable result digests.
- The focused tests verify repeated evaluation identity and that changing the
  lifecycle changes identity.
- The P07 handoff test verifies `PASS`/`FAIL` status mapping and scope identity.

The result constructor does not enforce all cross-field identity invariants:

- `paper_lifecycle_id` is not checked against
  `scope_identity["paper_lifecycle_id"]`;
- result provenance is accepted without the required schema;
- direct result construction can therefore produce an internally inconsistent
  result that still passes its own constructor checks.

The evaluator's normal construction path avoids some of these inconsistencies,
but the public immutable result contract must validate them rather than rely
on callers to use one factory path.

### Criterion 9 — Replay, duplicate, and contradiction semantics

**Result: FAIL**

**Evidence:**

- Stateless repeated evaluation is deterministic.
- A changed lifecycle scope changes the authorization identity.
- There is no registry, cache, database, or external duplicate lookup.

The implementation does not validate or represent the specification's
explicit duplicate/conflict cases. It also does not check every required
cross-field contradiction before evaluation, as shown by the result identity
and provenance gaps above. This is insufficient for the specification's
complete replay/duplicate/contradiction contract.

### Criterion 10 — Prohibition of live, economic, and provider authority

**Result: PASS**

**Evidence:**

- The implementation imports only deterministic standard-library and existing
  P05/P06/P07 contract modules.
- No provider, exchange, chain, wallet, signer, network, persistence, order,
  settlement, accounting, valuation, ROI, cost-basis, or classification
  operation was found.
- The result explicitly reports `is_order is False`.
- The focused test verifies the result is an authorization and not an order.

This pass does not permit any future expansion beyond the documented paper
lifecycle-entry effect.

### Criterion 11 — Tests cover the implementation boundary and negative paths

**Result: FAIL**

**Evidence:**

The seven existing focused tests cover:

- deterministic approval;
- risk denial;
- future and stale state;
- missing, invalid, and tampered policy input;
- one reason-precedence case;
- replay identity;
- basic immutability.

They do not cover:

- unsupported policy evaluator versions;
- required provenance presence and boundedness;
- rejection of floating-point provenance values;
- policy/result cross-field identity contradictions;
- duplicate and replay conflict reasons;
- explicit unknown capital/exposure states;
- all P06 action/posture rejection paths;
- complete result canonical-field and provenance validation.

The behavioral probe demonstrated that the first three omitted negative cases
currently approve.

### Criterion 12 — Required verification commands and static cleanliness

**Result: BLOCKED**

**Exact requested commands:**

```text
uv run pytest -q tests/test_paper_risk_capital_authorization.py
uv run python -m compileall -q core/risk/paper_risk_capital_authorization.py
```

Both commands exited with status 2 because the environment has no Python 3.13
interpreter available to `uv`:

```text
error: No interpreter found for Python 3.13 in search path
```

Supplemental, non-substitutive verification using the available Python 3.14
interpreter and an isolated temporary environment produced:

- focused tests: **7 passed**;
- compile check: **passed**.

Additional checks:

- `git diff --check`: **passed** before this audit document was created.
- No source, test, dependency, workflow, or runtime files were changed by this
  audit.

The supplemental result is useful evidence but cannot convert the exact
Python 3.13 requirement into a pass.

## 4. Required correction before re-audit

The smallest correction set is limited to the already reviewed implementation
and focused test paths, subject to a separate explicit authorization:

1. enforce the supported policy evaluator version;
2. enforce the required bounded provenance schema and reject executable,
   opaque, unbounded, and floating-point material;
3. enforce result cross-field identity invariants;
4. define and test explicit duplicate/conflict validation or document a
   contract correction before implementation changes;
5. add focused negative tests for each corrected requirement; and
6. provide a consistent, explicit implementation-authorization record before
   treating the implementation as authorized.

No correction was made during this audit.

## 5. Authority boundaries confirmed by this audit

- **P05:** owns normalized opportunity context and hard-risk viability.
- **P06:** owns analytical `DecisionIntent`, action, posture, assumptions,
  uncertainty, invalidation, confidence, decision time, and provenance.
- **Risk/Capital Authority Safe V1:** may only decide deterministic admission
  of one identity-linked paper lifecycle after the implementation is
  separately authorized and passes audit.
- **P07:** owns paper input validation, simulation observations, fills,
  positions, exposure, ledger, reconciliation, canonical paper result, and
  local history.
- **G1/G2/G3/G4/P09:** remain separate boundaries and are not granted authority
  by this implementation.

No approval, P07 `PASS`, paper fill, paper position, paper ledger, reconciliation,
or finalized paper result may be interpreted as live permission or economic
truth.

## 6. Change control and conclusion

This audit created exactly one project document:

`docs/P08-RISK-CAPITAL-AUTHORITY-IMPLEMENTATION-AUDIT.md`

`PROJECT_STATE.md` was not updated because the implementation audit contains
failed and blocked criteria. Source code, tests, dependencies, APIs, workflows,
specifications, predecessor contracts, and runtime behavior were not modified.

No commit or push was performed.