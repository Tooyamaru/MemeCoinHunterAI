# P02-T06 Specification

## 1. Purpose

P02-T06 defines a provider-neutral token-universe state/materialization
boundary. Its purpose is to turn accepted, current, and valid token-discovery
records into a deterministic read-oriented view of the current known token
universe.

This is a contract and architectural boundary only. It does not connect to a
provider, fetch data, persist data, collect market state, score tokens, or
authorize any action.

The boundary must make the following distinction explicit:

```text
accepted discovery result
    → current token-universe materialization
    → read-only universe snapshot
```

The materialized view is an in-memory or otherwise local contract result for
the approved implementation. It is not a database-backed token registry and
is not an authoritative statement about on-chain existence, safety, liquidity,
tradability, or investment quality.

## 2. Why This Is The Next Boundary

P02-T01 defines canonical raw-event, normalized-state, freshness, quality,
ordering, and provenance semantics. P02-T02 defines provider-neutral
observation orchestration and publication. P02-T03 defines the source-adapter
boundary. P02-T04 defines token-discovery observations and records. P02-T05
validates accepted discovery output and converts it into the existing
orchestration publication contract.

The completed sequence has therefore established how an observation becomes an
accepted discovery record, but it has not defined how accepted discovery
records are assembled into a current token-universe view for read-oriented
downstream consumers. P02-T06 is the smallest boundary that closes that gap
without selecting a data source or beginning market intelligence.

The recommendation is based on the following principles already present in the
repository:

- Data flows from the data layer toward intelligence and later consumers.
- Discovery is separate from market-state collection.
- Currentness, freshness, ordering, quality, and provenance must remain
  observable.
- Invalid, stale, duplicate, contradictory, incomplete, unavailable, or
  resynchronization-required information must fail closed.
- Equivalent inputs and explicit reference context must produce equivalent
  results.
- The system is paper-first, capital-protective, evidence-driven, auditable,
  and provider-neutral.

### Candidate A — Provider-neutral normalized discovery/state publication

**Evidence supporting it**

- P02-T01 requires normalized, provenance-preserving state.
- P02-T02 already defines provider-neutral observation publication.
- P02-T04 already publishes `DiscoveryResult` values and distinguishes
  accepted/current records from rejected outcomes.
- P02-T05 explicitly forwards accepted discovery into the existing
  orchestration input and publication contract.

**Evidence against it**

- The publication boundary is already defined by P02-T02.
- P02-T05 already implements the discovery-to-orchestration conversion and
  reuses that publisher protocol.
- Defining A as P02-T06 would duplicate the completed P02-T05 responsibility
  rather than create the next distinct boundary.

**Phase-boundary assessment**

It does not inherently violate P02 boundaries, but repeating it would create
architectural overlap and unclear ownership.

**Provider/network/persistence concerns**

The provider-neutral form introduces none. A transport-backed form would
introduce concerns that are explicitly outside this specification.

**Appropriate for P02-T06**

No. The relevant portion is already covered by P02-T02 and P02-T05.

### Candidate B — Token-universe state/materialization boundary

**Evidence supporting it**

- P02-T04 is explicitly a provider-neutral token-universe/discovery contract.
- `TokenDiscoveryRecord` contains token identity, chain identity, discovery
  classification, quality, ordering, freshness, metadata, provenance, and
  contract version.
- `DiscoveryResult.published_as_current` already distinguishes a record that
  may represent current discovery from an observable but non-current outcome.
- `DiscoveryKind` already includes `DISCOVERED`, `METADATA_UPDATED`, and
  `REMOVED`, which are sufficient inputs for a small materialization policy.
- P02-T05 provides the accepted discovery result at the existing data
  publication boundary.
- A read-oriented current-universe view is the natural consumer-facing
  representation before later market-state, intelligence, or safety work.

**Evidence against it**

- The repository does not define a persistent token registry or a policy for
  long-term retention.
- The repository does not define whether a token remains in the universe after
  a source disappears without an explicit removal observation.
- The repository does not define cross-source conflict resolution beyond the
  existing discovery-result rejection semantics.
- The repository does not define chain verification, token safety, liquidity,
  tradability, or market-state fields.

These gaps constrain the boundary. They do not prevent a minimal materializer
if it remains local, explicit, and limited to accepted discovery records.

**Phase-boundary assessment**

It fits P02 because token universe/discovery is a named P02 component. It does
not cross into P03 safety, P04 signal intelligence, execution, or production
operations when it stores only discovery evidence and currentness.

**Provider/network/persistence concerns**

The recommended form introduces no provider, network call, external transport,
database, migration, retention policy, or dependency. It may use an explicit
in-memory state object for deterministic processing. Persistence, recovery
across process restarts, and durable history require separate approval.

**Appropriate for P02-T06**

Yes. This is the smallest distinct boundary that consumes the completed
discovery publication contract and produces a useful, read-oriented state
view.

### Candidate C — Market-state collection boundary

**Evidence supporting it**

- P02's phase objective includes reliable normalized market data.
- The architecture and data pipeline place market state after validation and
  normalization.
- P02-T01 contains a normalized market-state contract.

**Evidence against it**

- No provider-neutral market observation contract for pools, prices, volume,
  liquidity, swaps, or transaction flow is defined in the current P02 task
  sequence.
- P02-T04 and P02-T05 contain token-discovery semantics, not market-state
  collection semantics.
- Collection would require defining additional identities, freshness policies,
  ordering rules, source health interactions, and field-level provenance.

**Phase-boundary assessment**

It is broadly within P02 but is a later data-intelligence boundary. Starting it
now would skip the smaller token-universe materialization step and risk
inventing market semantics.

**Provider/network/persistence concerns**

A contract-only version could avoid these concerns, but a useful collection
boundary would naturally lead to provider, network, and potentially persistence
decisions that are not authorized.

**Appropriate for P02-T06**

No. It is too broad and requires architectural information not established by
the completed discovery sequence.

### Candidate D — Provider/network integration

**Evidence supporting it**

- P02-T03 defines an adapter interface intended for future provider-specific
  wrappers.
- The P02 phase ultimately requires Solana/DEX data.

**Evidence against it**

- P02-T03 deliberately stops at a provider-neutral adapter boundary.
- The repository names no approved provider, transport, endpoint, SDK, rate
  limit, credential, retry, or operational policy.
- The uploaded decision explicitly forbids inventing a provider or network
  integration.

**Phase-boundary assessment**

It would violate the controlled scope for this task and would prematurely
introduce operational behavior.

**Provider/network/persistence concerns**

It directly introduces provider and network concerns, and may introduce
credentials, external side effects, retry behavior, and persistence.

**Appropriate for P02-T06**

No.

### Candidate E — Persistence/database boundary

**Evidence supporting it**

- P01 already contains a persistence foundation.
- P02-T01 discusses conceptual persistence and the broader architecture
  identifies persistence as a data-layer concern.
- Auditability and point-in-time reproducibility may eventually require durable
  records.

**Evidence against it**

- The current P02 contracts do not require durable token-universe storage.
- No retention, schema, migration, query, replay, or restart-recovery policy is
  defined for discovery materialization.
- A database would add lifecycle, migration, failure, and environment concerns
  without being necessary to define the next provider-neutral data boundary.

**Phase-boundary assessment**

It is not inherently outside the overall architecture, but it is premature for
this task and would expand the approved P02-T06 scope.

**Provider/network/persistence concerns**

It directly introduces persistence concerns and potentially schema and
migration changes.

**Appropriate for P02-T06**

No. Local deterministic state is sufficient for this boundary; durable
materialization must be specified separately if later required.

### Candidate F — Other directly supported boundary

**Evidence supporting it**

- The repository contains later concepts such as safety evidence, features,
  snapshots, and market state.
- A source-health or resynchronization extension could be useful in future
  work.

**Evidence against it**

- P02-T02 and P02-T05 already define the relevant observation, health,
  publication, and resynchronization handling.
- P03 safety and P04 market/signal intelligence are explicitly later phases.
- No other next boundary is named or sufficiently contracted by the current
  P02 evidence.

**Phase-boundary assessment**

Any such boundary would either duplicate completed work or cross into later
phases.

**Provider/network/persistence concerns**

The concern depends on the selected alternative, but each plausible alternative
would add scope not needed for the next deterministic discovery step.

**Appropriate for P02-T06**

No. Candidate B is the directly supported and narrower choice.

### Selected boundary

**P02-T06 is Candidate B: Provider-neutral token-universe
state/materialization boundary.**

## 3. Current Checkpoint

- **Project:** Meme Coin Hunter AI
- **Phase:** P02 — Solana / DEX Data Intelligence
- **Last completed task:** P02-T05 — Discovery-to-Orchestration Integration
  Boundary
- **P02-T05 status:** Implemented and verified
- **P02-T06 status:** Specification proposed; implementation not started and not
  authorized
- **P03 and later:** Not started and not authorized

The current boundary already provides accepted discovery results with explicit
quality, currentness, ordering/resynchronization, timestamps, source identity,
and bounded provenance. P02-T06 must consume those results rather than create a
competing discovery or normalized-state model.

## 4. Input Contract

The materializer accepts one or more provider-neutral discovery outputs in an
explicit processing context.

### Required discovery input

Each input must be a `DiscoveryResult` produced by the P02-T04 discovery
boundary and accepted through the P02-T05 integration boundary, or an
equivalent provider-neutral result explicitly defined by the approved
implementation. The input must include:

- a non-empty `discovery_id`;
- a non-empty `source_id`;
- `outcome = ACCEPTED`;
- `quality_status = VALID`;
- `accepted = true`;
- `published_as_current = true`;
- `resynchronization_required = false`;
- a non-null `TokenDiscoveryRecord`;
- timezone-aware processing and reference timestamps;
- a record with non-empty token identity and chain identity;
- the discovery kind and reason;
- ordering and freshness information;
- bounded metadata;
- bounded provenance;
- the discovery contract version.

The preferred implementation input is the existing P02-T05 result, using its
validated accepted discovery result. The materializer must not accept raw
provider objects, adapter SDK objects, unvalidated mappings, market events,
wallet data, strategy data, or arbitrary payloads.

### Processing context

The context must explicitly contain:

- the initial materialized state;
- the materializer contract version;
- the source/currentness policy;
- a deterministic batch or evaluation identity when the caller has one; and
- any explicitly approved ordering state needed to evaluate the supplied
  sequence.

The context must not read the wall clock, network, database, filesystem, or
process-global mutable state during evaluation.

## 5. Output Contract

For every input, the boundary must produce an observable result. The result
must include:

- a deterministic materialization-result identity;
- the source and discovery identities;
- token identity and chain identity when present;
- the applied discovery kind;
- an outcome distinguishing accepted/materialized, accepted/updated,
  accepted/removed, duplicate, rejected, stale, contradictory, invalid,
  unavailable, and resynchronization-required inputs;
- the resulting token-universe entry when the outcome is usable;
- whether the entry is present in the resulting current view;
- whether the current view changed;
- the complete reason category or categories;
- the processing and reference timestamps;
- the materializer contract version;
- the preserved discovery record or a bounded reference to it; and
- the resulting state version or deterministic state digest.

The current-universe view must contain only discovery-derived fields:

- token identity;
- chain identity;
- current discovery classification;
- current discovery reason;
- current quality and ordering status;
- current freshness/data-age information;
- bounded discovery metadata;
- source and discovery provenance;
- the relevant contract version; and
- deterministic state/version information.

It must not contain price, volume, pool, liquidity, swap, transaction-flow,
holder, safety, signal, feature, opportunity, decision, risk, wallet, trading,
execution, or profitability fields.

## 6. Processing Rules

1. Validate the input against the existing P02-T04/P02-T05 result semantics
   before changing materialized state.
2. Accept only a result that is accepted, valid, current, and does not require
   resynchronization.
3. Key universe entries by the canonical pair `(chain_id, token_identity)`.
   The implementation must use the repository's existing canonical identity
   conventions and must not invent an alternative token identity.
4. For `DISCOVERED`, create a new current entry when the key is absent.
5. For `DISCOVERED` on an already current key, apply duplicate or contradiction
   rules deterministically; do not silently treat the event as new information.
6. For `METADATA_UPDATED`, update only the bounded discovery metadata and
   discovery provenance represented by the accepted record. It must not add
   market or safety meaning.
7. For `REMOVED`, remove the key from the current view only when the removal
   result itself satisfies the same accepted, valid, current, and ordering
   requirements. The removal remains observable in the result.
8. For `RESYNC`, do not infer a usable universe from incomplete continuity.
   Resynchronization may be accepted only if a separately approved input
   contract supplies the complete replacement set and explicit resync evidence.
   A lone `RESYNC` record must otherwise produce a resynchronization-required
   outcome without mutation.
9. Preserve source-specific ordering evidence. An out-of-order or continuity-
   invalid input must not advance the materialized entry or current view.
10. A stale, invalid, incomplete, duplicate, contradictory, unavailable, or
    unsupported result must remain observable but must not become current state.
11. Multiple accepted records in one explicit batch must be processed in the
    supplied deterministic order, or by a documented stable ordering key. The
    implementation must not depend on incidental dictionary or set iteration.
12. The materializer must not merge records from different chains into one
    token key.
13. The materializer must not resolve contradictory evidence by choosing a
    provider, source, or value using an undocumented preference.
14. A current view is a discovery view only. Presence does not mean safety,
    liquidity, tradability, or permission to analyze or trade.
15. Publication, if exposed, must be read-oriented and must not require a
    broker, database, HTTP server, queue, or external service.

## 7. State and Mutation Rules

The materializer owns one explicit state object for one explicit processing
context. State mutation is permitted only after all acceptance checks for the
input pass.

The state must include, at minimum:

- the current entry map keyed by `(chain_id, token_identity)`;
- the last accepted discovery identity or equivalent deterministic evidence
  needed to detect duplicates;
- the latest accepted ordering evidence per applicable source;
- a resynchronization-required set or equivalent state;
- the materializer contract version; and
- a deterministic state version or digest input.

Mutation rules:

- Rejected inputs do not mutate the entry map, ordering state,
  resynchronization state, or state version.
- Duplicate inputs do not mutate current entries or advance accepted ordering.
- Contradictory inputs do not overwrite an existing entry.
- Out-of-order inputs do not advance accepted ordering or current state.
- Accepted `DISCOVERED` inputs add an entry only when the key is absent and the
  record is current and valid.
- Accepted `METADATA_UPDATED` inputs replace the prior discovery-derived
  representation atomically, preserving the new record's provenance and
  recording the prior state only if the approved result contract requires it.
- Accepted `REMOVED` inputs remove the current entry atomically and retain the
  removal result as an observable outcome.
- A missing entry may not be recreated from an invalid, stale, duplicate,
  contradictory, unavailable, or resynchronization-required result.
- State must not be shared implicitly between materializer instances.
- State must not be written to a database, file, cache service, queue, or other
  durable/external system under this specification.

No process restart, constructor call, or successful method invocation may be
interpreted as source recovery or universe completeness.

## 8. Provenance and Auditability

Every materialized entry and every result must preserve, directly or through a
bounded immutable reference:

- source identity;
- source event identity when available;
- discovery identity;
- observation, discovery, received, processing, and reference timestamps;
- sequence/order evidence;
- discovery kind and reason;
- freshness/data age;
- quality status;
- bounded source metadata;
- discovery contract version; and
- materializer contract version.

The boundary must preserve point-in-time evidence. A later metadata update or
removal must not rewrite the historical meaning of the earlier result.

Provenance must be bounded and provider-neutral. Raw provider payloads,
credentials, private keys, secrets, unbounded logs, and opaque SDK objects must
not cross the boundary.

The state digest/version must be derived from canonical serialized values with
stable field ordering and explicit treatment of absent values. It must not
depend on object memory addresses, process randomness, local hash randomization,
or hidden wall-clock reads.

## 9. Failure / Rejection Semantics

Every rejected input must return an explicit result with:

- a stable machine-readable outcome;
- one or more deterministic reason categories;
- source and discovery identity when safely available;
- `current_view_changed = false`;
- no state mutation; and
- enough bounded provenance to explain the rejection.

At minimum, the boundary must distinguish:

- malformed or wrong-type input;
- missing token or chain identity;
- unsupported discovery kind;
- missing or invalid record;
- non-accepted discovery outcome;
- non-`VALID` quality;
- non-current publication;
- stale input;
- duplicate input;
- contradictory identity or payload;
- out-of-order input;
- resynchronization required;
- unavailable source;
- unsupported provider-specific value; and
- invalid processing context.

Fail-closed rules:

- Unknown or ambiguous input is rejected.
- A rejected input is never materialized as current.
- A stale or unavailable source never produces a fresh current entry.
- A resynchronization requirement blocks mutation until the approved
  resynchronization contract is satisfied.
- Conflicting records are observable and not silently overwritten.
- A failure to compute a deterministic identity or state digest rejects the
  operation rather than producing an approximate result.

No rejection may trigger a network call, retry, provider failover, database
write, trading action, wallet action, or autonomous follow-up.

## 10. Determinism

Equivalent accepted input sequences, equivalent initial state, equivalent
ordering context, and equivalent explicit processing/reference times must
produce:

- the same result outcomes;
- the same current-universe entries;
- the same mutation flags;
- the same reasons;
- the same provenance values; and
- the same state version/digest.

The implementation must:

- use explicit timestamps supplied by the caller;
- use stable sorting for batch inputs;
- use canonical serialization for identities and state digests;
- avoid random identifiers;
- avoid implicit global state;
- avoid relying on dictionary/set iteration order;
- avoid environment-dependent provider behavior; and
- avoid comparing opaque provider values.

The materialized view must be reproducible by replaying the same accepted and
rejected discovery results against the same initial context.

## 11. Testing Requirements

If implementation is later authorized, deterministic local tests must cover at
least:

1. A valid `DISCOVERED` result creates one current token entry.
2. A valid `METADATA_UPDATED` result changes only discovery-derived fields.
3. A valid `REMOVED` result removes the current entry and remains observable.
4. A duplicate result is observable and does not mutate state.
5. A contradictory result is observable and does not overwrite state.
6. An out-of-order result does not advance accepted ordering or current state.
7. A stale result is rejected and does not create or update an entry.
8. An invalid, incomplete, or unavailable result is rejected fail closed.
9. A result requiring resynchronization does not mutate the current view.
10. A malformed or provider-specific object cannot cross the boundary.
11. Identical token identities on different chains remain separate entries.
12. Empty initial state and pre-populated state behave deterministically.
13. Batch processing produces the same result under repeated replay.
14. Explicit processing/reference times produce stable freshness and digest
    results.
15. Provenance and contract versions survive materialization.
16. Rejected inputs leave every owned state component unchanged.
17. State digests do not depend on insertion order or process randomness.
18. No test makes a live network call or requires a database, provider SDK,
    credential, or external service.
19. Existing P02-T01 through P02-T05 tests remain passing.

## 12. Explicit Non-Goals

P02-T06 does not include:

- Solana RPC, WebSocket, REST, DEX, indexer, or data-vendor integration;
- selecting, authorizing, or implementing a provider;
- network calls, credentials, secrets, rate limits, retries, reconnects, or
  failover;
- persistence, database schema, migrations, retention, query APIs, or durable
  restart recovery;
- replacing or redesigning P02-T01, P02-T02, P02-T03, P02-T04, or P02-T05;
- creating a competing raw-event, normalized-state, or discovery model;
- market-state collection;
- pools, liquidity, swaps, transaction flow, price, volume, or order books;
- token safety, eligibility, scam/rug analysis, holder analysis, or risk
  decisions;
- features, signals, opportunity scores, ranking, or phase analysis;
- AI, ML, LLM, narratives, or model inference;
- wallets, keys, signing, broadcasting, paper trading, or execution;
- strategy, profitability, capital allocation, or autonomous behavior;
- dashboards, APIs, deployment, Redis, queues, brokers, microservices, or
  operational infrastructure;
- cross-source conflict policy beyond explicit rejection;
- claims that universe presence means validity, safety, liquidity, or
  tradability; or
- authorization for P02-T07, P03, or any later phase.

## 13. Allowed Files

For this specification-only action, the only allowed file is:

- `docs/P02-T06_SPECIFICATION.md`

If implementation is separately authorized, changes must be limited to
explicitly approved provider-neutral materialization code under `core/data/`,
its focused deterministic tests under `tests/`, and any separately approved
documentation. The implementation approval must name the exact files before
work begins.

## 14. Forbidden Files

This specification does not authorize modification of:

- `PROJECT_STATE.md`;
- `docs/MASTER_BLUEPRINT.md`;
- `docs/CHANGELOG.md`;
- existing P02 implementation modules;
- existing tests;
- backend runtime, configuration, workflow, or deployment files;
- database schemas, migrations, repositories, or persistence configuration;
- dependency manifests or lockfiles;
- environment files, secrets, credentials, or provider configuration; or
- any P03 or later implementation or specification.

No new provider, network client, external integration, database object,
workflow, dependency, or credential may be introduced.

## 15. Verification Gate

Before any future implementation can be considered for approval, reviewers
must confirm:

1. The implementation consumes the existing P02-T04/P02-T05 discovery
   contracts and creates no competing model.
2. The selected boundary remains provider-neutral and local.
3. Input, output, provenance, rejection, determinism, and mutation semantics
   are explicit and covered by focused tests.
4. Invalid, stale, duplicate, contradictory, unavailable, out-of-order, and
   resynchronization-required inputs fail closed.
5. No persistence, provider, network, market-state, safety, trading, wallet,
   AI/model, or external-service behavior was added.
6. Existing P01 and P02 regression tests remain passing.
7. The implementation does not alter project governance files unless a
   separate governance update is explicitly approved.
8. Verification uses deterministic local fixtures and does not require
   credentials or live external services.

Passing these checks does not itself authorize implementation. It is only the
technical gate for a separately approved implementation task.

## 16. Authorization

This document records the architectural recommendation and controlled
implementation boundary for P02-T06. It authorizes no Python code, tests,
dependency change, workflow change, provider setup, network access,
persistence change, commit, or push.

Implementation requires:

- explicit review and approval of this specification;
- a separately authorized implementation task;
- confirmation of the exact implementation files;
- preservation of the current P02 and P01 boundaries; and
- separate approval for any future provider, network, persistence, or
  operational behavior.

P02-T06 implementation is NOT authorized by this specification alone. Implementation may begin only after the specification is reviewed and explicitly approved.