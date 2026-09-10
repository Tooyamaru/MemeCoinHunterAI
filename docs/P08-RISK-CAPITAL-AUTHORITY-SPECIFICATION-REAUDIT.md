# P08 — Risk/Capital Authority Specification Re-Audit

**Status:** SPECIFICATION COMPLETE / CLOSED / AUDITED PASS  
**Phase:** P08 — Outcome Learning  
**Audit type:** Documentation-only formal re-audit  
**Audit date:** 2026-09-10  
**Implementation status:** NOT AUTHORIZED

## 1. Re-audit scope and guardrails

This re-audit reviews:

`docs/P08-RISK-CAPITAL-AUTHORITY-SPECIFICATION.md`

It re-audits all 11 criteria from the original formal audit after the
policy-freshness correction. The review remains limited to the proposed
paper-only Risk/Capital Authority between P06 `DecisionIntent` and the P07
paper-simulation lifecycle.

This re-audit does not authorize or implement a Risk/Capital Authority, P07
change, provider, execution, settlement, G1/G2/G3/G4, P09, source code, tests,
dependencies, APIs, runtime behavior, wallets, signers, or persistence. It does
not modify the original audit or any predecessor contract.

The review was performed against:

1. `REPLIT_RULES.md`;
2. `PROJECT_STATE.md`;
3. `docs/P08-RISK-CAPITAL-AUTHORITY-SPECIFICATION.md`;
4. `docs/P08-RISK-CAPITAL-AUTHORITY-SPECIFICATION-AUDIT.md`;
5. `docs/P08-RISK-CAPITAL-AUTHORITY-BOUNDARY-DISCOVERY.md`;
6. `docs/P08-RISK-CAPITAL-AUTHORITY-SPECIFICATION-PROPOSAL.md`;
7. `docs/P05-T03_SPECIFICATION.md`;
8. `docs/P05-T08_SPECIFICATION.md`;
9. `docs/P06-SPECIFICATION.md`;
10. `docs/P06-T02_SPECIFICATION.md`;
11. `docs/P07-SPECIFICATION.md`;
12. `docs/P07-T01-SPECIFICATION.md`;
13. `docs/P07-T05-SPECIFICATION.md`; and
14. `docs/P07-T06-SPECIFICATION.md`.

## 2. Executive verdict

**Final verdict: PASS — all 11 criteria pass.**

The specification is narrow, paper-only, provider-neutral, immutable,
deterministic, provenance-aware, and fail-closed. It remains strictly between
the analytical P06 `DecisionIntent` and the identity-linked P07
paper-simulation lifecycle. It defines only `APPROVED` or `REJECTED`
paper-lifecycle admission and keeps implementation unauthorized.

The previous audit blocker is resolved. The specification now defines a
canonical, immutable freshness rule for each required risk, paper-capital, and
paper-exposure snapshot, including the supplied cutoff, positive maximum ages,
UTC observation fields, exact age calculation, boundary behavior, stale/future
reason mappings, precedence, and prohibition of ambient time.

## 3. Criterion-by-criterion findings

### Criterion 1 — Boundary strictly between P06 `DecisionIntent` and P07 paper simulation

**Result: PASS**

**Evidence:**

- Section 1 defines the governed path as validated P06 `DecisionIntent` plus
  one immutable policy snapshot, followed by a deterministic authorization
  result and P07 `AuthorizationObservation`.
- Sections 2.2 and 2.3 preserve P06 analytical ownership and P07
  paper-simulation ownership.
- Sections 3.1 and 3.2 limit the authority to two supplied inputs and the
  fixed `PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY` effect.
- Section 7 defines the handoff as value-preserving and not a second
  authorization.

No authority is placed before P06 analytical decision creation or after P07
paper-lifecycle admission.

### Criterion 2 — Paper-only and provider-neutral

**Result: PASS**

**Evidence:**

- Sections 1 and 2 explicitly exclude providers, exchanges, venues, chain
  endpoints, wallets, signers, broadcast, settlement, and live trading.
- Section 3.1 prohibits ambient configuration, current time, account state,
  provider state, database state, cache state, filesystem state, and other
  external inputs.
- Sections 4.3–4.5 define risk, capital, and exposure as supplied paper-only
  state; capital and exposure use a simulation-only unit.
- Section 4.7 restricts provenance to bounded descriptive references and
  prohibits fetch or refresh behavior.

The authority evaluates supplied immutable values and does not select or
contact any provider.

### Criterion 3 — Explicit, immutable, versioned, canonical,
provenance-aware, and digest-bound inputs

**Result: PASS**

**Evidence:**

- Sections 3.1 and 4.1 require exactly one validated P06 intent and one
  immutable `PaperRiskCapitalPolicySnapshot`.
- Section 4.1 lists the exact top-level fields, including contract,
  Risk Governor, capital-authorization, evaluator, scope, linkage, temporal,
  freshness, state, and provenance fields.
- Sections 4.2–4.7 define exact scope, paper-only state, freshness, and bounded
  provenance contracts.
- Sections 10.1–10.4 define canonical serialization, nested digest
  verification, top-level digest coverage, result identity, and immutable
  ordering.

Unknown fields, missing required material, invalid nested values, and digest
failures cannot be silently defaulted or repaired.

### Criterion 4 — Output is only deterministic `APPROVED` or `REJECTED`
paper-lifecycle admission

**Result: PASS**

**Evidence:**

- Section 3.2 permits only `status = APPROVED | REJECTED`.
- Section 3.3 admits only the explicitly defined `BUY` plus `WAIT` paper
  scenario.
- Sections 5.3 and 6 define approval as identity-linked admission of exactly
  one P07 paper lifecycle.
- Section 6 rejects any interpretation as a fill, position transition, ledger
  append, reconciliation, finalized result, order, or external action.
- Section 6 states that rejection grants no retry, fallback, reduction, repair,
  substitution, or alternate authority.

No third successful status or permissive fallback is defined.

### Criterion 5 — No mutation, sizing, resizing, reduction, repair,
inference, or substitution of P06/P07 inputs

**Result: PASS**

**Evidence:**

- Sections 1, 2.2, and 5.1 require the complete supplied P06 object and prohibit
  mutation, reconstruction, re-evaluation, or replacement.
- Section 5.1 preserves P05 hard-risk eligibility and rejects P06 uncertainty,
  invalidation, and non-eligible upstream states.
- Sections 4.4 and 4.5 use only explicit virtual-paper amounts and exact limit
  formulas; no amount is inferred from confidence, price, quote, or account
  state.
- Section 7 states that P07 independently validates its own inputs and remains
  responsible for simulation consequences.

The authority does not create an order, request quantity, quote, route, fill,
or execution instruction.

### Criterion 6 — Closed reason vocabulary, deterministic precedence, and
fail-closed handling

**Result: PASS**

**Evidence:**

- Section 8 defines the closed vocabulary for required material, identity,
  P05/P06 admission, temporal/state, paper limits, and replay conflicts.
- Section 8 excludes provider-specific, wallet-specific, settlement-specific,
  accounting-specific, P&L-specific, and classification-specific reasons.
- Section 9 defines nine fixed precedence groups and a fixed order within each
  group.
- Section 9 requires validation before deduplication and fixed ordering rather
  than discovery, mapping, timing, or caller order.
- Sections 5 and 8 require missing, malformed, stale, future, unsupported,
  tampered, unavailable, contradictory, and out-of-policy material to fail
  closed.

Invalid material cannot be demoted to an ordinary paper-limit rejection.

### Criterion 7 — Sufficient identity, serialization, digest, cutoff,
replay, duplicate, and contradiction rules

**Result: PASS**

**Evidence:**

- Sections 4.1–4.2 define exact policy identity, lifecycle scope, P06 linkage,
  and candidate/chain/token/portfolio identity.
- Sections 4.3–4.5 define complete risk, capital, and exposure snapshots.
- Section 4.6 resolves the prior ambiguity with the following closed rule:
  - `policy_cutoff_time` is the sole explicit, immutable, timezone-aware UTC
    freshness cutoff;
  - each required state has a positive canonical maximum age;
  - each required state has its own timezone-aware UTC `as_of_time`;
  - `age = policy_cutoff_time - snapshot.as_of_time`;
  - `snapshot.as_of_time > policy_cutoff_time` and negative age map to
    `POLICY_STATE_FUTURE_DATED`;
  - `age > matching maximum age` maps to `POLICY_STATE_STALE`; and
  - equality at the maximum-age boundary is accepted.
- Section 4.6 rejects missing, invalid, non-UTC, or unsupported temporal and
  maximum-age material using the applicable closed validation reason.
- Section 4.6 preserves `simulation_reference_time` as the separate P07
  paper-simulation cutoff and retains the availability-by-reference-time rule.
- Sections 8.3 and 9 place the exact stale/future codes in the existing group 6
  precedence order.
- Sections 10–12 define canonical digests, replay identity, duplicate
  conflicts, contradiction handling, and no ambient state.

The previous audit blocker is therefore resolved without changing the P06 or
P07 contracts. The same explicit freshness structure applies to all three
required nested policy states.

### Criterion 8 — Virtual paper budget and exposure treatment

**Result: PASS**

**Evidence:**

- Sections 4.4 and 4.5 define capital and exposure as virtual-paper state only.
- Amounts are finite, normalized, non-negative decimal values in one
  simulation-only unit.
- Section 5.3 requires the exact entry, budget, and exposure formulas.
- Unknown, unavailable, negative, contradictory, non-canonical, and
  digest-invalid values fail closed.
- Sections 4.4, 4.5, and 6 deny account-balance, wallet, custody, settlement,
  valuation, and economic meaning.

No price, quote, conversion, execution quantity, or live balance is derived.

### Criterion 9 — Prohibition of live, economic, and classification authority

**Result: PASS**

**Evidence:**

- Sections 1, 3.2, 4.4, 4.5, 6, and 7 prohibit live execution, providers,
  wallets, signers, broadcast, settlement, accounting, valuation, and
  classification authority.
- Section 3.2 excludes fills, positions, ledgers, reconciliation,
  finalization, orders, routes, and transactions from the result effect.
- Section 6 expressly excludes realized P&L, cost basis, proceeds, cash,
  valuation, ROI, numeraire, and `WIN`/`LOSS`/`BREAKEVEN`.
- Section 7 preserves P07, G1, G2, G3, G4, P08-T07, and P09 as separate
  boundaries.

Approval cannot be inferred as economic truth or live permission.

### Criterion 10 — Ownership boundaries with P05/P06/P07 and G1/G2/G3/G4/P09

**Result: PASS**

**Evidence:**

- Section 2.1 agrees with P05-T03 and P05-T08: P05 owns normalized opportunity
  context and hard-risk viability; the authority consumes the preserved result.
- Section 2.2 agrees with P06 and P06-T02: P06 owns analytical action,
  posture, assumptions, uncertainty, invalidation, confidence, and provenance;
  `BUY + WAIT` remains non-authorizing.
- Sections 2.3 and 7 agree with P07, P07-T01, P07-T05, and P07-T06: P07
  consumes authorization, owns paper simulation and reconciliation, and does
  not create or upgrade Risk/Capital Authorization.
- Section 7 preserves G1 as a separate simulation-recognition boundary and
  G2/G3/G4 as future realization, accounting, and classification boundaries.
- Section 7 preserves P09 as the separately governed live-execution chain.

No ownership is transferred across the existing boundaries.

### Criterion 11 — Future implementation/test scope only; implementation
unauthorized

**Result: PASS**

**Evidence:**

- Sections 1 and 2 state that the specification does not authorize
  implementation.
- Section 1 preserves the sequence from specification audit to separate,
  limited implementation authorization and later implementation audit.
- Section 13 limits any future implementation scope to the named authority
  module and focused test module, subject to separate authorization.
- Section 13 excludes exports, P07 changes, APIs, workers, databases,
  persistence, providers, wallets, signers, execution, G1–G4, P08-T07, and
  P09 unless a later authorization names them.
- The reviewed P07 contracts continue to require independently supplied,
  immutable authorization and do not authorize implementation through this
  specification.

The specification audit passes without creating code or tests.

## 4. Previous blocker resolution

The original audit identified one blocker under Criterion 7: the specification
required stale-state rejection and listed `POLICY_STATE_STALE`, but did not
define the canonical freshness input or exact comparison.

The corrected specification resolves that blocker by:

1. adding immutable `policy_cutoff_time` as the sole policy-freshness cutoff;
2. adding positive canonical maximum ages for risk, paper capital, and paper
   exposure;
3. replacing the ambiguous nested `observed_at` fields with required
   `as_of_time` fields;
4. defining `age = policy_cutoff_time - snapshot.as_of_time`;
5. defining future and negative-age rejection as
   `POLICY_STATE_FUTURE_DATED`;
6. defining over-age rejection as `POLICY_STATE_STALE`;
7. accepting the exact maximum-age boundary through strict `age > maximum_age`
   staleness; and
8. retaining both codes in the established group 6 precedence order while
   keeping `simulation_reference_time` as the P07 lifecycle cutoff.

This is sufficient to produce the same result, reason codes, canonical
representation, and digest for the same supplied inputs without ambient time.

## 5. Remaining blockers

No specification criterion remains blocked or failed.

The following remain intentionally outside this re-audit and unauthorized:

- Risk/Capital Authority source implementation and focused tests;
- any P07 contract or runtime change;
- providers, wallets, signers, execution, broadcast, or settlement;
- G1, G2, G3, G4, P08-T07, and P09 implementation or authority; and
- any production or live-trading behavior.

These are governance boundaries, not defects in the audited specification.
A separate limited implementation authorization naming exact files is required
before code may be created.

## 6. Authority boundaries

- **P05:** owns normalized opportunity context and hard-risk viability.
- **P06:** owns analytical `DecisionIntent`, action, entry posture, assumptions,
  uncertainty, invalidation, confidence, decision time, and upstream
  provenance.
- **Risk/Capital Authority Safe V1:** may only make the separately authorized
  deterministic paper-lifecycle admission decision for one identity-linked P07
  lifecycle.
- **P07:** owns paper input validation, hypothetical execution observations,
  fills, paper positions and exposure, paper ledger, reconciliation, the
  canonical non-economic paper result, and local history.
- **G1:** remains the separate simulation-only recognition boundary.
- **G2:** owns future realization and settlement eligibility.
- **G3:** owns future accounting and canonical economic-result calculation.
- **G4:** owns future performance classification.
- **P09:** remains the separately governed live-execution chain and cannot use a
  P07 authorization observation as live permission.

No authority may be inferred from a Risk/Capital approval, P07 `PASS`
observation, paper fill, paper position, paper ledger, reconciliation, or
finalized paper result beyond the explicitly limited paper-lifecycle admission.

## 7. Change control and conclusion

This re-audit created exactly one new project document:

`docs/P08-RISK-CAPITAL-AUTHORITY-SPECIFICATION-REAUDIT.md`

Because all 11 criteria pass, `PROJECT_STATE.md` was updated only with the
required Risk/Capital Authority closure statement. The original audit,
specification, predecessor contracts, source code, tests, dependencies, APIs,
runtime behavior, `.replit`, providers, wallets, signers, execution,
settlement, G1, G2, G3, G4, P08-T07, and P09 were not modified.

No commit or push was performed.