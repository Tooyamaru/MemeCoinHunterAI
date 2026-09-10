# P08 — G2 Realization / Settlement Endpoint Boundary Discovery

**Status:** BLOCKED / UNRESOLVED / NOT AUTHORIZED
**Phase:** P08 — Outcome Learning
**Boundary:** G2 — Realization Eligibility and Settlement Endpoint
**Document type:** Documentation-only governance discovery
**Implementation status:** NOT AUTHORIZED
**Provider/endpoint status:** OWNER DECISION REQUIRED

## 1. Scope and current governance position

This document records the unresolved boundary between an externally
authoritative execution or settlement fact and G2 realization eligibility. It
does not choose a provider, chain, venue, endpoint, evidence source, or
settlement model. It creates no runtime behavior, source code, tests,
dependencies, API, integration, wallet behavior, signing, broadcast,
execution, settlement, accounting, classification, persistence, or P09
behavior.

The current position is:

```text
P07                         = paper simulation only; not economic truth
P08-T01 through P08-T06     = immutable non-economic observation/readiness
G1                          = simulation-only recognition/finality authority
Authority A                 = subject/lifecycle identity authority
Authority B                 = correction/supersession lineage authority
G2                          = BLOCKED / UNRESOLVED / NOT AUTHORIZED
G3                          = NOT AUTHORIZED
G4                          = NOT AUTHORIZED
P09                         = NOT AUTHORIZED
```

G2 cannot be specified from the current paper-simulation chain alone. A
`RECOGNIZED / FINAL` G1 result means only that a complete simulation lifecycle
was recognized under the G1 contract. It does not establish external
execution, settlement, realized value, realized P&L, or accounting
admissibility.

The missing decision is therefore not merely an API URL. The owner must decide
which authority and endpoint can establish the governed realization fact, what
that fact means, and how its finality and corrections are represented.

## 2. Purpose of G2

G2 is the future boundary that determines whether the explicitly supplied
evidence for one decision/trade lifecycle satisfies the approved conditions for
a realized outcome.

G2 may eventually assert a bounded realization-eligibility state such as
eligible, non-final, pending, unavailable, invalid, or another owner-approved
vocabulary. It must not:

- create or redefine Authority A subject or lifecycle identity;
- create, correct, supersede, or resolve Authority B lineage facts;
- treat paper simulation as external economic truth;
- infer settlement from a broadcast, transaction hash, order acknowledgement,
  fill message, positive quantity, or paper result;
- calculate accounting, realized P&L, ROI, cost basis, numeraire, conversion,
  precision, or rounding;
- assign `WIN`, `LOSS`, or `BREAKEVEN`;
- authorize capital or execution;
- sign, broadcast, submit, cancel, replace, or retry an order or transaction;
- access a wallet or custody system; or
- invoke or redesign P08-T07, G3, G4, or P09.

G2 is an eligibility boundary, not a general settlement engine and not an
accounting boundary. It may consume a separately governed settlement result or
evidence reference, but the owner must first decide whether settlement
authority belongs inside G2, upstream of G2, or in a separate authority that G2
only validates.

## 3. Required boundary distinctions

The following distinctions are mandatory and remain unresolved as
implementation details until owner decisions lock the exact contracts.

### 3.1 Broadcast is not execution

Broadcast is a submission or propagation event. It means that a transaction
payload was handed to a transport, relay, node, venue, or other submission
boundary. Broadcast does not prove that a transaction was accepted, included,
executed, filled, or settled.

```text
signed payload
    → broadcast/submission evidence
```

The broadcast identity, submission timestamp, transport status, retry history,
and response must remain distinct from any later execution or settlement
identity. A broadcast acknowledgement cannot by itself make a lifecycle
realization-eligible.

### 3.2 Execution is not settlement

Execution is the authoritative occurrence of an order, fill, trade, or
transaction action under the future approved source. It may establish that an
action was performed or a fill occurred. It does not by itself establish that
the resulting asset, obligation, proceeds, or transfer was settled under the
approved realization semantics.

```text
execution/fill evidence
    → separate settlement evidence or settlement authority
```

Order acceptance, transaction inclusion, a venue fill, a chain execution
receipt, or a state transition must not be treated as settlement unless the
owner explicitly approves that equivalence for a defined source and state.

### 3.3 Settlement is not realized P&L

Settlement is the governed fact that an obligation, transfer, delivery,
proceeds movement, or other approved economic endpoint became settled. It is
not the accounting calculation of realized economic result.

```text
settlement / realization evidence
    → G2 realization eligibility
    → G3 accounting and canonical economic result
    → G4 performance classification
    → P08-T07 interpretation / assembly
```

Settlement must carry its own identity, authority, state, timestamp,
provenance, and integrity digest. G3 remains responsible for accounting basis,
quantity treatment, costs, fees, numeraire, conversion, precision, rounding,
sign convention, and realized P&L. A settled event must not be labeled
profitable or classified by G2.

### 3.4 Valuation is not settlement

A mark, quote, market observation, or valuation at a timestamp is not a
settlement event. If valuation is ever authorized, it must remain explicitly
separate from realization eligibility and realized P&L. G2 must not upgrade a
valuation endpoint into a settlement endpoint without a separate governance
decision.

## 4. Current ownership and dependency map

| Boundary | Owns | G2 relationship |
|---|---|---|
| Authority A | Canonical economic subject and lifecycle identity, mapping, equivalence, split, and mapping conflicts | G2 preserves the established references and fails closed on mismatch; it does not create or redefine identity. |
| Authority B | Immutable correction and supersession lineage facts | G2 consumes validated lineage references where approved; it does not create, choose, repair, or resolve lineage. |
| P07-T01 through P07-T07 | Paper input, fills, paper state, paper ledger, reconciliation, finalized non-economic result, and local history | G2 may preserve the chain as context. It must not treat paper facts as external execution or settlement. |
| P08-T01 through P08-T06 | Observation linkage, dataset cutoff, evidence-state interpretation, evidence evaluation, snapshot, and non-economic readiness | G2 may preserve their identities and cutoff. Readiness is not economic evidence and does not establish realization. |
| G1 | Simulation-only lifecycle recognition/finality | G2 may consume the immutable G1 result, but G1 `FINAL` is not settlement or realized P&L. |
| G2 | Future realization eligibility | G2 owns only the approved eligibility assertion and its failure/non-final semantics. |
| G3 | Accounting and canonical economic-result calculation | G3 owns economic quantities, costs, basis, numeraire, conversion, precision, rounding, and realized result calculation. |
| G4 | Performance classification | G4 owns `WIN`, `LOSS`, `BREAKEVEN`, and any approved classification vocabulary. |
| P08-T07 | Interpretation and assembly of separately supplied G2/G3/G4 results | G2 supplies a materialized result; T07 remains the independent consumer and assembler. |
| P09 | Separately governed live execution chain | P09 remains unauthorized and cannot be activated by G2. |

The existing execution boundary remains:

```text
Decision Intent
    → Risk / Capital Authorization
    → Execution Request
    → Isolated Signing Boundary
    → Broadcast
    → Reconciliation
    → Journal
```

That chain does not answer which event is the G2 realization endpoint. It also
does not authorize any of those future runtime steps.

## 5. Immutable evidence G2 may consume

Subject to a later approved G2 contract, G2 may consume explicit immutable
references to:

1. Authority A canonical economic subject identity and lifecycle identity;
2. the complete P06 → P07 → P08-T06 provenance chain;
3. the immutable G1 result identity, recognition state, finality state,
   provenance, and digest;
4. Authority B correction/supersession facts and their validated lineage
   projections, without selecting a canonical head itself;
5. a future explicitly materialized execution/fill result;
6. a future explicitly materialized settlement/realization result;
7. source, authority, event, transaction, order, fill, settlement, and
   correction identities;
8. source contract/policy versions, timestamps, finality state, and digests;
9. an explicit immutable snapshot or evidence packet whose membership and
   cutoff semantics are defined by the approved G2 contract; and
10. explicit unavailable, contradictory, stale, corrected, superseded, or
    non-final states defined by the approved authority.

These are references and governed facts, not permission to reconstruct missing
records. G2 must not infer a settlement record from an identifier, transaction
hash, timestamp, quantity, order status, paper result, or database lookup.
G2 must not create a parallel Authority A identity, a second Authority B
lineage, or a substitute economic evidence authority.

## 6. Owner decisions required before a G2 specification

No G2 specification can be considered implementation-ready until each decision
below is explicitly answered and recorded.

### 6.1 Authoritative source and endpoint

1. What exact source is authoritative for realization or settlement?
2. Is the source a venue record, chain/RPC observation, custodian/account
   ledger, wallet-controlled record, transaction indexer, manual attestation,
   provider-neutral adapter, or a separately governed authority?
3. Is there one authoritative source or a source hierarchy/quorum?
4. What exact provider, endpoint family, API version, chain, venue, or
   provider-neutral interface is approved?
5. Who owns the source contract, credentials, availability semantics, and
   corrections?
6. Is the source read-only to G2, with all side effects prohibited?
7. What evidence is authoritative when provider sources disagree?

Until these decisions are made, the provider/endpoint owner is unresolved and
G2 remains blocked.

### 6.2 Supported scope

The owner must specify:

- supported chains and network identifiers;
- supported venues, programs, or execution environments;
- supported assets and asset identity rules;
- supported order, trade, fill, transfer, and settlement types;
- account, custody, wallet, or sub-account scope, if any;
- whether cross-chain, bridged, wrapped, or routed assets are in scope; and
- explicit out-of-scope cases and their fail-closed states.

### 6.3 Finality, correction, and reorganization

The owner must define:

- what state counts as execution;
- what state counts as settlement;
- what state counts as final;
- confirmation/finality requirements and their authority;
- replacement, cancellation, reversal, chargeback, and failed-settlement rules;
- chain reorganization and transaction re-inclusion semantics;
- venue correction and late-update semantics;
- whether finality can be reopened;
- whether a changed result is a correction, supersession, invalidation, or new
  lifecycle fact; and
- which facts belong to Authority B rather than G2.

G2 must never resolve a correction or supersession branch by freshness,
insertion order, result magnitude, or caller preference.

### 6.4 Canonical identities

The owner must lock the canonical identity and linkage for:

- the decision and lifecycle;
- the account or custody scope, if relevant;
- the order;
- each execution/fill;
- the transaction and transaction attempt;
- the broadcast/submission;
- the settlement event;
- the asset and quantity;
- the source and authority;
- the finality assertion; and
- any correction or supersession fact.

The owner must also decide which identities participate in semantic identity,
which are provenance-only, and how circular references are prevented.

### 6.5 Cutoff and timestamp semantics

The owner must define:

- event time, observation time, submission time, inclusion time, execution
  time, settlement time, finality time, correction time, and ingestion time;
- the authoritative timestamp for each event;
- UTC normalization and invalid timezone behavior;
- the G2 cutoff or explicit realization horizon;
- whether the endpoint is event-time, settlement-time, as-of, or another
  governed horizon;
- equal-timestamp ordering;
- late evidence and future-dated evidence;
- replay behavior under a changed source snapshot; and
- future-leakage prevention.

P08-T02 `as_of_time` remains the upstream dataset cutoff. It must not silently
become the G2 settlement endpoint or realized-outcome horizon.

### 6.6 Duplicate, contradiction, and unavailable-data rules

The owner must define exact behavior for:

- duplicate orders, fills, transactions, broadcasts, and settlement events;
- repeated provider pages or replayed source responses;
- partial fills and multiple settlement legs;
- contradictory source identities or quantities;
- missing source records;
- provider outage and unavailable endpoint data;
- stale data and delayed finality;
- incomplete account or chain history;
- reorg or venue correction after a prior result; and
- multiple possible lifecycle assignments.

G2 must distinguish unavailable evidence from confirmed absence where the source
contract permits that distinction. It must fail closed rather than silently
prefer, filter, deduplicate, or repair conflicting evidence.

### 6.7 Provenance, digest, retention, and audit

The owner must define:

- the complete immutable provenance chain;
- source, authority, endpoint, request, response, and policy identities;
- canonical serialization and Unicode rules;
- digest algorithm and non-circular identity projection;
- evidence snapshot membership and ordering;
- retention and replay requirements;
- correction and supersession retention;
- audit record requirements;
- source availability and evidence-quality metadata; and
- whether raw responses are retained or only governed materializations.

G2 must preserve the exact inputs that support an eligibility assertion. It must
not use process state, wall-clock time, filesystem state, database order,
network timing, or hidden configuration to change a result.

### 6.8 Boundary with G3 and G4

The owner must define the exact handoff:

```text
G2 realization eligibility
    → G3 accounting / canonical economic result
        → G4 classification
            → P08-T07 interpretation / assembly
```

The handoff must specify:

- which G2 states G3 may consume;
- whether G2 supplies event references, a settlement assertion, an eligibility
  result, or separate records;
- what G2 must not include in economic calculation;
- how partial and residual quantities are handed to G3;
- which costs and fees are evidence only versus accounting inputs;
- the exact G3 accounting basis and numeraire ownership;
- the exact G4 classification input and prohibition on G2 classification; and
- how non-final, unavailable, contradictory, corrected, and superseded states
  appear downstream.

## 7. Fail-closed behavior while the endpoint is unresolved

Until the owner approves the source, endpoint, supported scope, finality rules,
identity contract, and G2 specification:

- no provider or endpoint is selected or contacted;
- no external execution or settlement evidence is accepted as G2 authority;
- no G2 realization-eligibility result is produced;
- no paper result or G1 `FINAL` result is upgraded to realized;
- no settlement, realized P&L, accounting, or classification result is
  produced;
- no missing evidence is inferred from transaction, order, fill, or paper
  identifiers;
- no source conflict is resolved by preference or freshness;
- no correction, supersession, reorg, reversal, or duplicate is silently
  repaired; and
- downstream G3, G4, and P08-T07 must treat the absent/unapproved G2 result as
  unavailable for a valid realized interpretation.

The current fail-closed governance state is:

```text
G2 source/endpoint owner          = UNRESOLVED
G2 specification                  = BLOCKED
G2 implementation                 = NOT AUTHORIZED
realization eligibility           = NOT ESTABLISHED
settlement authority              = NOT ESTABLISHED
realized P&L                      = NOT ESTABLISHED
G3 / G4 / P09                     = NOT AUTHORIZED
```

This is a governance state, not a runtime result vocabulary. No source code is
created by this discovery.

## 8. Future-only implementation and test scope

After owner decisions, a separate G2 specification, formal audit, and explicit
implementation authorization, future work may define:

### 8.1 Future implementation scope

- immutable input and output contracts;
- explicit G1, Authority A, and Authority B references;
- source/endpoint materialization boundary;
- execution and settlement event contracts;
- finality and endpoint state machine;
- canonical identity and digest derivation;
- timestamp and cutoff validation;
- source snapshot membership and duplicate handling;
- correction, supersession, reversal, and reorg handling;
- unavailable versus absent evidence behavior;
- G2-to-G3 handoff references;
- deterministic fail-closed evaluator behavior; and
- no side-effecting provider, wallet, signing, broadcast, or execution code
  unless a separate later authorization explicitly permits it.

### 8.2 Future test scope

The future focused suite must cover at least:

1. supported source, chain, venue, and asset scope;
2. exact execution-versus-settlement distinction;
3. broadcast without execution;
4. execution without settlement;
5. settlement without accounting or classification;
6. finality and confirmation rules;
7. replacement, cancellation, reversal, chargeback, and reorg behavior;
8. duplicate and replayed source records;
9. partial fills and multiple settlement legs;
10. missing, unavailable, stale, future, and contradictory evidence;
11. cross-lifecycle and ambiguous identity linkage;
12. correction and supersession without in-place mutation;
13. canonicalization, Unicode, timestamp, identity, and digest tampering;
14. deterministic replay independent of retrieval or provider order;
15. provenance, retention, and audit coverage;
16. G1 and Authority A/B ownership preservation;
17. G3 accounting handoff without economic calculation in G2;
18. G4 classification exclusion;
19. no provider, wallet, signing, broadcast, execution, persistence, or P09
    behavior outside a separately approved adapter boundary; and
20. complete reason/state precedence and fail-closed behavior.

These are future-only verification expectations. They do not authorize a G2
implementation or a provider integration.

## 9. Authorization gates

### 9.1 Gate for a G2 specification

G2 specification work may begin only after all of the following are approved:

1. an authoritative realization/settlement source and endpoint owner;
2. supported chain, venue, asset, account, custody, and event scope;
3. execution, broadcast, settlement, realization, and finality semantics;
4. correction, supersession, replacement, reversal, and reorg semantics;
5. canonical identities and lifecycle linkage;
6. cutoff, timestamp, replay, duplicate, contradiction, and unavailable-data
   rules;
7. provenance, digest, retention, and audit requirements;
8. exact G1/Authority A/Authority B relationship;
9. exact G2-to-G3 accounting boundary;
10. exact G3-to-G4 classification boundary;
11. prohibited behavior and security boundaries; and
12. documented formal review showing that P07, P08-T01 through T07, Authority A,
    and Authority B are not redefined.

### 9.2 Gate for a G2 implementation

Implementation may begin only after:

1. the G2 specification is complete;
2. the G2 specification audit passes;
3. the provider/endpoint owner and source contract are explicitly approved;
4. the exact implementation files and focused tests are authorized;
5. the implementation boundary excludes G3, G4, P09, wallets, signing,
   broadcast, execution, settlement side effects, and unapproved providers;
6. deterministic and fail-closed behavior is tested; and
7. a separate implementation audit passes before G3 specification work begins.

No discovery-complete status satisfies either gate.

## 10. Discovery conclusion

The G2 problem is bounded but unresolved:

> G2 needs an owner-approved, authoritative, immutable realization/settlement
> endpoint and exact finality semantics before it can determine realization
> eligibility for one lifecycle.

The current project has the required upstream identity, simulation, evidence,
readiness, and lineage references, but it does not have an approved source that
establishes external execution or settlement. Execution, broadcast, and
settlement remain distinct; settlement remains distinct from realized P&L.

```text
G2 = BLOCKED / UNRESOLVED / NOT AUTHORIZED
provider/endpoint owner decision = REQUIRED
G3 = NOT AUTHORIZED
G4 = NOT AUTHORIZED
P09 = NOT AUTHORIZED
```

No code, tests, dependencies, providers, wallets, signing, broadcast,
execution, settlement, accounting, classification, API, or runtime behavior
was created by this discovery.