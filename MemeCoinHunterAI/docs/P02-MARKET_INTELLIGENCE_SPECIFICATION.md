# P02 — Market Intelligence Boundary Specification

**Status:** Specification authored; implementation not authorized  
**Phase:** P02 — Solana / DEX Data Intelligence  
**Official task title:** Provider-Neutral Market Intelligence Boundary  
**Contract version:** `p02-market-intelligence-v1`

This document defines a narrow provider-neutral contract between the completed
P02-T08 market-state layer and future market-intelligence/provider layers. It
does not authorize implementation, provider setup, network access, persistence,
dependency changes, workflow changes, commit, or push.

## 1. Purpose

The Market Intelligence Boundary defines how future market-intelligence
observations can be represented, traced, validated, and consumed after
P02-T08 has materialized current market state.

The intended progression is:

```text
P02-T06 token universe
    → P02-T07 accepted token-scoped observation evidence
    → P02-T08 current market state
    → Market Intelligence Boundary
    → future P03/P04 and later consumers
```

This boundary owns representation and admission of already normalized,
provider-neutral intelligence observations. It does not collect data, calculate
market measurements, aggregate sources, generate signals, score opportunities,
evaluate risk, or make decisions.

The boundary exists to prevent future intelligence data from bypassing
provenance, identity, freshness, ordering, immutability, and fail-closed
requirements established by P02-T06, P02-T07, and P02-T08.

## 2. Relationship to P02-T08

The direct relationship is:

```text
P02-T08 current market state
    → Market Intelligence observation representation
```

The Market Intelligence Boundary may consume a read-only reference to a
P02-T08 current state entry or an explicit P02-T08 state snapshot reference.
It must preserve the P02-T08 state version and digest that formed the
evaluation context.

It must not:

- repeat P02-T07 candidate admission;
- accept a raw provider payload instead of a normalized contract value;
- rebuild or refresh P02-T08 state;
- mutate P02-T08 state or context;
- mutate P02-T07 accepted evidence or processing context;
- mutate P02-T06 token-universe state;
- reinterpret P02-T08 generic metadata as a measurement;
- treat P02-T08 state presence as safety, liquidity, tradability, or
  authorization.

P02-T07 remains the authority for observation-evidence admission. P02-T08
remains the authority for the local current market-state projection. This
boundary adds a separate intelligence-observation representation and does not
replace either predecessor.

## 3. Exact Boundary and Non-Goals

The boundary begins with:

```text
accepted P02-T08 market-state reference
    + provider-neutral intelligence observation value
```

It produces:

```text
immutable provider-neutral intelligence observation result
```

The result may be accepted as a representation-layer observation or rejected
with an observable reason. It is not a finalized market state, aggregated
market view, signal, opportunity, risk assessment, or decision.

The following are outside this boundary:

- data collection and source transport;
- provider selection;
- external API or SDK behavior;
- market-state aggregation;
- cross-source reconciliation;
- live monitoring;
- feature calculation;
- signal generation;
- opportunity scoring;
- ranking;
- prediction;
- confidence estimation;
- risk scoring;
- eligibility;
- trade decisions;
- execution;
- dashboard or API behavior;
- persistence or durable replay.

## 4. Canonical Identity

The canonical subject identity reuses the existing P02 concepts:

```text
(source_id, chain_id, token_identity, market_subject_id)
```

The intelligence-observation identity is:

```text
(
    source_id,
    chain_id,
    token_identity,
    market_subject_id,
    intelligence_category,
    observation_id
)
```

Where:

- `source_id` identifies the logical upstream source;
- `chain_id` identifies the chain domain;
- `token_identity` is the canonical P02 token identity;
- `market_subject_id` is the opaque subject identity established upstream;
- `intelligence_category` identifies the representation category; and
- `observation_id` identifies the individual observation within that category.

No second token-identity scheme is introduced. The boundary must not derive
identity from display names, symbols, provider object identity, or arbitrary
payload fields.

The category is part of identity so that distinct future observation types do
not silently overwrite one another. A category does not, by itself, define
measurement semantics.

## 5. Intelligence Observation Model

The future provider-neutral observation representation should contain only
explicit contract fields:

- canonical identity from Section 4;
- `intelligence_category`;
- an immutable category-specific value representation;
- observation and received timestamps;
- explicit reference/evaluation timestamp when required by the contract;
- sequence or cursor when supplied;
- ordering status;
- freshness metadata;
- source and observation provenance;
- upstream P02-T08 contract version;
- upstream P02-T08 state version and digest;
- this boundary's contract version;
- deterministic observation fingerprint;
- explicit quality and acceptance state.

The value representation must be bounded, canonical, and provider-neutral.
It may be a typed scalar, bounded immutable mapping, or bounded immutable
sequence only when the separately approved category contract defines that
shape. An implementation must not infer a type or unit from an arbitrary
provider payload.

The representation must be able to name future categories such as:

```text
PRICE
VOLUME
LIQUIDITY
POOL_STATE
SWAP_FLOW
TRANSACTION_FLOW
FRESHNESS
STREAM_HEALTH
```

These categories are reserved representation categories only in this
specification. This document does not define their fields, units, formulas,
normalization, calculations, or source requirements. A category-specific
measurement contract must be separately specified and approved before that
category is implemented.

## 6. Observation, Measurement, State, and Aggregation

These concepts remain separate:

### Observation

One bounded, timestamped, provenance-preserving representation received at
this boundary. It says what was observed under an explicit contract context.

### Measurement

A category-specific semantic value, such as a price or volume measurement.
Measurement meaning, units, validation, and calculation require a separate
approved category contract. This boundary does not calculate measurements.

### State

The current representation selected from admissible observations under an
explicit local evaluation context. This boundary does not replace P02-T08
market-state materialization and does not create a combined market state.

### Aggregation

Any combination, reduction, reconciliation, interpolation, derivation,
consensus, or source preference across observations. Aggregation is a future
boundary and is not performed here.

No implementation may turn a generic category value into a semantic price,
volume, liquidity, pool, swap, or transaction-flow result merely because the
category name suggests one.

## 7. Upstream Contract and Input Requirements

The input must include an explicit P02-T08 reference containing, at minimum:

- source, chain, token, and market-subject identity;
- P02-T08 contract version;
- P02-T08 state version;
- P02-T08 state digest;
- the current-state entry or an immutable equivalent reference;
- evaluation identity when one exists.

The intelligence observation must be supplied as a provider-neutral value, not
as a raw provider payload, SDK object, arbitrary object, credential, or
unbounded log.

The input must be accepted only when:

1. the upstream state reference is explicit and internally consistent;
2. all identity fields are non-empty and canonical;
3. the category is explicitly supported by an approved category contract;
4. the observation value conforms to that category contract;
5. timestamps and data age are explicit and valid when required;
6. provenance is bounded and internally consistent;
7. quality is admissible for representation as current intelligence; and
8. a deterministic fingerprint can be computed.

This boundary may reject an unapproved category as `UNSUPPORTED`. It must not
silently preserve it as an opaque measurement.

## 8. Provenance

Every represented observation must preserve sufficient provenance to establish
what upstream state was known and where the observation came from:

- `source_id`;
- source event identity when supplied;
- observation identity;
- chain identity;
- token identity;
- market-subject identity;
- intelligence category;
- observation timestamp;
- received timestamp;
- explicit evaluation/reference timestamp when supplied;
- sequence or cursor;
- ordering status;
- bounded source metadata;
- bounded observation metadata/value representation;
- P02-T08 contract version;
- P02-T08 state version and digest;
- this boundary's contract version;
- evaluation identity.

An update must not rewrite the historical provenance of a previously
represented observation. A current projection may replace an earlier current
projection only within the local state owned by this boundary and only under
the explicit ordering and lifecycle rules of an approved implementation.

Provenance is evidence, not a source-authority decision. The boundary must not
discard source identity or choose an authoritative source.

## 9. Determinism and Canonicalization

Equivalent input values and equivalent explicit evaluation contexts must
produce equivalent:

- observation identities;
- fingerprints;
- accepted/rejected outcomes;
- quality and reason categories;
- provenance;
- mutation flags;
- state version and digest;
- replay results.

The implementation must not depend on:

- wall-clock time;
- random UUIDs;
- memory addresses;
- object identity;
- process-global mutable state;
- network state;
- provider SDK identity;
- filesystem order;
- dictionary or set insertion order;
- unordered serialization.

Canonical serialization must define stable ordering for mappings and state
keys, explicit treatment of absent values, stable enum representation, and
stable timestamp representation. If canonicalization or fingerprinting cannot
be completed safely, the observation must be rejected rather than approximated.

## 10. Immutability

Accepted observation values, provenance, category values, nested metadata,
and public result values must be immutable at the public boundary.

The local context may be mutable only because it is explicitly owned by one
processor/materializer instance. Public snapshots must not expose mutable
internal dictionaries, sets, or references that can mutate accepted state.

An accepted observation must not be changed in place after admission. A later
observation may produce a new immutable representation, but it must not alter
the earlier object or its provenance.

## 11. Ordering

Ordering is represented only by explicit upstream values:

- `sequence` or cursor when supplied;
- `ordering_status`;
- observation and received timestamps;
- explicit replay order supplied by the caller.

The boundary must preserve ordering metadata and must not invent network,
block, slot, offset, or provider-specific ordering semantics.

Integer sequences may be compared only under an explicit approved contract.
String cursors must not be compared unless a stable comparison policy is
separately defined. Missing sequence remains ordering-unknown.

Incidental arrival order is not evidence of source order. A batch must process
the explicitly supplied sequence in its explicit order. Rejected observations
must not advance local ordering state.

## 12. Duplicate Handling

Duplicate handling uses canonical identity and canonical observation content.

Equivalent input with the same canonical identity and content must produce an
observable duplicate outcome, preserve the existing represented observation,
and leave local state and digest unchanged.

Duplicate detection must be deterministic across equivalent processor
contexts. Metadata insertion order must not affect equivalence.

An observation with a new identity is not automatically a duplicate, even when
its display metadata is equal.

## 13. Contradiction Handling

Contradiction occurs when:

- the same canonical observation identity is associated with different
  canonical category content;
- identity fields disagree with provenance or upstream state reference; or
- the explicit category contract is violated in a way that makes the
  observation's meaning uncertain.

Contradictory input must:

- produce an observable contradictory outcome;
- preserve the existing represented observation;
- leave ordering state unchanged;
- leave the local digest unchanged;
- avoid selecting one value by undocumented source or arrival preference.

Different sources remain source-scoped observations. Cross-source conflict
resolution is not defined here.

## 14. Freshness Semantics

Freshness is represented as explicit metadata and contract evidence only.

Where timestamps are required, the category contract must define the
relationship between observation time, received time, reference time, and
data age. This boundary must preserve those values and must not read the wall
clock.

This boundary does not:

- run live freshness evaluation;
- monitor aging observations;
- refresh stale values;
- schedule expiration;
- trigger source recovery;
- infer freshness from process time.

An observation that is explicitly stale, unavailable, invalid, or otherwise
inadmissible must not silently become current intelligence. Re-evaluation
against a new reference time requires a separately approved contract.

## 15. Stream Health Representation

`STREAM_HEALTH` is a future representation category, not a live monitor.

The boundary may eventually represent an explicit provider-neutral health
observation containing bounded status, timestamp, source identity, sequence
information, and reason categories under a separately approved category
contract.

This specification does not define health states, thresholds, recovery
criteria, or monitoring behavior. It does not authorize:

- health polling;
- retry loops;
- reconnect;
- failover;
- autonomous recovery;
- source lifecycle mutation;
- provider health APIs.

Health representation must not be confused with transport control or source
recovery.

## 16. Provider Neutrality and Future Adapters

Future provider adapters connect before this boundary:

```text
provider SDK/payload
    → separately specified adapter
    → provider-neutral normalized intelligence observation
    → Market Intelligence Boundary
```

Adapters must translate provider-specific values into approved core contracts.
Provider-specific types, SDK objects, endpoints, credentials, retry policies,
and transport errors must not leak into this boundary.

This specification explicitly prohibits:

- Solana RPC implementation;
- DEX implementation;
- Jupiter implementation;
- Binance implementation;
- provider SDK dependencies;
- WebSockets;
- REST clients;
- indexers;
- network calls;
- endpoint configuration;
- credentials and secrets.

## 17. Future Aggregation Boundary

Aggregation belongs after individual observations have been represented and
validated:

```text
individual intelligence observations
    → separately specified aggregation boundary
    → aggregated intelligence state
```

Future aggregation may define source comparison, time-window reduction,
derived features, consensus, conflict resolution, or category-specific state.
None of those semantics are defined here.

This boundary must not:

- merge multiple sources;
- choose an authoritative source;
- calculate consensus;
- average or sum values;
- interpolate missing observations;
- derive features;
- reconcile contradictory sources;
- calculate a market state from category observations.

## 18. State Ownership

The Market Intelligence Boundary may own only its explicitly defined local
representation context, containing at most:

- contract version;
- evaluation identity;
- immutable represented observations or current projections;
- canonical observation fingerprints;
- explicit local ordering state when approved;
- deterministic digest inputs.

It must not own or mutate:

- P02-T06 `TokenUniverseState`;
- P02-T06 materialization state;
- P02-T07 `MarketObservationContext`;
- accepted P02-T07 evidence;
- P02-T08 `MarketStateContext`;
- P02-T08 current state;
- provider or adapter lifecycle;
- orchestration source health;
- database, cache, queue, or durable state;
- process-global state.

Rejected observations must not mutate any owned state. Accepted observations
must not be written back into upstream contexts.

## 19. Fail-Closed Behavior

The boundary must fail closed for:

- invalid or empty identity;
- missing or inconsistent P02-T08 reference;
- unsupported category;
- incomplete observation;
- invalid timestamp or freshness relationship;
- invalid sequence or ordering metadata;
- duplicate observation;
- contradictory content;
- stale or unavailable input;
- unsupported or opaque value;
- unbounded metadata;
- sensitive data;
- untrusted provider object;
- uncomputable canonical fingerprint or digest.

Every safely representable rejection must be observable with:

- deterministic result identity;
- available subject identity;
- outcome;
- quality or rejection category;
- stable reason category;
- unchanged predecessor/local state version and digest;
- `accepted = false`;
- `state_changed = false`.

No rejection may trigger network I/O, retry, persistence, recovery, queueing,
trading, signing, execution, or any other external side effect.

## 20. Error Semantics

The implementation should expose stable conceptual categories without
prematurely fixing Python names:

- `INVALID` — malformed or internally inconsistent input;
- `INCOMPLETE` — required contract material is absent;
- `UNSUPPORTED` — category, value, or representation is not approved;
- `STALE` — explicit freshness policy marks the input inadmissible;
- `UNAVAILABLE` — upstream source or evidence is explicitly unavailable;
- `DUPLICATE` — equivalent identity and content already represented;
- `CONTRADICTORY` — same identity conflicts with represented content;
- `OUT_OF_ORDER` — explicit comparable ordering is inadmissible;
- `REJECTED` — fail-closed rejection without a more specific category.

Existing repository quality semantics should be reused where applicable. A
future implementation must not silently add a new global quality enum.

## 21. Canonical Digest and Versioning

The boundary must expose a deterministic contract version and local state
digest.

Digest material must include, at minimum:

- this boundary's contract version;
- evaluation identity;
- canonical represented observation keys;
- canonical observation content;
- provenance and P02-T08 state references;
- accepted fingerprints;
- explicitly owned ordering state.

Digest material must exclude:

- rejected input;
- transient exception text;
- wall-clock values not supplied as contract inputs;
- object identity;
- insertion order;
- secrets or credentials;
- hidden process state.

The empty context must have a stable digest. Any rejected or duplicate input
must leave the digest unchanged. A digest that cannot be computed
deterministically requires rejection.

Contract version changes must be explicit and must not be inferred from
provider SDK versions or runtime environment.

## 22. Replay

For identical ordered observations, identical P02-T08 references, identical
category contracts, identical local context, and identical explicit
evaluation context, replay must produce identical:

- observations;
- outcomes;
- reason categories;
- provenance;
- acceptance and mutation flags;
- state version;
- state digest.

Replay is local and in-memory for this boundary. It does not authorize
persistence, database snapshots, durable retention, restart recovery, or
historical backfill.

## 23. Future Decision-Engine Boundary

This boundary must not perform or authorize:

- signal generation;
- opportunity scoring;
- ranking;
- prediction;
- confidence calculation;
- risk scoring;
- eligibility;
- trade decisions;
- capital allocation;
- execution requests.

Those responsibilities belong to later intelligence, risk, opportunity, and
decision boundaries. Market-intelligence representation is evidence for later
consumers, not a decision.

## 24. Dashboard and Application Boundary

This specification does not implement:

- dashboards;
- APIs;
- UI components;
- application routes;
- background workers;
- presentation models;
- deployment infrastructure.

The future dashboard/application layer may consume finalized intelligence
through a separately specified read boundary. It must not be introduced here.

## 25. Persistence Boundary

This boundary is local and non-durable. It does not implement or require:

- PostgreSQL;
- Redis;
- queues;
- brokers;
- cache services;
- filesystem persistence;
- migrations;
- retention;
- durable snapshots;
- restart recovery.

Any durable representation requires a separate persistence specification and
must preserve the same provenance and deterministic replay requirements.

## 26. Security Boundary

The boundary must not accept, store, emit, or log:

- wallet material;
- private keys;
- seed phrases;
- signing material;
- API keys;
- credentials;
- access tokens;
- raw secret-bearing payloads;
- executable or opaque provider values.

Metadata and value representations must be bounded, canonical, provider
neutral, and immutable. Rejection reasons must explain the category of failure
without echoing sensitive values.

No observation represented here grants permission to trade or execute.

## 27. Testing Strategy for Future Implementation

A separately authorized implementation must test at least:

1. empty input and stable empty digest;
2. valid first observation;
3. valid update under explicit ordering;
4. duplicate observation;
5. contradictory observation;
6. invalid identity;
7. missing P02-T08 state reference;
8. unsupported category;
9. incomplete observation;
10. invalid timestamp or freshness relationship;
11. explicit ordering and unknown ordering behavior;
12. provenance preservation;
13. deterministic fingerprint, version, and digest;
14. deterministic replay;
15. immutable observation, metadata, and result outputs;
16. upstream P02-T06/P02-T07/P02-T08 non-mutation;
17. provider-neutral value validation;
18. rejection preserving local state and digest;
19. multiple sources remaining separate;
20. no aggregation or measurement calculation;
21. stream-health representation without monitoring;
22. absence of network, provider, persistence, wallet, and decision behavior.

Tests must use explicit local fixtures and must not contact providers, networks,
databases, queues, or external services.

## 28. Allowed Future Implementation Files

If a later implementation is separately authorized, the narrow recommended
boundary is:

```text
core/data/market_intelligence.py
core/data/__init__.py
tests/test_market_intelligence.py
```

This recommendation does not create those files or authorize their
modification. Existing P02-T06, P02-T07, and P02-T08 implementation files
must remain unchanged unless a separately approved task explicitly says
otherwise.

## 29. Explicit Prohibited Scope

This specification must not introduce:

- Solana RPC;
- DEX, Jupiter, or Binance integrations;
- provider SDKs;
- network calls;
- indexers;
- WebSockets or REST clients;
- databases, Redis, queues, brokers, caches, or persistence;
- credentials, wallets, private keys, signing, or broadcasting;
- trading, execution, capital allocation, or paper execution;
- AI, ML, LLM, narrative analysis, or multi-agent architecture;
- signal generation;
- opportunity scoring;
- ranking;
- prediction;
- confidence;
- risk scoring;
- eligibility;
- decision logic;
- dashboards, APIs, UI, or workers;
- retries, failover, health monitoring, or autonomous recovery;
- cross-source reconciliation or aggregation;
- semantic price, volume, liquidity, pool, swap, or transaction-flow
  calculations;
- P03 or later phase behavior.

The boundary must remain a narrow representation contract, not a generic
crypto data model.

## 30. Open Architectural Decisions

The following decisions remain open and must not be invented here:

1. Exact category-specific schemas for price, volume, liquidity, pool state,
   swap flow, transaction flow, freshness, and stream health.
2. Units, normalization, precision, and validation rules for future
   measurements.
3. Whether category values are scalar, structured, or versioned by category.
4. Cross-source authority, reconciliation, and consensus policy.
5. Aggregation windows, derived features, and current-state replacement rules.
6. Stream-health states, thresholds, and recovery semantics.
7. Durable storage, retention, restart recovery, and historical replay.
8. Provider adapter ownership and transport contracts.
9. Final Python type names and public export details.
10. Ownership of future P03 safety, P04 signal, opportunity, and decision
    consumers.

Each open decision requires a separately reviewed specification or
implementation authorization before affected behavior is introduced.

## 31. Relationship to Roadmap

The intended progression is:

```text
P02-T06
    → P02-T07
    → P02-T08
    → Market Intelligence Boundary
    → P03 Application Foundation
    → Dashboard/Application layer
    → later Decision/Risk/Opportunity systems
```

This document does not assign the boundary a fabricated `T09` number. The
official name is **Market Intelligence Boundary** until the project governance
documents assign a later task identity.

The boundary remains gated by explicit review and authorization. Authoring
this specification does not authorize implementation.

## 32. Authorization and Verification Gate

Before implementation, a separate authorization must name:

- the approved implementation task;
- the exact implementation and test files;
- closed category decisions required for that task;
- the verification commands;
- the reviewer-approved baseline.

Until that authorization exists, do not:

- create implementation files;
- create or modify tests;
- modify P02-T06, P02-T07, or P02-T08 implementation;
- modify project-control or governance documents;
- install dependencies;
- change configuration or workflows;
- access providers or networks;
- commit; or
- push.
