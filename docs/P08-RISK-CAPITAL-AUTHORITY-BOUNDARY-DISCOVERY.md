# P08 — Risk/Capital Authority Boundary Discovery

**Status:** COMPLETE / AWAITING EXPLICIT GOVERNANCE DECISIONS  
**Document type:** Documentation-only discovery  
**Boundary:** P06 `DecisionIntent` → paper-only Risk/Capital Authority →
P07 paper-simulation lifecycle  
**Provider posture:** Provider-neutral and simulation-only  
**Implementation status:** NOT AUTHORIZED

## 1. Purpose and current governance position

This document discovers the smallest missing boundary between the completed
P06 analytical decision contract and the completed P07 paper-simulation
contracts. It proposes a deterministic, immutable authority that evaluates a
paper-only risk/capital policy snapshot and emits a bounded result that P07
can consume as an authorization observation.

This is not a live-trading authority, an execution request, a portfolio
manager, or an economic-result authority. It does not select or integrate a
provider, exchange, venue, network, wallet, signer, broadcast path,
settlement endpoint, or live-trading capability.

The current repository position is:

```text
P05                 = deterministic opportunity and hard-risk context
P06 DecisionIntent  = immutable analytical decision; not authorization
Risk/Capital        = missing independent authorization producer
P07                 = provider-neutral paper simulation only
G1–G4               = separately governed future outcome/economic boundaries
P09                 = separately governed live execution chain; NOT AUTHORIZED
```

The proposed boundary is:

```text
validated P06 DecisionIntent
        +
explicit paper-only Risk/Capital Policy Snapshot
        +
explicit paper-simulation reference time
        ↓
deterministic Paper Risk/Capital Authorization Result
        ↓
P07-T01 AuthorizationObservation
        ↓
P07 PaperSimulationInput and paper lifecycle
```

The discovery authorizes no implementation and does not modify P06, P07, G1,
G2, G3, G4, P09, source code, tests, dependencies, APIs, or runtime behavior.

## 2. Repository-grounded inputs already available

The boundary should consume existing immutable contracts by identity and
digest. It should not reconstruct them from partial fields.

### 2.1 P06 `DecisionIntent`

The exact P06 `DecisionIntent` is the primary upstream input. The current
contract provides:

- the complete validated P05 `OpportunityContext`;
- candidate, chain, and token identity;
- P05 hard-risk evaluation, flags, rejection reason, and evidence references;
- P05 feature, signal, opportunity-record, and history provenance;
- P06 analytical action;
- separate P06 entry posture;
- expected-edge assumptions, uncertainty, and invalidation conditions;
- bounded analytical confidence, explicitly not profit probability;
- context, contract, ruleset, evaluator, and decision-time provenance;
- canonical representation and deterministic digest; and
- immutable/frozen semantics.

The Risk/Capital Authority must preserve the supplied intent and context
digests. It must not re-evaluate P05 evidence, recalculate the P06 score,
change the action or posture, add a ranking, or turn analytical confidence
into a probability, capital amount, or execution instruction.

The intent remains analytical even when its action is `BUY`. Existing tests
explicitly verify that it is not authorization, not an order, and not an
execution request.

### 2.2 Existing P07 paper-state and simulation identities

P07 already defines immutable identities that can be linked by the future
authority and then carried into `PaperSimulationInput`:

- `InitialPaperStateIdentity`, including portfolio scope, position-state
  digest, exposure-state digest, as-of time, quality, and provenance;
- `PaperSimulationInput` and its explicit simulation reference time;
- `ReplayIdentity`;
- `SimulationConfigurationIdentity`;
- the provider-neutral `ExecutionObservation`; and
- the P07 `AuthorizationObservation` envelope.

These are supplied paper-simulation inputs, not account balances or live
state. A paper-state digest does not prove a wallet or external account
position. The future authority may validate the linkage and quality of a
paper-state observation, but must not fetch or refresh it.

### 2.3 Existing authorization observation handoff

P07-T01 already reserves the following independent observation:

```text
AuthorizationObservation
    observation_id
    observation_digest
    status = PASS | FAIL | UNKNOWN | NOT_REQUIRED
    scope_identity
    observed_at
    valid_from
    valid_until
    contract_version
    risk_governor_version
    capital_authorization_version
    reason_codes
    unknown_reasons
```

P07-T01 does not create or evaluate this observation. It requires a `PASS`
observation to be valid for the complete simulation scope and reference time
when authorization is required. `FAIL` and `UNKNOWN` are preserved and fail
closed. `NOT_REQUIRED` is not a bypass for a scenario that requires
authorization.

The proposed authority is therefore a producer of an approved, paper-only
authorization result that can be materialized into this existing P07
observation shape. It is not a replacement for P07-T01 and does not alter the
current P07 contract.

## 3. Required paper-only Risk/Capital Policy Snapshot

The authority must never read ambient risk configuration, process-global
limits, a current account balance, or an external portfolio. All policy and
state inputs must be supplied as one immutable, canonical snapshot.

The smallest future snapshot should contain these groups:

### 3.1 Policy identity and versioning

- `policy_snapshot_id`;
- `policy_snapshot_digest`;
- `contract_version`;
- `risk_governor_version`;
- `capital_authorization_version`;
- `evaluator_version`;
- explicit policy provenance; and
- a bounded, canonical policy scope.

The versions identify deterministic paper policy behavior. They do not select
a provider or authorize any behavior outside this boundary.

### 3.2 Scope and P06 linkage

The snapshot must identify the exact paper scope to which its limits apply:

- candidate or lifecycle identity;
- portfolio/simulation scope identity;
- P06 `DecisionIntent` digest;
- P06 context digest;
- asset identity as preserved by the P06/P07 chain; and
- the supplied paper-simulation reference time or an equivalent explicit
  as-of boundary.

Scope mismatch must reject the request. A policy for one candidate,
portfolio, replay, or time window must not be reused for another.

### 3.3 Paper-only budget and exposure observations

The snapshot must provide explicit virtual-paper observations, not live
financial state:

- paper budget amount and canonical unit;
- maximum paper entry amount for this scope;
- current paper committed amount, if applicable;
- current paper exposure amount, if applicable;
- target paper exposure amount or a bounded exposure identity;
- any approved single-lifecycle or single-asset limit; and
- quality, observation time, availability time, provenance, and digest for
  each supplied observation.

These values describe a simulation budget and paper state. They are not
account balances, cash availability, custody, settlement, realized cost, or
realized P&L. Unknown or unavailable values must remain unknown or unavailable
and must not become zero.

The authority should not derive a requested order quantity, quote, route,
fill, fee, or price. If a later paper-simulation contract needs a requested
quantity or a notional cap, the cap must be carried by explicit policy
identity and validated by that later contract. It must not be inferred from a
P06 confidence value or from a live-looking account concept.

### 3.4 Paper risk observations and limits

The snapshot may contain only explicit, bounded, paper-scope risk inputs
needed for the Safe V1 decision:

- the required P05 hard-risk result identity and digest;
- whether uncertainty or invalidation is present in the P06 intent;
- approved maximum paper exposure or budget thresholds;
- approved single-candidate or single-lifecycle limits; and
- explicit policy flags that are already materialized in the snapshot.

It must not contain an unbounded risk engine, an implicit risk model, a
provider response, a wallet state, or an account-level authority. Correlation,
theme, ecosystem, portfolio-wide optimization, and candidate comparison
should remain out of the smallest V1 unless separately specified with
immutable input contracts.

### 3.5 Temporal validity

The snapshot must carry explicit:

- `observed_at`;
- `valid_from`;
- `valid_until` or explicit non-expiry semantics; and
- the simulation reference time against which validity is checked.

The evaluator must use supplied timestamps only. It must reject a future
snapshot, a stale snapshot, an expired approval window, or an observation
whose availability is after the supplied simulation reference time. It must
not call the system clock to decide whether a policy is current.

## 4. Proposed deterministic result

The future result should be a frozen, canonical record tentatively named
`PaperRiskCapitalAuthorization`.

### 4.1 Result fields

The smallest useful result contains:

| Field | Meaning |
|---|---|
| `status` | `APPROVED` or `REJECTED`; only `APPROVED` maps to P07 `PASS`. |
| `decision_intent_digest` | Exact P06 intent digest consumed. |
| `context_digest` | Exact P06 context digest consumed. |
| `candidate_id` | Exact candidate identity from the intent. |
| `scope_identity` | Exact bounded paper scope covered by the result. |
| `policy_snapshot_id` | Supplied policy snapshot identity. |
| `policy_snapshot_digest` | Digest of the complete policy snapshot. |
| `simulation_reference_time` | Explicit as-of time for this authorization. |
| `valid_from` / `valid_until` | Supplied validity window for the paper entry. |
| `reason_codes` | Sorted, deduplicated, bounded explanation vocabulary. |
| `authorization_effect` | Fixed value `PAPER_SIMULATION_ENTRY_ONLY`. |
| `contract_version` | Version of this future result contract. |
| `evaluator_version` | Version of the deterministic evaluator. |
| `provenance` | Bounded references to all consumed immutable inputs. |
| `result_digest` | Digest of all other canonical fields. |

The result must not contain an order, order side/quantity instruction, quote,
route, provider, wallet, account balance, signer, transaction, settlement
identity, realized value, P&L, accounting result, classification, or live
execution field.

`APPROVED` means only that the supplied P06 intent and supplied paper-only
policy snapshot passed the deterministic admission checks for one paper
simulation scope. It does not mean that P07 will fill, mutate state, append a
ledger entry, reconcile, or produce a successful paper result.

### 4.2 Approval conditions

An `APPROVED` result is permitted only when all of the following are true:

1. The `DecisionIntent` is the supported immutable P06 contract and its
   canonical representation and digest verify.
2. The policy snapshot is the supported immutable policy contract and its
   canonical representation and digest verify.
3. P06 identity, scope, candidate, token, context, and reference-time links
   agree exactly.
4. The P05 hard-risk result is `ELIGIBLE`.
5. The P06 action and entry posture are allowed by the explicit paper-entry
   policy. `NO_TRADE`, uncertainty, and invalidation cannot pass.
6. The paper-state and exposure observations required by the policy are
   present, canonical, available by the reference time, and within their
   approved validity rules.
7. The virtual paper budget and paper exposure checks pass without using a
   live balance or inferred value.
8. The scope is not already blocked by an explicit policy reason.
9. All required versions, provenance references, and digests agree.
10. The result can be reproduced from the supplied inputs without a clock,
    randomness, provider, database, or process-global state.

No condition may be satisfied by dereferencing an identity, fetching newer
data, preferring a conflicting source, or silently substituting a default.

### 4.3 Rejection semantics

For well-formed inputs that do not satisfy policy, the result must be
`REJECTED` with one or more stable reason codes. Contract violations must
also fail closed: a future implementation may reject construction with a
deterministic validation error, but it must never construct `APPROVED` from
invalid material.

The proposed Safe V1 reason vocabulary is:

**Contract and linkage**

- `INVALID_INPUT`
- `UNSUPPORTED_VERSION`
- `NON_CANONICAL_INPUT`
- `DIGEST_MISMATCH`
- `PROVENANCE_LINKAGE_FAILURE`
- `CONTRADICTORY_INPUT`
- `POLICY_SCOPE_MISMATCH`

**P06 and P05 gate**

- `P06_NO_TRADE`
- `P06_UNCERTAIN_OR_INVALIDATED`
- `DECISION_ACTION_NOT_PAPER_ENTRY`
- `ENTRY_POSTURE_NOT_PERMITTED`
- `P05_HARD_RISK_NOT_ELIGIBLE`
- `P05_HARD_RISK_UNKNOWN`

**Policy and temporal state**

- `POLICY_SNAPSHOT_MISSING`
- `POLICY_SNAPSHOT_UNKNOWN`
- `POLICY_SNAPSHOT_STALE`
- `POLICY_SNAPSHOT_FUTURE_DATED`
- `PAPER_STATE_MISSING`
- `PAPER_STATE_UNKNOWN`
- `PAPER_EXPOSURE_UNKNOWN`
- `PAPER_BUDGET_UNKNOWN`
- `PAPER_OBSERVATION_UNAVAILABLE`

**Limit results**

- `PAPER_BUDGET_EXCEEDED`
- `PAPER_ENTRY_LIMIT_EXCEEDED`
- `PAPER_EXPOSURE_LIMIT_EXCEEDED`
- `PAPER_RISK_LIMIT_EXCEEDED`

Reason codes must be canonical text, sorted and deduplicated. The future
specification must define precedence when multiple categories apply. At
minimum, malformed, tampered, unsupported, or contradictory input must not be
reported as an ordinary limit rejection, and no rejection reason may be
treated as permission to retry or bypass the boundary.

## 5. Clock, data, and side-effect prohibitions

The evaluator must be a pure operation over explicit immutable inputs.

It must not depend on:

- an ambient or wall clock;
- local timezone or process time;
- random values or uncontrolled seeds;
- provider, exchange, venue, network, RPC, API, or chain data;
- account balance, bank balance, custody state, or wallet state;
- private keys, seed phrases, signer state, signing, or broadcast;
- live order books, quotes, routes, fills, or execution acknowledgements;
- database, filesystem, cache, queue, workflow, or process-global state; or
- a hidden risk configuration or caller-specific mutable default.

`chain_id`, asset identity, and source labels already present in P06/P07
contracts may be preserved as identity/provenance. They do not select or
integrate a chain, provider, venue, wallet, or execution system.

The result must be immutable and deterministically canonicalized. The same
intent, policy snapshot, paper-state observations, and explicit reference time
must produce the same status, reason codes, canonical representation, and
digest.

## 6. Authority effect and explicit non-authority

### 6.1 What this boundary may authorize

The only permitted authority effect is:

```text
PAPER_SIMULATION_ENTRY_ONLY
```

In practice, an approved result may be represented as a P07
`AuthorizationObservation` with `status = PASS`, allowing a complete,
identity-linked P07-T01 input to enter a paper-simulation lifecycle.

It may not authorize a fill, position transition, ledger append,
reconciliation, result finalization, retry, cancellation, or any other
downstream state transition. P07 remains responsible for validating its own
input, observations, configuration, initial state, and replay identity.

### 6.2 What this boundary must never authorize

This boundary must never authorize or imply:

- a real order or live execution;
- an execution request, route, quote, or transaction;
- a provider, exchange, venue, network, chain endpoint, or external source;
- a wallet, account, custody, signer, key, signing, or broadcast action;
- capital movement, account-balance use, or settlement;
- external execution truth or on-chain state;
- realized P&L, economic accounting, cost basis, proceeds, or cash state;
- valuation as settlement;
- `WIN`, `LOSS`, `BREAKEVEN`, or any classification;
- strategy promotion, learning, model updates, ranking, or optimization;
- a G1, G2, G3, G4, P08-T07, or P09 result; or
- an override of a P06 `NO_TRADE` or an existing fail-closed state.

An approved paper authorization is not economic truth. A later paper fill,
paper ledger record, reconciliation result, or P07-T06 finalization cannot
upgrade it into any of these prohibited authorities.

## 7. Ownership boundaries

### 7.1 P06 `DecisionIntent`

P06 owns analytical decision creation, action, entry posture, uncertainty,
invalidation, assumptions, confidence, and upstream provenance. The
Risk/Capital Authority consumes the intent and may reject it under policy. It
must not modify, reinterpret, or regenerate the intent.

P06 does not own capital limits or paper admission.

### 7.2 P07 paper simulation

P07 owns paper-simulation input validation, hypothetical fill outcomes,
paper-position and exposure transitions, logical paper ledger records,
reconciliation, the canonical non-economic paper result, and local history.

P07 consumes the authorization observation; it does not create, renew,
upgrade, or override it. P07 paper status is not economic truth and cannot
authorize live behavior.

### 7.3 G1

G1 must remain a separate, governed recognition boundary. It may recognize a
complete paper lifecycle under its own approved simulation-only semantics, but
it does not create Risk/Capital Authorization and cannot turn paper admission
or a paper result into external execution, settlement, or realized economics.

The existing G1 discovery still records unresolved owner decisions about the
concrete economic authority. This document does not resolve those decisions or
make the Risk/Capital Authority a G1 substitute.

### 7.4 G2

G2 owns future realization eligibility and the governed endpoint distinction
between execution, settlement, and realization. It must not infer realization
from a paper authorization, paper fill, paper ledger, or P07 finalization.

This authority supplies no G2 input other than preserved provenance if a
future contract explicitly permits that reference. It does not establish a
settlement endpoint.

### 7.5 G3

G3 owns future accounting and canonical economic-result calculation, including
economic quantities, costs, fees, basis, numeraire, conversion, precision,
rounding, and realized P&L. The Risk/Capital Authority must not calculate any
of these. A virtual paper budget or paper exposure check is not G3
accounting.

### 7.6 G4

G4 owns future performance classification and its approved vocabulary. The
Risk/Capital Authority must not emit, infer, or prepare `WIN`, `LOSS`,
`BREAKEVEN`, or another economic classification.

### 7.7 P09

P09 remains the separately governed live execution chain:

```text
DecisionIntent
    → live Risk/Capital Authorization
    → Execution Request
    → isolated signing
    → broadcast
    → reconciliation
    → journal
```

The paper-only authority is not the P09 risk gate, cannot activate P09, and
cannot be reused as live authorization. A `PASS` observation for P07 must not
be accepted as permission for any P09 step.

## 8. Smallest future specification and implementation/test scope

This discovery should lead to one separately approved future specification,
not a broad risk-engine refactor.

### 8.1 Future specification

The smallest specification should lock:

1. the exact immutable policy-snapshot fields and canonical digest;
2. the supported P06 action/posture admission rule;
3. the paper budget and paper-exposure units and limit formulas;
4. the explicit reference-time and validity-window rules;
5. the status, reason-code, and precedence vocabulary;
6. the exact mapping to P07 `AuthorizationObservation`;
7. the `PAPER_SIMULATION_ENTRY_ONLY` authority effect; and
8. the complete forbidden-ownership list.

The specification must explicitly state that it does not change the existing
P06 or P07 contracts. If carrying a paper limit into P07 requires a field
change rather than an existing bounded identity/provenance field, that is a
separate P07 contract decision and must not be smuggled into this authority.

### 8.2 Future implementation boundary

After specification and audit approval, the smallest implementation could be
limited to:

```text
core/risk/paper_risk_capital_authorization.py
tests/test_paper_risk_capital_authorization.py
```

An export change should be included only if explicitly authorized. No
database, persistence, workflow, provider adapter, network client, wallet,
signer, live execution module, G1–G4 module, P08-T07 module, or P09 file is
part of this scope.

The implementation should be a pure local evaluator and immutable result
contract. It should not add a new service, API, background worker, or
configuration loader.

### 8.3 Future focused tests

The focused suite should cover at least:

1. valid approval for an exact P06 intent and exact paper policy scope;
2. P06 `NO_TRADE`, uncertainty, invalidation, and non-entry action rejection;
3. P05 hard-risk rejection and preservation of the upstream digest;
4. policy-scope, candidate, context, and asset identity mismatches;
5. missing, unknown, stale, future, unavailable, contradictory, tampered, and
   unsupported policy observations;
6. paper budget, paper-entry, exposure, and risk-limit boundaries;
7. explicit rejection of account-balance, wallet, provider, and live-order
   inputs or fields;
8. stable reason-code sorting, deduplication, and precedence;
9. immutable nested inputs and immutable output;
10. canonicalization and deterministic digest stability;
11. explicit reference-time behavior with the system clock unavailable or
    patched to a different value;
12. exact `APPROVED` → P07 `PASS` and `REJECTED` → P07 `FAIL` handoff
    semantics, without accepting `NOT_REQUIRED` as an entry bypass; and
13. absence of fills, position mutation, ledger writes, reconciliation,
    accounting, realized P&L, classification, G1–G4, and P09 behavior.

Existing P06 and P07 focused suites should remain regression-only inputs to
this future task. They must not be modified by the discovery or by the
smallest implementation unless a separately approved contract change is
identified.

## 9. Recommended Safe V1 design

The recommended Safe V1 is:

```text
one validated P06 DecisionIntent
    +
one immutable paper-only policy snapshot
    +
one caller-supplied simulation reference time
    ↓
one immutable APPROVED or REJECTED result
    ↓
one P07 AuthorizationObservation by identity
```

Safe V1 should:

- require a Risk/Capital result for every paper-entry scenario;
- never use `NOT_REQUIRED` as an entry bypass;
- admit only the explicitly approved P06 paper-entry action/posture, with the
  conservative default of `BUY` plus `WAIT`;
- require P05 hard-risk eligibility and reject P06 uncertainty or invalidation;
- evaluate only one candidate and one explicitly scoped paper portfolio;
- use a virtual paper budget and supplied paper exposure observations;
- authorize no live or external action;
- carry policy identity, digest, version, scope, validity, and bounded reasons;
- use no ambient clock, provider data, account balance, wallet, or order
  state; and
- stop at P07 lifecycle admission.

The conservative `BUY` plus `WAIT` recommendation is intentional: it preserves
the existing distinction between an analytical action and an execution
instruction while avoiding promotion of `WATCH`, `HOLD`, `TAKE_PROFIT`,
`REDUCE`, `EXIT`, `AVOID`, or `NO_TRADE` into a paper-entry request. Whether
`BUY` plus `DEFERRED` should also admit a paper lifecycle remains an owner
decision.

### Unresolved points for the future specification

The following points must be decided before implementation:

1. the canonical virtual budget and exposure units, without introducing a
   live-account or settlement concept;
2. whether the authority approves only lifecycle admission or also supplies a
   maximum paper notional that P07 must enforce;
3. how a paper request quantity, if any, is linked to the approved cap without
   turning this boundary into an order or sizing engine;
4. the exact validity-window and freshness policy for paper state and
   exposure observations;
5. whether `BUY` plus `DEFERRED` is admitted in addition to the recommended
   `BUY` plus `WAIT`;
6. whether Safe V1 supports only single-candidate limits or a bounded
   multi-position paper scope;
7. the exact stable reason precedence when multiple rejection categories apply;
8. whether policy unknown/unavailable states are represented only as
   `REJECTED` reasons or also as an explicit non-approval observation state;
   either choice must remain fail closed; and
9. the exact P07 handoff field for preserving a paper limit if the existing
   authorization scope identity is insufficient.

Until these decisions are resolved, the safe governance state is:

```text
Risk/Capital Authority specification = DISCOVERY ONLY
Risk/Capital Authority implementation = NOT AUTHORIZED
paper entry approval = NOT PRODUCED BY RUNTIME
live authorization/execution = NOT AUTHORIZED
G1/G2/G3/G4 = unchanged and separately governed
P09 = NOT AUTHORIZED
```

## 10. Discovery conclusion

The missing boundary is a small, independent, paper-only admission authority:
it validates one immutable P06 `DecisionIntent` against one immutable,
explicitly supplied paper Risk/Capital Policy Snapshot and emits a
deterministic approval or rejection result for one P07 simulation scope.

It must preserve identity, timestamps, provenance, uncertainty, and
fail-closed states. It must not calculate or claim external economic truth.
Its only possible authority effect is admission to a paper-simulation
lifecycle. All real execution, settlement, accounting, realized P&L,
classification, G1–G4 economic authority, and P09 behavior remain outside
this boundary and require their own governance.

No source code, tests, dependencies, APIs, runtime behavior, providers,
wallets, signers, broadcast paths, settlement endpoints, live-trading
capability, G1, G2, G3, G4, P08-T07, or P09 behavior was created or changed
by this discovery.