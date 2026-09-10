# P08 — Risk/Capital Authority Specification Audit

**Status:** SPECIFICATION NOT CLOSED — CORRECTION REQUIRED  
**Phase:** P08 — Outcome Learning  
**Audit type:** Documentation-only formal specification audit  
**Audit date:** 2026-09-10  
**Implementation status:** NOT AUTHORIZED

## 1. Audit scope and guardrails

This audit reviews:

`docs/P08-RISK-CAPITAL-AUTHORITY-SPECIFICATION.md`

The audit is limited to the proposed paper-only Risk/Capital Authority between
P06 `DecisionIntent` and the P07 paper-simulation lifecycle. It does not
authorize or implement a Risk/Capital Authority, P07 change, provider,
execution, settlement, G1/G2/G3/G4, P09, source code, tests, dependencies,
APIs, runtime behavior, wallets, signers, or persistence.

The audit was performed against:

1. `REPLIT_RULES.md`;
2. `PROJECT_STATE.md`;
3. `docs/P08-RISK-CAPITAL-AUTHORITY-BOUNDARY-DISCOVERY.md`;
4. `docs/P08-RISK-CAPITAL-AUTHORITY-SPECIFICATION-PROPOSAL.md`;
5. `docs/P08-RISK-CAPITAL-AUTHORITY-SPECIFICATION.md`;
6. `docs/P05-T03_SPECIFICATION.md`;
7. `docs/P05-T08_SPECIFICATION.md`;
8. `docs/P06-SPECIFICATION.md`;
9. `docs/P06-T02_SPECIFICATION.md`;
10. `docs/P07-SPECIFICATION.md`;
11. `docs/P07-T01-SPECIFICATION.md`;
12. `docs/P07-T05-SPECIFICATION.md`; and
13. `docs/P08-MEMECOINHUNTER-CORE-PIPELINE-READINESS-AUDIT.md`.

## 2. Executive verdict

**Final verdict: NOT CLOSED / FORMAL AUDIT BLOCKED BY ONE SPECIFICATION
AMBIGUITY.**

The specification is otherwise narrow, paper-only, provider-neutral,
immutable, deterministic, provenance-aware, fail-closed, and correctly placed
between P06 and P07. It defines only `APPROVED` or `REJECTED` paper-lifecycle
admission and keeps implementation unauthorized.

Criterion 7 does not pass because the specification requires rejection of stale
paper risk, capital, and exposure observations and includes
`POLICY_STATE_STALE` in its closed reason vocabulary, but it does not define the
exact freshness rule or identify a canonical field that supplies that rule.
`valid_from` and `valid_until` define the policy snapshot window, but the
specification does not state whether that window also bounds the age of each
nested observation, nor does it define a maximum age or equivalent per-state
freshness relationship. A future implementation could therefore make different
deterministic decisions for the same supplied snapshot while each claiming to
follow the specification.

Because this is a material temporal and fail-closed ambiguity, the
specification must not be marked complete or closed, and `PROJECT_STATE.md`
must remain unchanged.

## 3. Criterion-by-criterion findings

### Criterion 1 — Boundary strictly between P06 `DecisionIntent` and P07 paper simulation

**Result: PASS**

**Evidence:**

- The specification’s governed path is:
  `DecisionIntent` → `PaperRiskCapitalPolicySnapshot` →
  `PaperRiskCapitalAuthorizationResult` → P07 `AuthorizationObservation` →
  one P07 paper-simulation lifecycle.
- Section 2 states that P06 owns analytical decision creation and that P07 owns
  the paper-simulation lifecycle after admission.
- The authority accepts one validated P06 intent and does not create or
  reinterpret the P06 result.
- P07-T01 independently validates and consumes the authorization observation;
  it does not create or evaluate Risk/Capital Authorization.
- The result effect is limited to
  `PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY`.

No authority is placed before P06 analytical decision creation or after P07
paper-lifecycle admission.

### Criterion 2 — Paper-only and provider-neutral

**Result: PASS**

**Evidence:**

- The specification identifies the boundary as paper-lifecycle admission only.
- It explicitly excludes providers, exchanges, venues, chain endpoints, RPC,
  APIs, order books, quotes, liquidity sources, wallets, custody, signers,
  broadcast, settlement, and external accounts.
- `chain_id`, token identity, and source labels are retained only as supplied
  identity or provenance; they do not select or contact a provider.
- The policy amounts are explicitly virtual-paper amounts in one
  simulation-only unit.
- The evaluator is defined as a pure operation over supplied immutable values
  with no network, database, filesystem, cache, queue, or process-global
  dependency.

### Criterion 3 — Explicit, immutable, versioned, canonical,
provenance-aware, and digest-bound inputs

**Result: PASS**

**Evidence:**

- The exact two inputs are one validated immutable P06 `DecisionIntent` and one
  immutable `PaperRiskCapitalPolicySnapshot`.
- The policy snapshot has explicit contract, Risk Governor, capital
  authorization, and evaluator versions.
- It requires exact scope, P06 intent/context digests, a supplied simulation
  reference time, validity bounds, risk state, paper capital state, paper
  exposure state, and bounded provenance.
- Unknown fields are rejected, required fields cannot be silently defaulted,
  and nested state digests plus the top-level policy digest are verified.
- Canonical serialization rules cover sorted mapping keys, explicit fields,
  ordered tuples, UTC timestamps, normalized decimal text, explicit nulls,
  rejected opaque values, and compact sorted-key JSON.
- The result is immutable, versioned, provenance-preserving, and has a digest
  covering its other canonical fields.

The specification also correctly requires exact P06 identity and context
linkage rather than reconstructing an intent from duplicated snapshot fields.

### Criterion 4 — Output is only deterministic `APPROVED` or `REJECTED`
paper-lifecycle admission

**Result: PASS**

**Evidence:**

- The result contract allows only `status = APPROVED | REJECTED`.
- `APPROVED` means only that one exact identity-linked P07 paper lifecycle
  passed admission checks.
- `REJECTED` grants no retry, fallback, reduction, repair, substitution, or
  alternate authority.
- The result cannot authorize a fill, position transition, ledger append,
  reconciliation, finalization, or external action.
- Malformed material can fail deterministic validation, but it can never
  produce `APPROVED`; no third successful or permissive result status is
  defined.

### Criterion 5 — No mutation, sizing, resizing, reduction, repair,
inference, or substitution of P06/P07 inputs

**Result: PASS**

**Evidence:**

- The specification expressly prohibits changing, repairing, resizing,
  reducing, substituting, or regenerating a P06 intent or P07 value.
- It requires the complete P06 object to remain the source of truth.
- The authority does not rerun P05 or P06 and cannot override `NO_TRADE`,
  uncertainty, invalidation, or non-eligible hard risk.
- `requested_entry` is a caller-supplied virtual-paper amount used only by the
  stated limit checks; it is not inferred from confidence, score, expected
  edge, price, quote, or account state.
- The authority does not calculate a request quantity, quote, route, fill, or
  execution instruction.
- P07 remains responsible for validating its own input, observations,
  configuration, state, and replay identity.

### Criterion 6 — Closed reason vocabulary, deterministic precedence, and
fail-closed handling

**Result: PASS**

**Evidence:**

- The specification defines a closed reason vocabulary covering required
  material, contract and identity, P05/P06 admission, temporal/state,
  virtual-paper limits, and replay/duplicate identity.
- Provider, wallet, settlement, accounting, P&L, and classification reasons are
  excluded from Safe V1.
- It defines a fixed nine-group precedence order and a tie-break order inside
  each group.
- Reason codes are validated, deduplicated, and emitted in fixed contract
  order rather than discovery, mapping, timing, or caller order.
- Contract, integrity, contradiction, and scope failures cannot be demoted to
  ordinary limit failures.
- Missing, invalid, stale, future, unsupported, tampered, unavailable,
  contradictory, duplicate-conflicting, and out-of-policy material fails
  closed.

### Criterion 7 — Sufficient identity, serialization, digest, cutoff,
replay, duplicate, and contradiction rules

**Result: FAIL — TEMPORAL FRESHNESS RULE IS AMBIGUOUS**

**Evidence that passes:**

- Exact scope identity covers paper lifecycle, paper portfolio, candidate,
  chain identity, and token identity.
- P06 intent and context digests, candidate identity, chain identity, and token
  identity must agree exactly.
- Canonical serialization, nested digest validation, result identity, and
  result-digest coverage are explicitly defined.
- `simulation_reference_time` is the sole supplied cutoff; the system clock,
  local timezone, filesystem time, ingestion order, network timing, and later
  data are excluded.
- Exact replay is stateless and deterministic for the same canonical intent,
  policy snapshot, lifecycle identity, and reference time.
- Different digests, scope, lifecycle identity, or reference time cannot be
  silently treated as the same replay.
- Contradictory duplicated identities, digests, scopes, timestamps, statuses,
  and fields must be rejected rather than resolved by freshness, insertion
  order, caller preference, or result magnitude.
- P07 handoff fields and `observation_digest` are identified, and
  `NOT_REQUIRED` cannot bypass required paper-entry authorization.

**Blocking deficiency:**

- The specification requires rejecting “stale” risk, capital, and exposure
  observations and includes `POLICY_STATE_STALE`, but it defines no exact
  freshness predicate.
- `risk_state`, `paper_capital_state`, and `paper_exposure_state` contain
  `observed_at` and `available_at`, but no maximum age, freshness duration,
  per-state validity interval, or equivalent rule is specified.
- The global `valid_from` / `valid_until` window is not explicitly stated to
  govern the age of each nested observation. It therefore cannot be assumed to
  resolve the ambiguity.
- The implementation/test scope asks for stale-state rejection without naming
  the input field or formula that determines staleness.

**Smallest required correction:**

Amend the specification before closure to define one canonical freshness rule
for every required nested observation. The correction must identify the
versioned input field or fields carrying the rule, include those fields in the
policy snapshot digest, and state the exact comparison against
`simulation_reference_time` (including boundary inclusivity and the resulting
reason code). The same rule must be used for risk, paper capital, and paper
exposure observations, or each state must have its own explicitly versioned
rule. The focused test plan must name below-boundary, at-boundary, and
stale-boundary cases.

No other identity, serialization, cutoff, replay, duplicate, or contradiction
deficiency was identified in the reviewed text.

### Criterion 8 — Virtual paper budget and exposure treatment

**Result: PASS**

**Evidence:**

- `paper_capital_state` and `paper_exposure_state` are explicitly simulation
  only.
- All amounts use one declared canonical unit and are finite, normalized,
  non-negative decimal values.
- The exact checks are:
  `requested_entry <= max_single_entry`,
  `committed_before + requested_entry <= budget_total`, and
  `exposure_before + requested_entry <= max_total_exposure`.
- Unknown and unavailable values do not become zero.
- The specification expressly denies that these values are account balances,
  cash, custody, settlement, realized cost, realized P&L, or valuation.
- The authority does not derive a price, quote, quantity, conversion, or
  external numeraire.

### Criterion 9 — Prohibition of live, economic, and classification authority

**Result: PASS**

**Evidence:**

The specification explicitly prohibits ownership of or behavior involving:

- wallets, signers, keys, custody, account balances, and capital movement;
- orders, order sides, quantities as execution instructions, quotes, routes,
  fills, transactions, execution, broadcast, and retries;
- settlement and realization;
- realized P&L, accounting, proceeds, cash, cost basis, valuation, ROI,
  numeraire, conversion, precision, and rounding for economic results; and
- `WIN`, `LOSS`, `BREAKEVEN`, or any other performance classification.

It also prohibits provider selection and external data access and does not
produce G1, G2, G3, G4, P08-T07, or P09 results.

### Criterion 10 — Ownership boundaries with P05/P06/P07 and G1/G2/G3/G4/P09

**Result: PASS**

**Evidence:**

- P05 owns normalized opportunity and hard-risk viability; Safe V1 consumes
  the preserved result and rejects every non-eligible state.
- P06 owns analytical action, posture, assumptions, uncertainty, invalidation,
  confidence, and upstream provenance; Safe V1 cannot mutate or regenerate
  those values.
- P07 owns paper input validation, hypothetical fills, paper state, ledger,
  reconciliation, canonical non-economic results, and local history.
- G1 remains a separate simulation-only recognition boundary.
- G2 remains the future realization/settlement authority and is not supplied
  with an eligibility or settlement assertion by Safe V1.
- G3 remains the accounting/economic-result authority.
- G4 remains the performance-classification authority.
- P09 remains a separately governed live-execution chain, and a P07 `PASS`
  observation cannot be reused as P09 permission.

These ownership statements agree with the reviewed P05, P06, and P07
specifications and with the current project state.

### Criterion 11 — Future implementation/test scope only; implementation
unauthorized

**Result: PASS**

**Evidence:**

- The specification explicitly states that it does not authorize
  implementation.
- The proposed implementation and focused test paths are identified as paths
  only and must not be created from the specification.
- The default future scope is limited to:
  `core/risk/paper_risk_capital_authorization.py` and
  `tests/test_paper_risk_capital_authorization.py`.
- Export changes, P07 changes, APIs, workers, databases, persistence, providers,
  wallets, signers, execution, G1–G4, P08-T07, and P09 are excluded unless a
  later authorization names them explicitly.
- The required sequence remains specification approval, formal audit, limited
  implementation authorization, implementation/focused tests, and separate
  implementation audit.

## 4. Remaining blocker and authority boundaries

### Remaining blocker

The specification must define the exact freshness/staleness semantics for
every required nested risk, capital, and exposure observation. Until then:

- the specification is not complete or closed;
- `PROJECT_STATE.md` must continue to state that formal audit is pending;
- no implementation or focused test file may be created; and
- no paper-entry approval may be produced by runtime.

### Authority retained by existing boundaries

- **P05:** normalized opportunity and hard-risk viability.
- **P06:** analytical `DecisionIntent`, action, entry posture, assumptions,
  uncertainty, invalidation, confidence, and upstream provenance.
- **Risk/Capital Safe V1:** only the future, separately authorized,
  paper-lifecycle admission decision described here; no implementation is
  authorized by this audit.
- **P07:** paper input validation, hypothetical simulation consequences,
  positions/exposure, paper ledger, reconciliation, non-economic paper result,
  and local result history.
- **G1:** separately governed simulation-only recognition/finality.
- **G2:** future realization and settlement eligibility; currently blocked and
  unauthorized.
- **G3:** future accounting and canonical economic-result calculation.
- **G4:** future performance classification.
- **P09:** separately governed live-execution chain; not authorized.

No authority may be inferred from the proposed result, a P07 `PASS`
observation, a paper fill, a paper position, a paper ledger, reconciliation, or
P07 finalization beyond the explicitly limited paper-lifecycle admission.

## 5. Change control and conclusion

This audit created exactly one project file:

`docs/P08-RISK-CAPITAL-AUTHORITY-SPECIFICATION-AUDIT.md`

`PROJECT_STATE.md` was not modified because not every criterion passed.

No source code, tests, dependencies, APIs, runtime behavior, `.replit`,
providers, wallets, signers, execution, settlement, G1, G2, G3, G4, P08-T07,
P09, or existing specification was modified. No commit or push was performed.

The smallest next governance action is to amend the Risk/Capital Authority
specification with the exact nested-observation freshness rule described under
Criterion 7, then perform a focused re-audit of Criterion 7 and the dependent
fail-closed and reason-precedence statements. Closure and any later limited
implementation authorization remain separate decisions.