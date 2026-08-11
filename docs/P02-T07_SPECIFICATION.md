# P02-T07 Specification

**Status:** Specification approved in principle; implementation not authorized  
**Phase:** P02 — Solana / DEX Data Intelligence  
**Official task title:** Provider-Neutral Token-Scoped Market Observation
Evidence Contract

This document formalizes the reviewed P02-T07 proposal. It defines a future
provider-neutral contract only. It does not authorize Python implementation,
tests, provider setup, network access, persistence, dependency changes,
workflow changes, commit, or push.

## 1. Problem and Architectural Purpose

P02-T06 produces a deterministic, local, read-oriented current token-universe
view from accepted token-discovery results. The repository does not yet define
the next boundary for receiving an observation about a known token and a
market subject while preserving evidence, provenance, freshness, quality, and
ordering.

P02-T01 already provides a generic `NormalizedMarketState` envelope, but it
does not define a token-scoped market-subject identity or the lifecycle and
admission rules needed for a market-observation boundary. P02-T07 therefore
defines the smallest next contract:

```text
P02-T06 current token-universe read view
    → P02-T07 token-scoped market observation evidence
    → separately specified future market-domain contracts
```

P02-T07 is an evidence-admission boundary. It is not market-state collection,
market-state aggregation, or market intelligence. It records whether a
provider-neutral observation candidate is admissible for a token currently
represented by the P02-T06 view, without interpreting price, volume, pools,
liquidity, swaps, or transaction flow.

The boundary is intended to be:

- provider-neutral;
- deterministic;
- local/in-memory;
- freshness-aware;
- provenance-aware;
- auditable and explainable;
- fail closed for uncertain input;
- safe against duplicate, contradictory, and out-of-order input; and
- free of hidden side effects.

## 2. Exact Scope

P02-T07 defines:

1. A read-only predecessor context derived from the actual P02-T06 public
   snapshot and state-digest interfaces.
2. A provider-neutral token-scoped market-observation candidate contract.
3. Deterministic identities for an observation, token, chain, market subject,
   and source.
4. Observation lifecycle semantics for first evidence and later updates.
5. Explicit freshness, provenance, quality, ordering, sequence, duplicate,
   contradiction, stale, unavailable, and resynchronization semantics.
6. An immutable accepted-evidence output.
7. An observable rejected-result output.
8. Explicit ownership of a local observation-processing context.
9. Deterministic replay and state-digest requirements.
10. A provider, security, and data-hygiene boundary.

P02-T07 does not create or replace a provider-specific adapter. It consumes
already normalized provider-neutral values at a contract boundary.

## 3. Explicit Non-Goals

The following are explicitly outside P02-T07:

- price;
- volume;
- liquidity;
- pool discovery or pool registry;
- swaps;
- transaction-flow interpretation;
- DEX or Jupiter integration;
- provider selection or provider integration;
- Solana RPC, WebSocket, or REST;
- indexers and data vendors;
- persistence, database schema, migrations, retention, or durable restart
  recovery;
- trading or execution;
- wallets, keys, signing, broadcasting, or capital allocation;
- risk, safety, eligibility, signal, opportunity, ranking, or decision engines;
- AI, ML, LLM, or narrative analysis;
- P03 or any later phase;
- dashboards, APIs, queues, brokers, or deployment infrastructure;
- network retry, reconnect, failover, or source recovery;
- market-state aggregation;
- cross-source conflict resolution by undocumented preference.

Presence in the P02-T06 token universe never means that a token is safe,
liquid, tradable, eligible, profitable, or authorized for analysis or trading.

## 4. Exact Predecessor Dependency on P02-T06

### 4.1 Actual P02-T06 public/read-only contract

The current repository exposes these relevant P02-T06 types and methods:

- `TokenUniverseEntry`
  - discovery-derived `token_identity`;
  - `chain_id`;
  - discovery identity and kind;
  - discovery reason;
  - quality and ordering status;
  - data age;
  - bounded metadata;
  - discovery provenance;
  - discovery contract version;
  - materializer contract version.
- `TokenUniverseKey`, currently represented as
  `(chain_id, token_identity)`.
- `TokenUniverseState.state_version`, which returns the deterministic state
  digest.
- `TokenUniverseState.state_digest()`, which canonicalizes owned state.
- `TokenUniverseMaterializer.snapshot()`, which returns a tuple of deep-copied
  `TokenUniverseEntry` values in canonical key order.

The public exports are available from `core.data.materialization` and are
re-exported by `core.data`. The current `snapshot()` result is a read-oriented
tuple; it does not expose mutable materializer internals.

### 4.2 How P02-T07 consumes P02-T06

P02-T07 receives an explicit read-only predecessor context containing:

- the P02-T06 snapshot tuple;
- the P02-T06 state version/digest captured with that snapshot;
- the P02-T06 materializer contract version;
- an explicit evaluation identity when the caller has one.

This wrapper is a **new proposed P02-T07 context contract**. It is not an
existing repository type and must not be treated as implemented.

The P02-T07 admission check forms the P02-T06 universe key:

```text
(chain_id, token_identity)
```

The candidate is admissible only if that key is present in the supplied
snapshot. P02-T07 may read the entry's discovery evidence and context version,
but may not modify the entry, the tuple, the `TokenUniverseState`, or the
materializer that produced the snapshot.

The P02-T06 snapshot is a point-in-time input to an evaluation. If a caller
needs a newer universe, it must supply a new explicit snapshot and state
version. P02-T07 must not refresh, rebuild, or infer the universe.

### 4.3 Compatibility constraints

P02-T07 must:

- reuse the existing `(chain_id, token_identity)` identity convention;
- preserve P02-T06 provenance and contract-version references;
- avoid adding market fields to `TokenUniverseEntry`;
- avoid changing `TokenUniverseMaterializer`;
- avoid using a database or process-global token registry;
- avoid treating P02-T06 presence as a market or safety assertion.

## 5. Proposed Market Observation Candidate Contract

The following is the proposed contract to be implemented only after separate
implementation authorization. These names and values do not currently exist
in the repository and are specification-level definitions, not claims about
existing code.

### 5.1 Required candidate fields

Each candidate must provide:

- `observation_id` or sufficient canonical material to derive one;
- `source_id`;
- `chain_id`;
- `token_identity`;
- `market_subject_id`;
- `observation_kind`;
- `observation_time`;
- `received_time`;
- `sequence`, when the source provides ordering;
- `observation_metadata`;
- `source_metadata`;
- `contract_version`;
- an explicit candidate quality status.

The evaluation additionally supplies:

- `processing_time`;
- `reference_time`;
- freshness policy;
- the P02-T06 read-only snapshot context;
- the local P02-T07 observation-processing context.

`processing_time` and `reference_time` are evaluation inputs, not values read
from the system clock.

### 5.2 Identity fields

All identity fields must be non-empty strings after validation. They must be
canonical, stable, and provider-neutral.

`market_subject_id` is intentionally an opaque but stable domain identifier.
P02-T07 does not define it as a pool, venue, pair, route, or DEX object.
Defining those meanings belongs to a later market-domain specification.

`observation_metadata` and `source_metadata` are bounded canonical mappings.
They may carry descriptive evidence but must not introduce an unapproved
semantic measurement schema.

P02-T07 does not accept a raw provider payload, SDK object, arbitrary object,
credential, or unbounded log as a candidate field.

### 5.3 Unsupported measurement fields

P02-T07 does not define fields for price, volume, liquidity, reserves,
transaction count, swap amount, buy/sell pressure, order book state, or any
other market measurement.

An implementation may reject a candidate containing an explicitly unsupported
measurement field with an `UNSUPPORTED` outcome/reason. It must not silently
interpret, normalize, aggregate, or preserve such a field as if its semantics
were approved.

## 6. Deterministic Identity Semantics

### 6.1 Source identity

`source_id` identifies the logical source at the provider-neutral boundary. It
must match the source identity supplied by the upstream adapter/orchestration
contract when one exists. P02-T07 does not resolve or rename source identities.

### 6.2 Chain identity

`chain_id` identifies the chain domain of the observation. It is required and
must be the same value used by the P02-T06 universe key. P02-T07 does not
verify chain state or contact a chain.

### 6.3 Token identity

`token_identity` is the canonical token identity used by P02-T06. P02-T07
must not invent a second token-identity scheme or normalize a provider-specific
token representation itself.

### 6.4 Market subject identity

The market subject key is:

```text
(chain_id, token_identity, market_subject_id)
```

The tuple is the minimum subject identity for local P02-T07 state. Two
observations with different chain, token, or market-subject values are
different subjects, even if their display metadata is identical.

P02-T07 does not define whether one token may have zero, one, or many market
subjects from a business perspective. It only requires that each supplied
subject be explicitly identified.

### 6.5 Observation identity

An observation identity identifies one source observation, not a subject.

The preferred identity material is:

```text
{
  "source_id": source_id,
  "source_event_id": source_event_id
}
```

when an upstream source event identity is available.

When no source event identity is available, the implementation may derive a
stable digest from canonical material containing, at minimum:

```text
{
  "source_id": source_id,
  "chain_id": chain_id,
  "token_identity": token_identity,
  "market_subject_id": market_subject_id,
  "observation_time": canonical timestamp,
  "sequence": sequence,
  "observation_metadata": canonical metadata
}
```

The exact string prefix and digest encoding are an implementation decision,
but the identity must be deterministic, collision-resistant for the contract
scope, and independent of memory address, random UUID, dictionary insertion
order, provider SDK identity, or hidden current time.

An explicit supplied `observation_id` must be checked against the canonical
identity material. An implementation must not accept one identity and silently
associate it with contradictory identity material.

## 7. Observation Lifecycle Semantics

P02-T07 defines only two accepted observation kinds:

- `OBSERVED` — first accepted evidence for a source and market subject in the
  local processing context;
- `UPDATED` — a later accepted evidence record for an already accepted source
  and market subject.

The local evidence key is:

```text
(source_id, chain_id, token_identity, market_subject_id)
```

An `OBSERVED` candidate for an already accepted key is not silently treated as
new evidence. It is rejected as duplicate or contradictory according to its
observation identity and canonical content.

An `UPDATED` candidate requires an existing accepted evidence key from the same
source and subject. An update from a source/subject with no accepted prior
evidence is rejected as `REJECTED` with a deterministic
`UPDATE_REQUIRES_PRIOR_OBSERVATION` reason.

P02-T07 does not define `REMOVED`, `DELETED`, `RESYNCED`, pool-created, or
pool-closed lifecycle events. A complete subject replacement or lifecycle
contract requires a separately approved task.

## 8. Freshness Semantics

Freshness is computed exclusively from explicit values:

```text
data_age = reference_time - observation_time
```

Rules:

1. `reference_time` must be timezone-aware.
2. `processing_time` must be timezone-aware.
3. `observation_time` must be timezone-aware.
4. `received_time` must be timezone-aware.
5. `observation_time <= received_time`.
6. `observation_time <= reference_time`.
7. A negative data age is invalid.
8. A configured `stale_after` threshold is applied only when explicitly
   supplied in the freshness policy.
9. If `data_age > stale_after`, the candidate is stale and cannot be accepted.
10. No constructor, method, validator, or digest may read the wall clock.

The existing `FreshnessPolicy` and `DataQuality.STALE` are the preferred
repository semantics to reuse. P02-T07 does not create a second freshness
policy abstraction unless a later approved implementation demonstrates that
the existing type cannot express the contract.

## 9. Provenance

Accepted evidence must preserve, directly or through a bounded immutable
reference:

- `source_id`;
- source event identity when available;
- `observation_id`;
- `chain_id`;
- `token_identity`;
- `market_subject_id`;
- observation, received, processing, and reference timestamps;
- sequence/cursor when supplied;
- observation kind;
- source metadata;
- observation metadata;
- candidate contract version;
- P02-T06 materializer contract version;
- P02-T06 snapshot state version/digest.

P02-T07 must preserve point-in-time context. A later `UPDATED` evidence result
must not rewrite the historical content of the earlier accepted result.

Provenance must be bounded and canonical. Raw unbounded provider payloads,
credentials, private keys, secrets, opaque SDK values, and arbitrary log
streams cannot cross this boundary.

## 10. Quality Semantics

### 10.1 Existing quality values to reuse

The actual repository defines `core.data.contracts.DataQuality` with these
values:

- `VALID`;
- `STALE`;
- `INVALID`;
- `INCOMPLETE`;
- `DUPLICATE`;
- `OUT_OF_ORDER`;
- `SOURCE_UNAVAILABLE`;
- `CONTRADICTORY`.

P02-T07 must reuse this enum for candidate and result quality. It must not
silently invent a second quality enum.

### 10.2 Outcomes and reason categories

The following are not currently `DataQuality` values and therefore must be
represented as proposed outcome or reason values rather than added silently to
the existing quality enum:

- `TOKEN_NOT_CURRENT`;
- `UNSUPPORTED`;
- `RESYNCHRONIZATION_REQUIRED`;
- `UPDATE_REQUIRES_PRIOR_OBSERVATION`.

The proposed P02-T07 result outcome vocabulary is:

- `OBSERVED`;
- `UPDATED`;
- `DUPLICATE`;
- `CONTRADICTORY`;
- `STALE`;
- `INVALID`;
- `INCOMPLETE`;
- `OUT_OF_ORDER`;
- `SOURCE_UNAVAILABLE`;
- `TOKEN_NOT_CURRENT`;
- `RESYNCHRONIZATION_REQUIRED`;
- `UNSUPPORTED`;
- `REJECTED`.

The final Python enum name and exact reason-code representation remain an
implementation detail, but every outcome must be machine-readable and stable.

### 10.3 Quality mapping for boundary-generated failures

Unless an existing candidate quality already provides a more specific value:

- malformed types, invalid timestamps, invalid identity, and unsupported
  values use `INVALID`;
- missing required fields or absent predecessor evidence use `INCOMPLETE`;
- stale input uses `STALE`;
- duplicate input uses `DUPLICATE`;
- contradictory input uses `CONTRADICTORY`;
- out-of-order input uses `OUT_OF_ORDER`;
- unavailable source input uses `SOURCE_UNAVAILABLE`;
- resynchronization-required input uses `INVALID` together with the
  `RESYNCHRONIZATION_REQUIRED` outcome/reason.

This mapping reuses the existing quality contract while keeping boundary
outcomes that do not belong in `DataQuality` explicit.

## 11. Ordering and Sequence Semantics

Ordering state is local to P02-T07 and keyed by source plus market subject:

```text
(source_id, chain_id, token_identity, market_subject_id)
```

For an integer sequence:

- no prior sequence means the candidate is first;
- a sequence greater than the accepted sequence is in order;
- a sequence equal to or lower than the accepted sequence is out of order;
- rejected, duplicate, contradictory, stale, unavailable, and resync-required
  candidates do not advance ordering state.

If a source provides no sequence, the candidate may be evaluated without
sequence ordering, but the absence of sequence must remain visible in
provenance. A source must not be treated as ordered merely because candidates
arrived in a particular Python collection order.

String sequence values may be preserved as provenance, consistent with the
existing `SequenceValue` type, but P02-T07 cannot compare arbitrary strings
unless an explicit, stable comparison policy is supplied. Without such a
policy, string sequence values are ordering-unknown rather than guessed.

Batch processing must use the supplied sequence order or a documented stable
ordering key. It must never depend on incidental dictionary or set iteration.

## 12. Duplicate Handling

Duplicate detection uses observation identity and canonical content:

1. Same observation identity and same canonical content produces
   `DUPLICATE` with `DataQuality.DUPLICATE`.
2. Duplicate input is observable in the returned result.
3. Duplicate input does not replace accepted evidence.
4. Duplicate input does not advance sequence state.
5. Duplicate input does not change the local state digest.
6. Duplicate input does not mutate the P02-T06 snapshot or state.

Duplicate detection must remain deterministic across replay and process
instances initialized with equivalent explicit context.

## 13. Contradiction Handling

Contradiction occurs when an identity that was previously accepted is presented
with different canonical identity material or different canonical evidence
content, or when envelope, subject, provenance, and identity fields disagree.

Contradictory input:

- produces `CONTRADICTORY` with `DataQuality.CONTRADICTORY`;
- preserves bounded evidence sufficient to explain the conflict;
- does not overwrite the previous accepted evidence;
- does not advance ordering;
- does not change the current local accepted-evidence state;
- does not choose one source or value using an undocumented preference.

P02-T07 does not define cross-source reconciliation. If two sources provide
different evidence for the same subject, both may be represented as separate
source-scoped evidence only when their identities and ordering contexts are
valid. A later task must define any authoritative merge or conflict policy.

## 14. Stale Handling

A stale candidate is observable but cannot be accepted as current evidence.

It must:

- produce `STALE` with `DataQuality.STALE`;
- preserve source, subject, timestamps, and bounded provenance when safely
  available;
- leave accepted evidence unchanged;
- leave sequence state unchanged;
- leave the local state digest unchanged;
- leave P02-T06 state unchanged.

A stale candidate must not become fresh merely because it is processed later.
Freshness is evaluated against the explicit reference time supplied for that
evaluation.

## 15. Unavailable and Resynchronization Semantics

### 15.1 Source unavailable

An upstream source-unavailable observation uses the existing
`DataQuality.SOURCE_UNAVAILABLE` value and produces a
`SOURCE_UNAVAILABLE` outcome. It is observable and never accepted as current
evidence.

P02-T07 does not perform retry, reconnect, failover, or source recovery.

### 15.2 Resynchronization required

An upstream discontinuity or explicit resynchronization requirement produces a
`RESYNCHRONIZATION_REQUIRED` outcome with `DataQuality.INVALID`, because the
repository has no separate resynchronization quality enum.

Such an input:

- does not mutate accepted evidence;
- does not advance ordering;
- does not infer a complete subject state;
- does not clear a resynchronization condition by itself;
- does not contact a provider.

A future resynchronization input would need a separately approved contract
containing complete replacement evidence, explicit subject scope, source
identity, ordering reset evidence, timestamps, provenance, and completeness
proof. P02-T07 does not authorize or define that replacement contract.

## 16. Immutable Accepted Evidence Output

The proposed accepted output is a new P02-T07 contract and is not currently
implemented. It must be immutable and contain at least:

- deterministic `observation_result_id`;
- `observation_id`;
- `source_id`;
- `chain_id`;
- `token_identity`;
- `market_subject_id`;
- accepted lifecycle kind (`OBSERVED` or `UPDATED`);
- `DataQuality.VALID`;
- ordering status and sequence;
- observation, received, processing, and reference timestamps;
- computed data age;
- bounded observation metadata;
- bounded source metadata;
- immutable provenance;
- candidate contract version;
- P02-T06 materializer contract version;
- P02-T06 snapshot state version/digest;
- local P02-T07 state version/digest after acceptance;
- an explicit `accepted = true` indicator.

Accepted evidence is not an aggregate market state. It must not contain
unapproved price, volume, liquidity, pool, swap, transaction-flow, safety,
signal, opportunity, decision, trading, or profitability fields.

An `UPDATED` result preserves the earlier evidence as historical context or
through a bounded immutable reference. It must not mutate the earlier result.

## 17. Rejected Result Semantics

Every candidate, including malformed input where safe identity fields cannot
be extracted, must produce an observable rejected result rather than silently
disappearing.

A rejected result must contain, when safely available:

- deterministic result identity, or a deterministic invalid-input identity;
- source identity;
- observation identity;
- chain, token, and market-subject identity;
- outcome;
- existing `DataQuality` value;
- one or more stable reason categories;
- explicit processing/reference times when valid;
- P02-T06 snapshot state version/digest when supplied;
- unchanged P02-T07 local state version/digest;
- `accepted = false`;
- `state_changed = false`.

Rejected results must not:

- mutate accepted evidence;
- advance ordering;
- mutate P02-T06 state;
- perform network I/O;
- retry or fail over;
- write persistence;
- trigger a trading, wallet, or autonomous action.

## 18. Deterministic Replay Requirements

For identical candidate inputs, identical P02-T06 snapshot/context, identical
freshness policy, identical ordering context, and identical explicit
processing/reference times, replay must produce:

- identical result outcomes;
- identical quality values;
- identical reason categories;
- identical accepted evidence;
- identical provenance;
- identical mutation flags;
- identical local state digest.

The implementation must not depend on:

- current time;
- random UUIDs;
- memory addresses;
- process hash randomization;
- dictionary or set insertion order;
- provider SDK object identity;
- network state;
- hidden process-global mutable state.

Canonical serialization must define stable ordering and explicit treatment of
absent values. If a deterministic identity or digest cannot be computed, the
candidate must be rejected rather than approximated.

## 19. Explicit State Ownership

P02-T07 may own only one explicit local observation-processing context. That
context may contain:

- accepted evidence keyed by source and market subject;
- accepted observation identity fingerprints;
- latest accepted integer sequence per source and subject;
- a local resynchronization-required set;
- the P02-T07 contract version;
- an evaluation identity;
- deterministic state-digest inputs.

P02-T07 must not own or mutate:

- `TokenUniverseState`;
- `TokenUniverseEntry`;
- P02-T06 ordering state;
- P02-T06 discovery fingerprints;
- source adapter lifecycle;
- orchestration source health;
- database or durable state;
- process-global state.

The supplied P02-T06 snapshot is read-only input. A new snapshot must be
explicitly supplied by the caller; P02-T07 must never mutate or refresh it.

## 20. Provider Boundary

P02-T07 begins after provider-neutral adaptation and validation. It does not
call or implement a provider.

The existing repository provides:

- `ProviderNeutralAdapter` in `core.data.contracts`;
- `ProviderNeutralSourceAdapter` in `core.data.adapters`;
- `AdapterObservation` and orchestration contracts in
  `core.data.orchestration`;
- discovery conversion through `DiscoveryToOrchestrationBoundary`.

Those interfaces establish how future external values can become
provider-neutral observations. P02-T07 must consume a dedicated
provider-neutral market-observation candidate rather than accept a provider
SDK type or raw provider mapping.

No provider, network, credential, endpoint, retry, rate limit, or failover
policy is selected by this specification.

## 21. Security and Data-Hygiene Boundary

P02-T07 must not accept, store, emit, or log:

- secrets;
- API keys;
- credentials;
- access tokens;
- private keys;
- seed phrases;
- wallet signing material;
- raw unbounded provider payloads;
- opaque SDK objects;
- memory addresses;
- unbounded source logs.

Metadata and provenance must be bounded, canonical, and provider-neutral.
Inputs with unsupported values must be rejected. Error reasons must be
explainable without echoing sensitive data.

P02-T07 has no authorization, wallet, trading, or execution capability.

## 22. Proposed Files and Implementation Constraints

This specification authorizes no implementation. If a separate implementation
task is approved later, it must name exact files before work starts.

### Proposed implementation files

The likely narrow implementation boundary is:

- `core/data/market_observations.py`
- `tests/test_market_observations.py`

`core/data/__init__.py` may be modified only if public exports are explicitly
approved.

These are proposals for a future implementation, not authorized changes.

### Files not to modify for P02-T07 implementation

P02-T07 must not modify:

- `PROJECT_STATE.md`;
- `docs/MASTER_BLUEPRINT.md`;
- `docs/DATA_PIPELINE.md`;
- `docs/P02-T06_SPECIFICATION.md`;
- `docs/CHANGELOG.md`;
- `core/data/materialization.py`;
- `core/data/discovery.py`;
- `core/data/discovery_orchestration.py`;
- `core/data/contracts.py`;
- `core/data/adapters.py`;
- existing P02-T06 tests;
- backend runtime, configuration, workflows, or deployment files;
- database schemas, migrations, repositories, or persistence configuration;
- dependency manifests or lockfiles;
- environment files or secrets;
- P03 or later implementation/specification files.

### Implementation constraints

Any separately authorized implementation must remain:

- provider-neutral;
- deterministic;
- local/in-memory;
- free of network calls;
- free of persistence;
- free of external side effects;
- free of hidden clocks;
- free of credentials and provider SDK objects.

## 23. Test and Acceptance Criteria

### 23.1 Required deterministic test cases

If implementation is authorized, tests must cover at least:

1. A valid `OBSERVED` candidate for a token present in a P02-T06 snapshot is
   accepted.
2. A valid `UPDATED` candidate with a newer accepted sequence is accepted.
3. An `UPDATED` candidate without a prior accepted same-source subject is
   rejected.
4. A token absent from the P02-T06 snapshot is rejected as
   `TOKEN_NOT_CURRENT`.
5. Chain/token identity mismatch is rejected.
6. Empty or invalid market-subject identity is rejected.
7. Duplicate identity with identical canonical content is observable and does
   not mutate state.
8. Same identity with contradictory content is observable and does not
   overwrite accepted evidence.
9. Equal or lower integer sequence is rejected as out of order.
10. Missing sequence is handled according to the explicit no-ordering policy,
    never incidental arrival order.
11. Stale input is rejected and does not change accepted evidence.
12. Negative data age and invalid timestamp relationships are rejected.
13. Source-unavailable input is observable and does not mutate accepted state.
14. Resynchronization-required input does not mutate state or clear the
    condition.
15. Unsupported observation kind and unsupported measurement fields are
    rejected.
16. Provider-specific objects, opaque values, and uncanonical metadata cannot
    cross the boundary.
17. Accepted evidence preserves P02-T06 snapshot version and provenance.
18. Rejected input leaves every P02-T07-owned state component unchanged.
19. Identical inputs and explicit contexts produce identical result and state
    digests on replay.
20. Same token identity on different chains remains a different subject.
21. Multiple sources do not get merged by an undocumented preference.
22. No test uses a live network, database, provider SDK, credential, or
    external service.
23. Existing P02-T01 through P02-T06 tests remain passing.

### 23.2 Objectively testable acceptance criteria

P02-T07 can be accepted for a later implementation review only if:

1. The implementation consumes the actual P02-T06 snapshot contract and does
   not mutate P02-T06 state.
2. The candidate and result contracts are provider-neutral and bounded.
3. Observation, token, chain, market-subject, and source identities are
   deterministic.
4. All required evaluation times and freshness policies are explicit.
5. No hidden wall-clock read occurs.
6. Existing `DataQuality` values are reused; new concepts are represented as
   explicit outcomes/reasons rather than silently added quality values.
7. Accepted evidence is immutable and preserves provenance, contract versions,
   and P02-T06 snapshot state version.
8. Duplicate, contradictory, stale, out-of-order, unavailable, invalid,
   incomplete, and resynchronization-required input fails closed.
9. Rejected input does not mutate either P02-T07 accepted state or P02-T06
   state.
10. Deterministic replay produces identical results and state digests.
11. No price, volume, liquidity, pool, swap, transaction-flow, safety,
    signal, opportunity, decision, AI, trading, or execution behavior exists.
12. No provider, RPC, WebSocket, REST, database, persistence, dependency, or
    workflow behavior is introduced.
13. Focused tests, P02 regression tests, compilation, and diff checks pass.
14. The implementation does not change governance files unless separately
    approved.

Passing these criteria would be a technical verification gate only. It would
not authorize provider integration, persistence, market measurements, or any
later phase.

## 24. Dependency Matrix Based on Actual Repository Interfaces

| Existing interface/file | Actual role | P02-T07 relationship | Modification allowed? |
| --- | --- | --- | --- |
| `core/data/contracts.py` | Defines `DataQuality`, `FreshnessPolicy`, `SequenceValue`, `RawEvent`, `NormalizedMarketState`, and generic normalization semantics | Reuse quality, freshness, and sequence conventions; do not replace `NormalizedMarketState` | No |
| `core/data/discovery.py` | Defines discovery records/results and discovery provenance | Indirect predecessor evidence; P02-T07 consumes the resulting P02-T06 view, not raw discovery observations | No |
| `core/data/discovery_orchestration.py` | Validates accepted discovery results and converts them to existing orchestration observations | Upstream boundary already completed; no direct provider implementation is needed | No |
| `core/data/materialization.py` | Defines `TokenUniverseEntry`, `TokenUniverseState`, `MaterializationContext`, `MaterializationResult`, and `TokenUniverseMaterializer.snapshot()` | Direct predecessor; supply a read-only snapshot and explicit state digest/version | No |
| `core/data/adapters.py` | Defines provider-neutral adapter identity/capability/lifecycle and `ProviderNeutralSourceAdapter` | Establishes upstream adapter boundary; P02-T07 does not implement an adapter | No |
| `core/data/orchestration.py` | Defines adapter observations, ordering, ingestion results, source health, and publication boundary | Provides existing source/ordering concepts; P02-T07 does not re-run orchestration | No |
| `core/data/__init__.py` | Re-exports current data contracts | May later export approved P02-T07 contracts only if separately authorized | Not for specification-only work |
| `tests/test_materialization.py` | Verifies current P02-T06 materialization behavior | Must remain passing; P02-T07 must not alter it | No |
| `PROJECT_STATE.md` | Authoritative project status and authorization state | Currently keeps P02-T07 implementation unauthorized | No |
| `docs/MASTER_BLUEPRINT.md` | Phase map and architectural gates | Lists P02-T07 and later as not started/not authorized | No |
| `docs/DATA_PIPELINE.md` | Data freshness, provenance, quality, ordering, and failure principles | Governing compatibility requirements | No |

P02-T07 has no dependency on P03+ interfaces. It does not require a new
provider, database, migration, credential, dependency, workflow, or external
service.

## 25. Future Boundary

P02-T07 intentionally stops before semantic market-domain contracts.

A later, separately approved P02 market-domain task may define one or more of:

- price observations and price-state semantics;
- volume observations and volume-state semantics;
- pool discovery or pool identity;
- liquidity and reserve state;
- swap events;
- transaction-flow interpretation;
- market-state aggregation.

The repository does not currently define which future task owns those
semantics. This specification does not assign a task number, create a roadmap
entry, or pre-authorize any of them.

Any future market-domain task must consume P02-T07 evidence without weakening
its provenance, freshness, ordering, contradiction, or fail-closed rules.
Features, signals, opportunity logic, and safety intelligence remain governed
by their later phase boundaries.

## 26. Open Decisions

The following decisions remain open because they cannot be determined from the
current repository without inventing semantics:

1. **Final Python type and module names.** The repository has no P02-T07
   implementation module or public type names yet.
2. **Exact observation identity string format.** The canonical material is
   constrained above, but the prefix and digest encoding are open.
3. **Market-subject domain meaning.** It is not yet defined whether a subject
   represents a pool, venue, pair, route, or another market entity.
4. **Whether a future market subject may relate to multiple tokens.** This
   task is intentionally token-scoped and does not define pair or pool
   semantics.
5. **Cross-source reconciliation.** No source-authority or merge policy exists.
6. **String-sequence ordering.** The current repository permits string
   `SequenceValue` values but does not define a safe comparison policy.
7. **Formal resynchronization replacement contract.** Existing orchestration
   and discovery boundaries expose resynchronization-required states, but no
   complete market-observation replacement-set contract exists.
8. **Retention and durable replay.** P02-T07 is local/in-memory only; no
   restart or database policy is approved.
9. **Whether generic bounded metadata may later be specialized.** Price,
   volume, liquidity, pool, swap, and transaction-flow metadata must not be
   interpreted until separately specified.
10. **Future task ownership.** The current blueprint does not assign a task
    number for market-domain semantics after P02-T07.
11. **State-digest serialization details.** The implementation must be
    canonical and deterministic, but the exact field encoding is open until
    implementation review.
12. **Snapshot staleness policy.** P02-T07 must consume the explicit P02-T06
    snapshot supplied for evaluation, but a separate policy for how old that
    predecessor snapshot may be is not currently defined. It must not be
    invented here.

Open decisions must be resolved in a reviewed implementation specification or
follow-up task before the affected behavior is implemented.

## 27. Authorization and Verification Gate

This document is specification-only. It authorizes no:

- source-code change;
- test change;
- dependency installation;
- workflow change;
- provider or network access;
- persistence change;
- environment or secret change;
- commit;
- push.

Before implementation can be separately considered, reviewers must confirm:

1. The exact open decisions needed for the selected implementation are closed.
2. The implementation consumes the actual P02-T06 read-only contract.
3. P02-T06 behavior and files remain unchanged.
4. The candidate, output, provenance, quality, ordering, rejection, and state
   ownership contracts are covered by deterministic tests.
5. No measurement semantics have entered P02-T07.
6. No provider, network, persistence, trading, safety, intelligence, or P03+
   behavior has entered the boundary.
7. Existing P01/P02 regression and documentation governance remain intact.

Implementation requires a separately authorized task that names the exact
files and permits the relevant tests. P02-T07 implementation is not authorized
by this specification alone.