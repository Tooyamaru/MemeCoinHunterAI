# P08 — Read-Only Market-Data Adapter Proposal

**Status:** PROPOSAL ONLY / DOCUMENTATION-ONLY / IMPLEMENTATION NOT AUTHORIZED  
**Phase:** P08 — Outcome Learning  
**Proposed boundary:** Read-only market observations for candidate discovery and
paper-only evaluation  
**Proposed contract version:** `p08-read-only-market-data-observation-v1`  
**Nature:** Immutable, deterministic, provider-neutral, read-only

## 1. Purpose

This proposal defines a future adapter boundary that supplies normalized,
read-only market observations for:

1. token-candidate discovery; and
2. provider-neutral, paper-only opportunity evaluation.

The boundary supplies evidence. It does not trade, authorize trading, create an
order, or establish external economic truth. A valid observation means only that
the supplied market evidence is internally coherent, attributable, within its
explicit cutoff and freshness policy, and safe for an explicitly authorized
downstream analytical or paper-simulation consumer.

The proposal does not create implementation authority. It does not modify the
existing P02, P05, P06, Risk/Capital, P07, P08, G1, or governance contracts.

## 2. Architectural position

The proposed direction is:

```text
future source-specific collection
        ↓
future provider-neutral adapter boundary
        ↓
P08 read-only canonical market observation
        ↓
explicit discovery or paper-evaluation consumer
        ↓
P05 opportunity context / P07 paper-simulation observation
```

The adapter is the only boundary that translates a future source payload into
this observation contract. Source-specific parsing, transport behavior, retry
behavior, authentication, and source error translation remain outside the
canonical domain record.

The adapter must not bypass existing P02 admission, market-state, freshness, or
provenance contracts when those contracts are the approved predecessor for a
given input. Where an observation is materialized through an existing P02
boundary, the P02 identity and digest remain predecessor-owned facts.

## 3. Provider neutrality

The canonical contract contains no vendor, venue, endpoint, SDK, transport, or
provider-specific type. It accepts only bounded provider-neutral values and
source/provenance identities.

A future source adapter may:

- parse its own source payload;
- translate source-specific errors into bounded rejection reasons;
- preserve source event identity where supplied;
- compute the raw-payload digest; and
- construct the provider-neutral candidate presented to this boundary.

It may not expose source objects, callbacks, clients, credentials, handles,
unbounded logs, or transport state to canonical consumers. Replacing one future
source adapter with another must not require changing the observation contract,
P05/P06 contracts, Risk/Capital contracts, P07 contracts, or G1.

No source, provider, venue, endpoint, SDK, or provider-specific implementation
is selected or named by this proposal.

## 4. Canonical observation contract

The future public record is an immutable
`ReadOnlyMarketDataObservation`. It contains exactly the semantic groups below.
Unknown fields are rejected; absent and `null` are not interchangeable.

### 4.1 Contract and observation identity

| Field | Requirement |
|---|---|
| `contract_version` | Exactly `p08-read-only-market-data-observation-v1` for this proposal. |
| `observation_id` | Stable source-observation identity, or a deterministic identity derived from the approved identity projection. |
| `candidate_id` | Non-empty deterministic candidate identity. |
| `chain_id` | Non-empty canonical chain-domain identity. It is an identity value only. |
| `token_identity` | Non-empty canonical token identity reused from the approved upstream token contract. |
| `market_subject_id` | Explicit opaque market-subject identity when a market subject exists; it is never inferred from display metadata. |
| `observation_kind` | Explicit supported kind, such as `DISCOVERY` or `PAPER_EVALUATION`; no implicit consumer mode is inferred. |
| `observed_at` | Required timezone-aware timestamp normalized to canonical UTC. |
| `availability_at` | Required timezone-aware UTC timestamp at which the observation was available to the consumer. |
| `sequence` | Explicit source sequence/cursor when provided; otherwise explicit `null` with ordering unknown. |

`candidate_id` identifies the analytical candidate. The `(chain_id,
token_identity)` pair remains the minimum token identity. A
`market_subject_id`, when present, distinguishes an explicitly supplied market
subject without defining it as a venue, pool, route, or execution target.

An observation must not derive identity from a display name, symbol, object
address, process identity, random value, insertion order, or current time.

### 4.2 Source and provenance

The immutable `source` group contains:

| Field | Requirement |
|---|---|
| `source_id` | Stable logical source identity at the provider-neutral boundary. |
| `source_event_id` | Source event identity when supplied; explicit `null` otherwise. |
| `source_contract_version` | Exact version of the source-to-adapter translation contract. |
| `adapter_contract_version` | Exact version of this adapter boundary. |
| `source_observed_at` | Source-declared observation time when available, normalized to UTC; it must agree with the observation time under the approved source contract. |
| `source_metadata` | Bounded canonical metadata only; no credentials, opaque values, or unbounded payload. |

The immutable `provenance` group contains the bounded identity and context
needed to reproduce the observation, including:

- source and source-event identity;
- candidate, chain, token, and market-subject identity;
- observation and availability timestamps;
- the explicit cutoff and freshness-policy identity;
- the upstream contract/version references;
- the consumer profile, when one is supplied; and
- any approved predecessor observation or state digest.

Provenance is evidence of origin and context. It is not an authority grant, an
approval, a source preference, or a claim that the source is authoritative.

### 4.3 Raw payload integrity

The adapter must compute and preserve:

| Field | Requirement |
|---|---|
| `raw_payload_digest` | Lowercase 64-character SHA-256 digest of the source payload's approved canonical byte representation. |
| `observation_digest` | Lowercase SHA-256 digest of the complete canonical observation excluding only `observation_digest`. |

The raw source payload is not part of the public canonical observation. The
digest is the integrity reference; it is not permission to retrieve the payload
later and is not a substitute for missing normalized fields.

The observation digest covers the contract version, identity, timestamps,
source/provenance, normalized fields, cutoff/freshness material, raw-payload
digest, and all other canonical fields. A digest is derived, verified, and
never accepted as authority over different source fields.

Nested digests must be validated before the enclosing observation digest. A
digest mismatch rejects the observation; no repair, recomputation from partial
material, or silent replacement is allowed.

### 4.4 Normalized fields

The initial allowed normalized field catalog is deliberately small:

| Field | Normalized meaning | Required source semantics |
|---|---|---|
| `price` | Finite decimal value plus explicit quote-asset/unit metadata. | Must be supplied by the future source; no price is inferred from another field. |
| `liquidity` | Finite decimal value plus explicit unit metadata and valuation context. | Must be supplied by the future source; no depth or liquidity is inferred from volume. |
| `volume` | Finite decimal value plus explicit unit and measurement-window metadata. | Must be supplied by the future source; no volume is inferred from transactions. |
| `asset_age` | Source-provided age with an explicit unit and reference semantics. | Must be supplied by the future source; it is distinct from observation data age. |
| `holders` | Source-provided holder count or bounded holder observation, only when the future source provides it. | Optional field; absence is not zero and cannot be inferred. |
| `transactions` | Source-provided transaction count or bounded transaction observation, only when the future source provides it. | Optional field; absence is not zero and cannot be inferred. |

Each field is represented by an explicit immutable field envelope containing:

- field status: `PRESENT`, `MISSING`, `UNAVAILABLE`, or `INVALID`;
- value, which is `null` unless status is `PRESENT`;
- unit and semantic version where applicable;
- source-provided measurement-window or reference metadata where applicable;
- field-level provenance reference; and
- field-level digest material included in the observation digest.

The adapter may preserve a rejected observation with a missing, unavailable, or
invalid field for auditability when the safely available identity and integrity
material is valid. It must not emit that record as an accepted usable
observation for a consumer profile that requires the field.

No field may be silently defaulted to zero, an empty collection, a current
value, a guessed unit, or a value reconstructed from another field. Holders and
transactions are not required merely because the observation is a market
observation; they are admitted only when supplied by a future source and
authorized by the consumer's versioned field policy.

This proposal does not define formulas, source coverage, valuation, cross-source
aggregation, or feature derivation for any field.

## 5. Cutoff and freshness semantics

Every validation call must supply an explicit immutable evaluation context:

- `cutoff_time`, timezone-aware and normalized to UTC;
- a versioned `freshness_policy`;
- the intended consumer profile; and
- any explicit predecessor snapshot or ordering context.

The adapter computes observation data age only from supplied values:

```text
data_age = cutoff_time - observed_at
```

The following rules are mandatory:

1. `observed_at <= availability_at <= cutoff_time`.
2. A future observation is invalid; it is never delayed into validity.
3. A negative data age is invalid.
4. A configured maximum age is applied only when explicitly supplied by the
   freshness policy.
5. `data_age == max_age` is valid when the policy uses an inclusive boundary.
6. An observation older than the policy is `STALE` and is not accepted as current
   usable evidence.
7. Missing, malformed, or contradictory timestamps fail closed.
8. `observed_at` is not replaced by received time, processing time, or the
   system clock.
9. A later processing time cannot make an old observation fresh.
10. The adapter's cutoff is validation context only. It does not replace the
    P07 simulation reference time, the P08 dataset cutoff, or any predecessor
    contract's owned timestamp.

`asset_age` is a source-provided normalized field and must not be confused with
`data_age`. If an evaluation rule needs both, both must be present and valid.
Missing age information fails closed for that rule.

## 6. Consumer profiles and fail-closed input policy

The observation contract does not decide which fields a downstream strategy
needs. A separately versioned consumer profile must declare its required fields,
units, freshness policy, and permitted optional fields.

### 6.1 Candidate discovery

A discovery profile may consume only the canonical candidate identity and the
explicitly authorized normalized market fields. A discovery result is usable
only when every field required by that profile is `PRESENT`, finite,
unit-valid, provenance-valid, and within the supplied cutoff/freshness policy.

Missing price, liquidity, volume, or asset age must not be converted into an
eligible discovery candidate when that field is required by the profile.
Missing holders or transactions must remain explicit and cannot be treated as
zero, healthy, inactive, or safe.

Presence in a discovery observation does not mean that a token is safe,
eligible, liquid, tradable, profitable, or authorized.

### 6.2 Paper-only opportunity evaluation

A paper-evaluation profile may admit the same normalized field catalog only when
the profile explicitly declares the fields needed for its point-in-time
evaluation. At minimum, a profile that uses market conditions must declare its
required price, liquidity, volume, and age semantics. Holders and transactions
may be used only when a future source has supplied them under an approved
field/version contract and the profile explicitly requires or permits them.

If any required value is missing, stale, unavailable, invalid, contradictory,
unsupported, or outside the cutoff, the profile produces a fail-closed
non-usable result. It must not manufacture a quote, fill, score component,
confidence value, or opportunity from partial data.

An accepted observation can be supplied as evidence to a future paper-only
evaluation. It is not a paper order, fill, position transition, ledger entry,
authorization, or simulation result. P07 must validate and own its own
`execution_observation` contract before using any observation in a simulation.

## 7. Canonicalization and immutability

The future implementation must use the repository's established canonical
representation rules:

- mappings have sorted string keys;
- sequences have explicit semantic order;
- sets are forbidden;
- timestamps are timezone-aware and serialized as canonical UTC;
- decimal values are finite, normalized decimal text;
- binary floating-point, NaN, and infinity are rejected;
- enum values use explicit wire values;
- `null` is explicit and is not equivalent to an omitted field;
- text is trimmed, bounded, and canonical;
- unknown fields and non-string mapping keys are rejected; and
- SHA-256 is computed over compact, deterministic UTF-8 canonical material.

The public observation, nested metadata, field envelopes, provenance, and
canonical views must be recursively immutable. A later observation creates a new
record and never edits an earlier observation or its provenance.

Equivalent canonical inputs and equivalent explicit evaluation contexts must
produce equal identities, outcomes, canonical representations, and digests.

## 8. Validation order and reason-code precedence

Validation must be deterministic and independent of caller order. The proposed
single-result reason vocabulary is:

```text
VALID
INVALID_TYPE
MISSING_REQUIRED_INPUT
UNSUPPORTED_VERSION
INVALID_CANONICAL_REPRESENTATION
DIGEST_MISMATCH
INVALID_IDENTITY
PROVENANCE_FAILURE
CONTRADICTORY_INPUT
FUTURE_OBSERVATION
STALE_OBSERVATION
UNAVAILABLE_INPUT
INCOMPLETE_INPUT
UNSUPPORTED_FIELD
OUT_OF_ORDER
REPLAY
DUPLICATE
DETERMINISM_FAILURE
```

The implementation must select exactly one reason from the fixed precedence
below when more than one condition is visible:

1. `INVALID_TYPE`
2. `MISSING_REQUIRED_INPUT`
3. `UNSUPPORTED_VERSION`
4. `INVALID_CANONICAL_REPRESENTATION`
5. `DIGEST_MISMATCH`
6. `INVALID_IDENTITY`
7. `PROVENANCE_FAILURE`
8. `CONTRADICTORY_INPUT`
9. `FUTURE_OBSERVATION`
10. `STALE_OBSERVATION`
11. `UNAVAILABLE_INPUT`
12. `INCOMPLETE_INPUT`
13. `UNSUPPORTED_FIELD`
14. `OUT_OF_ORDER`
15. `REPLAY`
16. `DUPLICATE`
17. `DETERMINISM_FAILURE`
18. `VALID`

Precedence is based on the canonical validation model, not retrieval order,
arrival order, timestamps, value magnitude, freshness preference, or caller
preference. `VALID` is used only when the complete required material is valid.

`MISSING_REQUIRED_INPUT` covers absent required observation, context, field, or
cutoff material. `INCOMPLETE_INPUT` covers a structurally present observation
whose required consumer fields are explicitly unavailable or missing under the
selected profile. A future implementation must document the exact distinction
without allowing either state to pass.

## 9. Replay, duplicate, contradiction, and ordering behavior

The adapter must receive its processing context explicitly. It may not consult a
process-global registry, hidden cache, filesystem, database, network, or
current source state.

### 9.1 Exact replay

An exact replay has the same canonical observation, same explicit cutoff and
freshness context, same consumer profile, and same explicit prior-context
identity. It returns the same immutable result, canonical representation, and
digest, with reason `REPLAY` when an outcome record is needed. Replay does not
create another accepted observation, advance ordering, or mutate context.

### 9.2 Duplicate

A duplicate has the same observation identity and canonical content as an
already supplied accepted observation in the explicit processing context but is
not the same complete replay request. It is observable as `DUPLICATE`, does not
replace the accepted record, does not advance sequence state, and leaves the
context digest unchanged.

### 9.3 Contradiction

A contradiction occurs when the same observation identity is paired with
different canonical content, or when identity, source, candidate, timestamps,
provenance, field status, or digest material disagree. It returns
`CONTRADICTORY_INPUT`, preserves the previously accepted record, and leaves
ordering and context digests unchanged. The adapter must not choose a value by
arrival order, source label, or undocumented preference.

Different source identities remain separate observations. Cross-source merge,
consensus, reconciliation, interpolation, and authoritative-source selection
require a separate contract.

### 9.4 Ordering

Only explicit comparable sequence/cursor semantics may establish ordering.
Integer sequences may be compared under the approved source contract. An
untyped or incomparable cursor remains ordering-unknown and is not guessed.
Missing sequence is not evidence of order. Rejected, stale, unavailable,
duplicate, contradictory, or replayed records do not advance ordering state.

## 10. Version compatibility and unsupported versions

The proposed observation contract supports only the exact version
`p08-read-only-market-data-observation-v1`. Any change to field meaning,
requiredness, canonicalization, identity, digest coverage, timestamp semantics,
field units, or validation behavior requires a new explicit contract version.

Unsupported observation, source, adapter, field, freshness, consumer-profile,
or predecessor versions fail closed with `UNSUPPORTED_VERSION`. Version-like
names, overlapping fields, matching digests, or compatible-looking statuses do
not authorize substitution.

No automatic migration, legacy promotion, inference, reconstruction, or
reinterpretation is permitted. A future migration would require its own
specification, canonical representation, focused tests, implementation
authorization, and audit.

## 11. No ambient external state

Validation, normalization, identity derivation, and digest calculation must be
pure with respect to the explicit inputs. The boundary must not read or depend
on:

- wall-clock time;
- local timezone;
- random values or random UUIDs;
- environment variables or hidden configuration;
- process identity or memory address;
- dictionary/set insertion order;
- filesystem state;
- database, cache, queue, or durable history;
- network or source availability;
- a provider client or SDK;
- a hidden registry or mutable singleton; or
- a caller preference not represented in the canonical context.

All reference times, freshness policies, source metadata, predecessor
snapshots, ordering context, and replay identity must be supplied explicitly.
If a deterministic identity or digest cannot be computed safely, the input is
rejected rather than approximated.

## 12. Ownership boundaries

### 12.1 P02 and source adaptation

Existing P02 contracts own the approved upstream token and market-observation
admission, current-state materialization, and provider-neutral data conventions.
This proposal must reuse their identities and predecessor digests where
applicable and must not mutate them.

The proposed adapter owns only translation into the read-only canonical
observation and its validation result. It does not own source lifecycle,
transport health, retry/recovery, durable persistence, or a cross-source state.

### 12.2 P05 Opportunity Engine

P05 owns candidate normalization, hard-risk gating, feature availability,
opportunity scoring, opportunity records, and opportunity context.

The adapter may supply validated observation evidence to an explicitly approved
P05 input boundary. It must not:

- create or replace a P05 candidate;
- reevaluate safety or eligibility;
- calculate P05 features without an approved P05 feature contract;
- score, rank, compare, or reduce candidates;
- create an opportunity record or context; or
- treat a valid observation as `ELIGIBLE`.

P05 remains responsible for missing-data behavior at its own contract boundary.

### 12.3 P06 Decision Engine

P06 owns deterministic decision evaluation and immutable `DecisionIntent`
production from a validated P05 context.

The adapter may not fetch data for P06, modify a P06 context, select an action,
produce confidence, create a decision intent, or interpret market evidence as
authorization. P06 consumes only the explicit point-in-time evidence admitted by
its own contract and remains analytical intent, not permission.

### 12.4 Risk / Capital Authority

Risk/Capital owns capital admission, risk-governor state, approval scope,
validity, and the exact paper-only authorization reference required by the
current P07 v2 admission path.

The adapter does not create, infer, renew, validate, or substitute
Risk/Capital authorization. A market observation with `VALID` quality is not a
Risk/Capital `PASS`, and missing market evidence remains fail-closed wherever
the Risk/Capital policy requires it.

### 12.5 P07 Paper Trading Engine

P07 owns paper-simulation input, fills, paper-state transitions, ledger,
reconciliation, canonical non-economic result, and local paper-result history.

The adapter may provide a read-only market observation as explicitly supplied
evidence to a P07 execution-observation envelope only after P07 validates the
required identity, cutoff, quality, provenance, and digest links. It does not:

- calculate fills, fees, spread, slippage, impact, latency, or MEV;
- create an execution observation by hidden lookup;
- authorize a paper lifecycle;
- mutate position, exposure, ledger, or history;
- reconcile against external truth; or
- turn a data observation into an order or execution request.

P07's explicit `simulation_reference_time` remains the P07 cutoff.

### 12.6 G1

G1 owns only simulation-only recognition and finality for a complete,
explicitly supplied P06 → P07 → P08 chain. It validates predecessor-owned
contracts through their own canonical representations and does not create
market observations.

This adapter is not a G1 authority and does not add a G1 input, cutoff,
economic state, or provenance link. G1 may encounter the observation
transitively inside a validated predecessor artifact, but G1 does not
reinterpret it, recalculate it, or use it to establish settlement, valuation,
accounting, realized P&L, or performance.

## 13. Minimal future implementation scope

Implementation is not authorized by this proposal. If separately authorized,
the smallest proposed implementation boundary is:

```text
core/data/read_only_market_data.py
tests/test_read_only_market_data.py
```

`core/data/__init__.py` may be changed only if an explicit implementation
authorization names the required public exports. No other source, test,
dependency, workflow, environment, database, migration, or project-state file
is part of this proposal.

The future implementation should contain only:

1. immutable canonical observation and field-envelope values;
2. explicit consumer-profile and freshness-policy inputs;
3. deterministic identity, canonicalization, and SHA-256 digest validation;
4. fail-closed validation and the fixed reason precedence;
5. explicit replay, duplicate, contradiction, and sequence handling; and
6. a local, explicit processing context with no ambient state.

It must not add a live source adapter, source client, transport, persistence,
worker, API, dashboard, or integration.

## 14. Focused future test scope

If and only if implementation is separately authorized, the focused test file
must cover:

1. valid immutable discovery observation with complete required fields;
2. valid immutable paper-evaluation observation with explicit cutoff;
3. candidate, chain, token, and market-subject identity validation;
4. source identity, source-event identity, bounded provenance, and raw-payload
   digest preservation;
5. canonical normalized price, liquidity, volume, asset-age, holders, and
   transactions field envelopes;
6. holders and transactions accepted only when explicitly supplied and
   version-authorized by the future source contract;
7. missing, null, unavailable, stale, future, invalid, and non-finite values;
8. missing required consumer fields failing closed without zero/default
   substitution;
9. explicit cutoff equality and stale-boundary behavior;
10. unsupported observation, field, freshness, and consumer-profile versions;
11. canonical representation stability across mapping order and equivalent
    timestamp/decimal forms;
12. raw-payload and observation SHA-256 digest verification and tampering;
13. exact replay producing the same result and digest without mutation;
14. duplicate identity/content producing `DUPLICATE` without replacement;
15. same identity with changed content producing `CONTRADICTORY_INPUT` without
    replacement;
16. explicit sequence ordering, missing sequence, and out-of-order behavior;
17. deterministic reason-code precedence when several failures coexist;
18. no wall-clock, random, environment, filesystem, persistence, network,
    source-client, provider, or ambient-registry dependency;
19. recursive immutability and upstream-context non-mutation; and
20. absence of scoring, ranking, decision, authorization, execution, settlement,
    accounting, or live-trading behavior.

Tests must use deterministic local fixtures only. They must not contact a
source, network, external service, database, queue, or provider SDK.

## 15. Explicit exclusions

This proposal does not include and does not authorize:

- any named or selected provider;
- provider-specific code or SDKs;
- exchange integration;
- wallet access or wallet state;
- signer or signing behavior;
- chain transactions or chain-transaction submission;
- API credentials, access tokens, or secrets;
- live trading;
- order creation, order broadcast, or execution;
- settlement or external finality;
- accounting, valuation, cost basis, numeraire, or realized P&L;
- G2 realization eligibility;
- G3 accounting or economic-result calculation;
- G4 performance classification;
- P09 controlled execution;
- network calls, source polling, retry, failover, or recovery;
- persistence, database schema, migrations, queues, caches, or durable replay;
- source aggregation, consensus, interpolation, or conflict resolution;
- safety or eligibility evaluation;
- signal generation or feature calculation without a separate contract;
- opportunity scoring, ranking, comparison, or reduction;
- P06 decision production;
- Risk/Capital authorization;
- P07 fill, position, ledger, reconciliation, or history mutation;
- G1 recognition, finality, or economic interpretation;
- AI, ML, LLM, narrative analysis, or autonomous behavior; and
- any change to source code, tests, dependencies, workflows, or governance state
  as part of this documentation-only proposal.

## 16. Separate gates before code

No implementation may begin from the existence of this proposal. The gates are
separate and ordered:

### Gate 1 — Proposal and architecture approval

The project owner must approve:

- the purpose and read-only boundary;
- the exact canonical field groups;
- the allowed normalized field catalog;
- missing-data fail-closed semantics;
- cutoff and freshness ownership;
- identity, provenance, canonicalization, and SHA-256 coverage;
- reason vocabulary and precedence;
- replay, duplicate, contradiction, and ordering behavior;
- ownership boundaries with P02, P05, P06, Risk/Capital, P07, and G1; and
- the explicit exclusions.

Approval must not be interpreted as implementation authorization.

### Gate 2 — Formal audit

An independent documentation audit must confirm that the approved proposal:

- is internally consistent and implementation-testable;
- does not weaken any closed predecessor contract;
- preserves P07 v2 Risk/Capital admission and paper-only semantics;
- preserves P06 intent-only authority and Risk/Capital higher authority;
- preserves P07's non-economic simulation boundary;
- preserves G1's predecessor-owned validation and non-economic recognition;
- has no provider-specific leakage or secret-bearing field;
- has deterministic cutoff, digest, version, replay, duplicate, contradiction,
  and reason-precedence semantics; and
- contains no scope that belongs to G2, G3, G4, or P09.

The audit must be recorded separately. Audit completion does not authorize code.

### Gate 3 — Explicit implementation authorization

Only a separate authorization may permit code. It must name the exact approved
files, contract version, public exports, focused tests, dependency posture,
forbidden behaviors, and verification commands. It must require:

- no provider or external connectivity;
- no credentials or secrets;
- no persistence or workflow changes;
- no changes to P05, P06, Risk/Capital, P07, G1, or project-state contracts;
- focused fail-closed and immutability tests;
- a post-implementation audit; and
- confirmation that the implementation remains paper-only and read-only.

This proposal itself creates none of those permissions.

## 17. Governance conclusion

The proposed next boundary is a narrow, provider-neutral, read-only observation
contract. It can supply normalized market evidence for candidate discovery and
paper-only opportunity evaluation while preserving point-in-time provenance,
freshness, immutability, and SHA-256 integrity.

It does not create a trading path, an authorization path, an execution path, an
economic-result path, or a later-phase shortcut. Until all three separate gates
are completed, this document remains the sole deliverable and no code is
permitted.