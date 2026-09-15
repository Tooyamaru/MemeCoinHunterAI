# P08 — Read-Only Market-Data Adapter Specification

**Status:** SPECIFICATION CORRECTED / AWAITING FORMAL RE-AUDIT / IMPLEMENTATION NOT AUTHORIZED
**Phase:** P08 — Outcome Learning  
**Boundary:** Provider-neutral, immutable, read-only market observations  
**Contract version:** `p08-read-only-market-data-observation-v1`  
**Nature:** Deterministic, immutable, read-only, paper-only evidence

## 1. Purpose and authority

This document defines the formal contract for a future provider-neutral,
read-only market-data adapter. The adapter supplies immutable observations that
may be used by an explicitly authorized consumer for:

1. memecoin candidate discovery; and
2. paper-only opportunity evaluation.

The adapter supplies evidence only. It does not decide whether a candidate is
safe, eligible, attractive, authorized, executable, profitable, or economically
realized.

This specification creates no implementation authority. A separate formal
specification audit must pass before a separate implementation authorization can
be considered. No code, test, dependency, provider, workflow, persistence, or
external access is authorized by this document.

For the single contract version `p08-read-only-market-data-observation-v1`,
this specification is the sole normative contract. The proposal with the same
version is a non-normative traceability document and must repeat this contract's
rules without variation.

## 2. Architectural position

The intended boundary is:

```text
future source-specific collection and parsing
        ↓
future provider-neutral translation
        ↓
P08 ReadOnlyMarketDataObservation
        ↓
explicit discovery or paper-evaluation consumer
        ↓
P05 opportunity context / P07 paper-simulation input
```

The source-specific layer owns transport, parsing, credentials, source error
translation, and raw-payload byte production. The canonical adapter contract
accepts only bounded provider-neutral values and explicit provenance.

The adapter does not replace or bypass an approved predecessor contract. When
the input originates at P02, the adapter preserves the P02 identity, source
identity, observation identity, predecessor version, and predecessor digest.
It does not re-admit, repair, refresh, aggregate, or rewrite P02 state.

## 3. Provider and domain neutrality

The contract does not select, require, or name a chain, exchange, venue, pool,
route, wallet, endpoint, SDK, transport, vendor, or provider.

`chain_id` is always present and is either an opaque `CanonicalText` domain
identity or explicit `null`. It is not a chain connection instruction,
chain-state assertion, RPC identity, or permission. `null` is permitted only
when no P02 predecessor is supplied and the selected consumer profile explicitly
allows a chain-neutral candidate. When a P02 predecessor is supplied,
`chain_id` must be the predecessor's non-null identity copied exactly.

Likewise:

- `token_identity` is an opaque canonical token identity, not a wallet lookup;
- `market_subject_id` is an opaque subject identity, not a pool, venue, pair,
  route, or execution target;
- `source_id` is a logical provenance identity, not an authority grant;
- `candidate_id` is a deterministic analytical identity, not an order or
  position identity.

No identity may be derived from a display name, symbol, object address,
provider-client identity, process identity, memory address, insertion order,
random value, or current time.

## 4. Contract vocabulary

### 4.1 Canonical scalar types and hard bounds

The following are closed wire rules for
`p08-read-only-market-data-observation-v1`. No implementation authorization may
select an alternative representation:

| Type | Required representation |
|---|---|
| `CanonicalText` | Unicode text normalized to NFC, trimmed of leading/trailing Unicode whitespace, non-empty, no unpaired surrogates, at most 256 Unicode scalar values, and at most 1,024 UTF-8 bytes after normalization and trimming. |
| `NullableCanonicalText` | `CanonicalText` or explicit `null`; omitted and `null` are different. |
| `DecimalText` | Finite normalized decimal text; no binary floating point, NaN, or infinity. |
| `NonNegativeInteger` | Canonical ASCII base-10 integer text of 1–20 digits, with `0` as the only zero form and no leading zeroes; values are in the inclusive range `0` through `99,999,999,999,999,999,999`. |
| `Digest256` | Exactly 64 lowercase hexadecimal characters representing SHA-256. |
| `UtcTimestamp` | Timezone-aware instant normalized to canonical UTC serialization. |
| `SequenceValue` | An explicit source sequence/cursor representation; it is not comparable unless its comparison policy is supplied. |
| `BoundedMapping` | Recursively canonical JSON mapping with Unicode-code-point-sorted string keys, maximum depth 8 including the root, maximum 64 members per mapping, maximum 128 elements per immutable sequence, and maximum 16,384 bytes for the complete compact canonical UTF-8 representation; only approved canonical scalar values, mappings, and sequences are allowed. |
| `ImmutableSequence` | Ordered immutable sequence of at most 128 elements; sets are forbidden. |

An input that exceeds any stated bound, uses a non-canonical representation, or
contains an opaque or unknown value fails closed; it is not truncated, repaired,
or substituted.

Canonical-field rejection mapping is fixed:

- an absent required field produces `MISSING_REQUIRED_INPUT`;
- a wrong runtime type, or explicit `null` for a non-nullable field, produces
  `INVALID_TYPE`;
- non-NFC text, untrimmed text, empty text, a text scalar/byte limit violation,
  a negative or non-canonical `NonNegativeInteger`, a mapping/sequence
  depth/entry/byte limit violation, an unknown mapping field, a non-string
  mapping key, an opaque value, or a set produces
  `INVALID_CANONICAL_REPRESENTATION`;
- an omitted optional field is valid, and explicit `null` is valid only for a
  field declared nullable; and
- unsupported enum, source, adapter, metric, freshness, consumer-profile, or
  predecessor versions use `UNSUPPORTED_VERSION`.

When multiple conditions are visible, these mappings are resolved by the
strict Section 12 precedence, with `INVALID_TYPE` before
`MISSING_REQUIRED_INPUT`, `UNSUPPORTED_VERSION`, and
`INVALID_CANONICAL_REPRESENTATION`.

### 4.2 Enumerations

The canonical observation supports only:

```text
observation_kind:
  DISCOVERY
  PAPER_EVALUATION

field_status:
  PRESENT
  MISSING
  UNAVAILABLE
  INVALID

freshness_boundary:
  INCLUSIVE
  EXCLUSIVE

ordering_status:
  ORDERED
  UNORDERED
  UNKNOWN
```

No additional wire value is accepted without a new contract version.

## 5. Exact public observation contract

The future public value is an immutable
`ReadOnlyMarketDataObservation`. Its top-level canonical mapping contains
exactly the following fields. Unknown fields are rejected.

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `contract_version` | `CanonicalText` | yes | Exactly `p08-read-only-market-data-observation-v1`. |
| `observation_id` | `CanonicalText` | yes | Stable source-observation identity, or the validated deterministic identity derived under Section 8. |
| `candidate_id` | `CanonicalText` | yes | Deterministic analytical candidate identity. |
| `chain_id` | `CanonicalText \| null` | yes | Always present; explicit `null` is permitted only for a chain-neutral profile with no P02 predecessor. A P02-linked observation must copy a non-null predecessor identity. |
| `token_identity` | `CanonicalText` | yes | Canonical token identity supplied by the source-neutral boundary or approved predecessor. |
| `market_subject_id` | `CanonicalText \| null` | yes | Opaque market-subject identity when supplied; never inferred from display metadata. |
| `observation_kind` | supported enum | yes | Explicit discovery or paper-evaluation use profile. |
| `observed_at` | `UtcTimestamp` | yes | Source observation instant. |
| `availability_at` | `UtcTimestamp` | yes | Earliest instant the observation was available to the consumer. |
| `sequence` | `SequenceValue \| null` | yes | Explicit source sequence/cursor, or explicit `null` when absent. |
| `ordering_status` | supported enum | yes | Ordering status supplied or established by an approved comparison policy. |
| `source` | `SourceEnvelope` | yes | Bounded source identity and source-contract provenance. |
| `provenance` | `ProvenanceEnvelope` | yes | Complete bounded origin and predecessor context. |
| `metrics` | `MetricSet` | yes | Exact normalized field catalog described in Section 7. |
| `evaluation_context` | `EvaluationContext` | yes | Explicit cutoff, freshness, consumer profile, and predecessor context. |
| `raw_payload_digest` | `Digest256` | yes | Digest of the source payload's approved canonical bytes. |
| `observation_digest` | `Digest256` | derived and verified | SHA-256 digest of the complete observation excluding only this field. |

Every top-level field is present in canonical form. `null` is a value, not an
omission. The only optional members in the contract are explicitly identified
inside nested mappings below.

The raw source payload is not part of the public observation. The
`raw_payload_digest` is an integrity reference and is not permission to fetch
the payload later or a substitute for missing normalized values.

## 6. Source and provenance envelopes

### 6.1 `SourceEnvelope`

`source` is an immutable mapping with exactly these fields:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `source_id` | `CanonicalText` | yes | Stable logical source identity at the provider-neutral boundary. |
| `source_event_id` | `CanonicalText \| null` | yes | Source event identity when supplied; explicit `null` otherwise. |
| `source_contract_version` | `CanonicalText` | yes | Exact source-to-adapter translation contract version. |
| `adapter_contract_version` | `CanonicalText` | yes | Exactly this adapter contract version. |
| `source_observed_at` | `UtcTimestamp \| null` | yes | Source-declared time when available; must agree with `observed_at` under the source contract. |
| `source_metadata` | `BoundedMapping` | yes | Bounded canonical metadata only; no credentials, opaque objects, or unbounded payload. |

`source_id` does not identify an authoritative source. Different source
identities remain separate observations unless a separate aggregation or
reconciliation contract is approved.

### 6.2 `ProvenanceEnvelope`

`provenance` is an immutable mapping with exactly these fields:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `source_id` | `CanonicalText` | yes | Must equal `source.source_id`. |
| `source_event_id` | `CanonicalText \| null` | yes | Must equal `source.source_event_id`. |
| `candidate_id` | `CanonicalText` | yes | Must equal the top-level candidate identity. |
| `chain_id` | `CanonicalText \| null` | yes | Must equal the top-level chain identity. |
| `token_identity` | `CanonicalText` | yes | Must equal the top-level token identity. |
| `market_subject_id` | `CanonicalText \| null` | yes | Must equal the top-level subject identity. |
| `observation_id` | `CanonicalText` | yes | Must equal the top-level observation identity. |
| `observed_at` | `UtcTimestamp` | yes | Must equal the top-level observation time. |
| `availability_at` | `UtcTimestamp` | yes | Must equal the top-level availability time. |
| `cutoff_time` | `UtcTimestamp` | yes | Must equal `evaluation_context.cutoff_time`. |
| `freshness_policy_version` | `CanonicalText` | yes | Must equal the selected freshness policy. |
| `consumer_profile_version` | `CanonicalText` | yes | Must equal the selected consumer profile. |
| `predecessor_digest` | `Digest256 \| null` | yes | Approved upstream digest when one exists; explicit `null` otherwise. |
| `field_provenance` | immutable ordered mapping | yes | One bounded source reference for every metric field present in `metrics`. |

Provenance is evidence of origin and context. It is not an approval, source
preference, authority grant, or claim of external truth.

## 7. Exact normalized metric catalog

`metrics` is an immutable mapping. It must contain the required keys
`price`, `liquidity`, `volume`, and `asset_age`. It may additionally contain
`holders` and `transactions`. No other key is permitted.

An omitted optional key is not equivalent to a present key with `null`. If an
optional key is present, it must contain a complete `MetricEnvelope`. All
metric envelopes use the following exact fields:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `status` | `field_status` | yes | Whether the source supplied a usable value. |
| `value` | field-specific value \| `null` | yes | Non-null only when status is `PRESENT`. |
| `unit` | `CanonicalText \| null` | yes | Explicit source-supplied unit; never guessed. |
| `semantic_version` | `CanonicalText \| null` | yes | Version of the source-to-field meaning. |
| `measurement_window` | `TimeWindow \| null` | yes | Explicit measurement window where the metric has one. |
| `reference_semantics` | `CanonicalText \| null` | yes | Explicit reference meaning where the metric requires one. |
| `source_field` | `CanonicalText \| null` | yes | Bounded source field reference when supplied. |
| `field_digest` | `Digest256` | derived and verified | Digest of the envelope excluding only `field_digest`. |

For `PRESENT`, the value, unit, semantic version, and applicable contextual
fields must be valid. For `MISSING`, `UNAVAILABLE`, and `INVALID`, `value`
must be `null`; the envelope must not hide a substitute value. A field status
does not turn an invalid or unavailable value into usable evidence.

### 7.1 Field-specific values

| Metric | Field-specific value | Required source semantics |
|---|---|---|
| `price` | `{ "amount": DecimalText, "quote_asset": CanonicalText }` | The source supplies the amount, quote asset, and unit. The adapter never derives price from another metric. |
| `liquidity` | `{ "amount": DecimalText, "valuation_unit": CanonicalText, "valuation_context": CanonicalText }` | The source supplies the value and valuation context. Liquidity is not inferred from volume, depth, or another source. |
| `volume` | `{ "amount": DecimalText }` | The source supplies the amount, unit, and explicit measurement window. Volume is not inferred from transactions. |
| `asset_age` | `{ "amount": DecimalText }` | The source supplies the amount, unit, and explicit reference semantics. Asset age is distinct from observation data age. |
| `holders` | `{ "count": NonNegativeInteger }` | Optional. Accepted only when the future source explicitly supplies a holder count under an approved field contract. |
| `transactions` | `{ "count": NonNegativeInteger }` | Optional. Accepted only when the future source explicitly supplies a count and measurement window under an approved field contract. |

`TimeWindow` is an immutable mapping with exactly:

```text
{
  "start": UtcTimestamp,
  "end": UtcTimestamp,
  "boundary": "INCLUSIVE" | "EXCLUSIVE"
}
```

It must satisfy `start <= end`. A metric that requires a window cannot use a
missing or contradictory window. A metric that does not require a window must
use explicit `null`; a caller may not invent one.

The adapter does not define source coverage, valuation, cross-source
aggregation, feature formulas, derived metrics, or strategy thresholds.

## 8. Identity and digest semantics

### 8.1 Candidate and token identity

`candidate_id` and `token_identity` are required opaque canonical identities.
`chain_id` and `market_subject_id` are required fields. `chain_id` follows the
single nullability rule in Section 3; `market_subject_id` may be explicitly
`null` only when the selected domain and consumer profile allow no market
subject.

When a P02 predecessor is supplied, its exact `(chain_id, token_identity)` and
`market_subject_id` identities remain predecessor-owned and must be copied,
validated, and linked. The adapter must not create a second token identity or
reinterpret a P02 identity. When no such predecessor exists, the adapter may
accept the explicitly chain-neutral form only under the profile rule in
Section 3; it must not infer a chain.

Identity equality is exact canonical equality. Display labels, symbols, source
labels, wallet addresses, provider identifiers, and matching text fragments do
not establish identity.

### 8.2 Observation identity

When `source_event_id` is present, the preferred identity material is:

```json
{
  "source_id": "...",
  "source_event_id": "..."
}
```

When it is absent, the adapter must derive identity from this fixed canonical
projection:

```json
{
  "source_id": "...",
  "candidate_id": "...",
  "chain_id": null,
  "token_identity": "...",
  "market_subject_id": null,
  "observed_at": "...",
  "sequence": null,
  "observation_kind": "...",
  "metrics": { "...": "..." }
}
```

The actual populated values are used; the shown `null` values are placeholders
for the projection shape. The derived identity is:

```text
SHA-256(UTF-8("p08-read-only-market-data:observation-id:v1\0"
              + canonical_identity_projection))
```

An explicitly supplied `observation_id` must equal the identity required by its
source contract. A supplied identity that disagrees with its identity material
is contradictory input, not a reason to accept the supplied label.

### 8.3 Field, raw-payload, and observation digests

All digests use lowercase SHA-256 over compact canonical UTF-8 bytes:

1. `field_digest` covers the complete metric envelope excluding only
   `field_digest`.
2. `raw_payload_digest` covers the source payload's approved canonical bytes.
   The source adapter computes it before the payload crosses this boundary.
3. `observation_digest` covers every top-level field and nested canonical field,
   including identity, timestamps, source, provenance, metrics, evaluation
   context, freshness material, and `raw_payload_digest`, excluding only
   `observation_digest`.

Nested field digests must be validated before the observation digest. Any
mismatch rejects the observation. No digest may override different source
fields, repair partial material, or authorize payload retrieval.

## 9. Evaluation context, cutoff, and freshness

Every validation call must supply an explicit immutable `EvaluationContext` with
exactly:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `cutoff_time` | `UtcTimestamp` | yes | Sole adapter validation cutoff. |
| `freshness_policy_version` | `CanonicalText` | yes | Exact supported freshness policy. |
| `max_age_seconds` | `DecimalText \| null` | yes | Maximum allowed data age; `null` means no maximum is declared by this policy. |
| `freshness_boundary` | `INCLUSIVE \| EXCLUSIVE` | yes | Equality behavior when `max_age_seconds` is present. |
| `consumer_profile_version` | `CanonicalText` | yes | Exact profile declaring required and permitted fields. |
| `required_fields` | sorted immutable sequence | yes | Required metric keys for this evaluation. |
| `permitted_optional_fields` | sorted immutable sequence | yes | Optional metric keys permitted by this profile. |
| `predecessor_context_digest` | `Digest256 \| null` | yes | Explicit predecessor snapshot/state digest when applicable. |
| `processing_context_identity` | `CanonicalText` | yes | Identity of the explicit local processing context. |

The required and optional field sequences must contain unique names from the
approved metric catalog. A required field cannot also be optional.

The adapter computes only:

```text
data_age = cutoff_time - observed_at
```

The mandatory temporal relationships are:

```text
observed_at <= availability_at <= cutoff_time
```

The rules are:

1. A future observation is invalid and is never delayed into validity.
2. A negative `data_age` is invalid.
3. If `max_age_seconds` is `null`, the policy declares no maximum age; this
   does not make an unavailable or invalid field usable.
4. With an inclusive boundary, `data_age == max_age_seconds` is valid.
5. With an exclusive boundary, equality is stale.
6. `data_age > max_age_seconds` is stale for either boundary.
7. Missing, malformed, naive, or contradictory timestamps fail closed.
8. `observed_at` is never replaced with received time, processing time, or the
   system clock.
9. Later processing cannot make an old observation fresh.
10. `asset_age` is source-supplied and must never be confused with `data_age`.

The adapter cutoff is validation context only. It does not replace P05
reference time, P06 decision time, P07 `simulation_reference_time`, P08-T02
`as_of_time`, or any predecessor-owned timestamp.

## 10. Consumer profiles and missing-data behavior

A consumer profile, not the adapter, decides which metrics are required. The
profile must explicitly declare field names, semantic versions, units, and
freshness policy.

### 10.1 Discovery

A discovery evaluation is usable only when every required field is:

- present in `metrics`;
- `PRESENT`;
- finite and unit-valid;
- semantically versioned;
- provenance-valid; and
- within the explicit cutoff and freshness policy.

Missing price, liquidity, volume, or asset age fails closed when the profile
requires that field. Missing holders or transactions are never zero, healthy,
inactive, or safe.

Presence in a discovery observation never means safe, eligible, liquid,
tradable, profitable, or authorized.

### 10.2 Paper-only evaluation

A paper-evaluation profile may require market fields only when it explicitly
declares their point-in-time semantics. A profile using market conditions must
declare required price, liquidity, volume, and asset-age semantics. Holders and
transactions may be used only when explicitly supplied and version-authorized.

If a required field is missing, unavailable, invalid, stale, contradictory,
unsupported, or outside the cutoff, the result is non-usable. The adapter must
not manufacture a quote, fill, score component, confidence value, or
opportunity from partial data.

An accepted observation is evidence only. It is not a paper order, fill,
position transition, ledger entry, authorization, or simulation result. P07 must
validate and own its own `execution_observation` contract before using any
observation in simulation.

## 11. Canonical serialization and immutability

Canonical serialization is compact UTF-8 JSON with the exact scalar and mapping
bounds in Section 4.1 and:

1. Unicode NFC normalization before escaping;
2. sorted object keys using Unicode code-point order;
3. fixed semantic order for arrays and ordered tuples;
4. explicit enum wire values;
5. timezone-aware timestamps serialized as canonical UTC RFC 3339 text;
6. finite decimal values serialized as normalized decimal text;
7. lowercase ASCII hexadecimal SHA-256 values;
8. explicit `null` values, with no absent/null equivalence;
9. no sets, unordered mappings, binary floats, NaN, infinity, opaque objects,
   non-string keys, or unbounded values; and
10. no insignificant whitespace, byte-order mark, or hidden serialization state.

The public observation, source metadata, provenance, metrics, field envelopes,
evaluation context, and canonical views are recursively immutable. A later
observation creates a new record and never edits an earlier record, digest,
provenance, or source value.

Equivalent canonical values and equivalent explicit evaluation contexts must
produce equal identities, canonical representations, digests, and validation
outcomes.

## 12. Validation result and reason precedence

The future pure validator returns one immutable result for safely representable
input. A structurally invalid input for which no safe result can be constructed
fails closed without an accepted observation. The result must expose:

| Field | Meaning |
|---|---|
| `accepted` | `true` only for `VALID`; otherwise `false`. |
| `reason_code` | Exactly one value from the fixed vocabulary below. |
| `observation` | The immutable observation only when accepted or safely preserved for audit. |
| `observation_digest` | The verified observation digest when available. |
| `processing_context_identity` | The supplied explicit context identity. |
| `state_changed` | Always `false` for rejected, duplicate, replayed, contradictory, stale, unavailable, or out-of-order input. |
| `provenance` | Bounded available provenance without secret or payload leakage. |

The fixed reason vocabulary is:

```text
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
VALID
```

When several conditions are visible, exactly one reason is selected by this
strict precedence:

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

Precedence is based on the canonical validation model, not caller order,
retrieval order, arrival order, timestamp preference, value magnitude, or
freshness preference.

`MISSING_REQUIRED_INPUT` means a required structural observation, context, or
field is absent. `INCOMPLETE_INPUT` means the structure exists but a required
consumer field is explicitly missing, unavailable, or incomplete under the
selected profile. Neither state may pass.

## 13. Replay, duplicate, contradiction, and ordering

The validator receives an explicit immutable processing context. The context
may contain accepted identity/content fingerprints, prior comparable sequence,
and a context digest. It must not be a hidden registry, cache, database,
filesystem, network lookup, source client, or process-global singleton.

### 13.1 Exact replay

An exact replay has the same canonical observation, cutoff/freshness context,
consumer profile, predecessor context identity, and prior-context identity as a
previous explicit request. It returns the same immutable result, canonical
representation, and digest with reason `REPLAY` when a result record is
requested. It does not create another accepted observation, advance ordering, or
mutate context.

### 13.2 Duplicate

A duplicate has the same observation identity and canonical content as an
accepted observation in the explicit processing context but is not the same
complete replay request. It returns `DUPLICATE`, does not replace the accepted
record, does not advance ordering, and leaves the context digest unchanged.

### 13.3 Contradiction

A contradiction occurs when the same observation identity is paired with
different canonical content, or when identity, source, candidate, timestamps,
provenance, metric status, field digest, or observation digest material
disagree. It returns `CONTRADICTORY_INPUT`, preserves the prior accepted
record, and leaves ordering and context digests unchanged.

The adapter never chooses a value by arrival order, source label, display
metadata, or undocumented preference. Cross-source merge, consensus,
interpolation, and authoritative-source selection require a separate contract.

### 13.4 Ordering

Only explicit comparable sequence/cursor semantics may establish ordering.
Integer sequences may be compared only under the approved source policy. An
untyped or incomparable cursor is `UNKNOWN`; it is not guessed. Missing
sequence is not evidence of order.

An explicitly comparable sequence that violates the supplied ordering context
returns `OUT_OF_ORDER`. Rejected, stale, unavailable, duplicate,
contradictory, replayed, and out-of-order records do not advance ordering.

## 14. Version compatibility

The validator supports only exact
`p08-read-only-market-data-observation-v1`. Any change to field meaning,
requiredness, identity, canonicalization, digest coverage, timestamp semantics,
metric units, profile semantics, or validation behavior requires a new explicit
contract version.

Unsupported observation, source, adapter, metric, freshness, consumer-profile,
or predecessor versions return `UNSUPPORTED_VERSION`. Similar names, matching
fields, matching digests, or compatible-looking statuses do not authorize
substitution.

There is no automatic migration, legacy promotion, inference, reconstruction,
or reinterpretation. Any future migration needs its own specification,
canonical representation, focused tests, implementation authorization, and
audit.

## 15. Pure validation and prohibited ambient state

Validation, normalization, identity derivation, and digest calculation operate
only on explicit inputs. They must not read or depend on:

- wall-clock time or local timezone;
- random values or random UUIDs;
- environment variables or hidden configuration;
- process identity or memory address;
- dictionary or set insertion order;
- filesystem, database, cache, queue, or durable history;
- network, source availability, or current provider state;
- provider clients, SDKs, callbacks, or endpoint handles;
- hidden registries or mutable singletons; or
- caller preferences not represented in the canonical context.

The adapter has no external access in its future pure validation contract. If a
digest, identity, or validation outcome cannot be computed safely, it rejects
the input rather than approximating it.

## 16. Ownership boundaries

### 16.1 P02 and source adaptation

P02 remains the owner of approved upstream token and market-observation
admission, source conventions, local state, freshness, ordering, and
predecessor digests where those contracts apply. A future source adapter owns
source parsing and raw-payload digest production.

This adapter owns only translation into this read-only observation and its pure
validation result. It does not own source lifecycle, transport health,
retry/recovery, durable persistence, market-state materialization, or
cross-source state.

### 16.2 P05 Opportunity Engine

P05 owns candidate normalization, hard-risk gating, feature availability,
opportunity scoring, opportunity records, and opportunity context.

The adapter may supply validated evidence to an explicitly approved P05 input
boundary. It must not create or replace a P05 candidate, reevaluate safety,
calculate P05 features, score, rank, compare, reduce, create an opportunity
record, or treat `VALID` as `ELIGIBLE`. P05 owns its own missing-data semantics.

### 16.3 P06 Decision Engine

P06 owns deterministic decision evaluation and immutable `DecisionIntent`
production from validated P05 context.

The adapter must not fetch for P06, modify P06 context, select an action,
produce confidence, create a decision intent, or interpret market evidence as
authorization. P06 remains analytical intent only.

### 16.4 Risk/Capital

Risk/Capital owns the Risk Governor, capital admission, approval scope,
validity, and the exact paper-only authorization reference required by the
current P07 v2 admission path.

The adapter does not create, infer, renew, validate, substitute, or attach
Risk/Capital authorization. A valid observation is not a Risk/Capital `PASS`.
Unknown, stale, missing, or invalid evidence remains fail-closed wherever the
Risk/Capital policy requires it.

### 16.5 P07 Paper Trading

P07 owns paper-simulation input, fills, state transitions, ledger,
reconciliation, the canonical non-economic paper result, and local history.

P07 may consume this observation only as explicitly supplied evidence after P07
validates its own required identity, cutoff, quality, provenance, and digest
links. The adapter does not calculate fills, fees, spread, slippage, impact,
latency, or MEV; create execution observations by lookup; authorize a paper
lifecycle; mutate position, exposure, ledger, or history; reconcile external
truth; or turn data into an order or execution request.

P07 `simulation_reference_time` remains the P07 cutoff.

### 16.6 G1

G1 owns only simulation-only recognition and finality for a complete explicitly
supplied P06 → P07 → P08 chain. It validates predecessor-owned contracts
through their own canonical representations and does not create market
observations.

This adapter adds no G1 authority, cutoff, economic state, or provenance link.
G1 may encounter an observation transitively inside a validated predecessor
artifact, but it does not reinterpret it or establish settlement, valuation,
accounting, realized P&L, or performance.

## 17. Minimal future implementation and test scope

No file in this section is created or authorized by this specification. If a
separate implementation authorization is granted, the smallest proposed
contract boundary is:

```text
core/data/read_only_market_data.py
tests/test_read_only_market_data.py
```

`core/data/__init__.py` may change only if the authorization explicitly names
the required public exports. No provider source adapter, API route, worker,
database, migration, cache, workflow, dependency, or persistence file is
included.

The future source module may contain only:

1. immutable observation and metric-envelope values;
2. explicit evaluation context, freshness policy, and consumer profile inputs;
3. deterministic identity, canonicalization, and SHA-256 verification;
4. fixed fail-closed validation and reason precedence;
5. explicit replay, duplicate, contradiction, and ordering handling; and
6. an explicit local processing context with no ambient state.

The focused test module must use deterministic local fixtures and cover:

1. valid discovery and paper-evaluation observations;
2. exact required and optional field behavior;
3. candidate, token, nullable chain, and nullable market-subject identity;
4. source identity, source-event identity, provenance, and predecessor links;
5. field-specific price, liquidity, volume, asset-age, holders, and transaction
   values;
6. source-only admission of holders and transactions;
7. missing, explicit `null`, unavailable, invalid, stale, future, and
   non-finite values;
8. cutoff equality for inclusive and exclusive freshness policies;
9. unknown fields, unsupported versions, unsupported metrics, and bad units;
10. canonical mapping order, timestamp, decimal, enum, and null behavior;
11. field, raw-payload, and observation digest validation and tampering;
12. exact replay without mutation;
13. duplicate identity/content without replacement;
14. same identity with changed content as contradiction;
15. explicit ordering, missing sequence, and out-of-order behavior;
16. deterministic reason precedence;
17. recursive immutability and predecessor non-mutation; and
18. absence of scoring, ranking, decision, authorization, execution, settlement,
    accounting, realized P&L, or live-trading behavior.

Tests must not contact a provider, network, API, database, queue, filesystem
store, wallet, SDK, or external service.

## 18. Explicit exclusions

This specification does not include or authorize:

- any named or selected provider, source vendor, exchange, venue, or endpoint;
- provider-specific code, SDKs, clients, callbacks, or transport behavior;
- API credentials, access tokens, secrets, private keys, or wallet material;
- exchange, wallet, signer, signing, chain transaction, RPC, DEX, or broadcast
  behavior;
- live trading, orders, execution, settlement, external finality, accounting,
  valuation, cost basis, numeraire, realized P&L, ROI, or performance
  classification;
- G2 realization eligibility;
- G3 accounting or economic-result calculation;
- G4 performance classification;
- P09 controlled execution;
- network calls, source polling, retry, failover, recovery, or monitoring;
- persistence, database schema, migration, queue, cache, durable replay, or
  filesystem state;
- source aggregation, consensus, interpolation, reconciliation, or conflict
  resolution;
- safety, eligibility, signal, feature, opportunity, score, rank, comparison,
  reduction, or decision behavior;
- Risk/Capital authorization;
- P07 fill, position, ledger, reconciliation, or history mutation;
- G1 recognition, finality, or economic interpretation;
- AI, ML, LLM, narrative analysis, autonomous behavior, or model promotion; and
- changes to existing source code, tests, dependencies, workflows, or
  governance contracts as part of this specification-only task.

## 19. Separate gates before code

The gates below are ordered and independent.

### Gate 1 — Formal specification audit

An independent audit must be recorded separately and must confirm that this
specification:

- is internally consistent and implementation-testable;
- defines exact required/optional fields, types, null semantics, canonical
  serialization, identity, provenance, timestamps, freshness, and digests;
- preserves provider, chain, exchange, wallet, and source neutrality;
- preserves P02 predecessor identity and digest ownership;
- does not weaken P05 hard-risk, feature, scoring, or opportunity ownership;
- preserves P06 intent-only authority;
- preserves Risk/Capital authority and paper-only admission;
- preserves P07's non-economic simulation and `simulation_reference_time`;
- preserves G1 predecessor-owned validation and simulation-only recognition;
- has deterministic missing, invalid, stale, future, unsupported, duplicate,
  replay, contradiction, ordering, and reason-precedence semantics;
- contains no credentials, provider leakage, ambient-state dependency, G2, G3,
  G4, or P09 scope; and
- matches the current repository-root governance and closed-contract status.

Audit completion does not authorize code.

### Gate 2 — Explicit implementation authorization

Only a separate written authorization after a passing audit may permit code. It
must name:

- the exact approved files and public exports;
- this exact contract version;
- the focused test file and required test cases;
- dependency posture and verification commands;
- forbidden provider, network, credential, persistence, workflow, and authority
  behavior; and
- the requirement for a post-implementation audit.

The authorization must require no changes to P05, P06, Risk/Capital, P07, G1,
or their project-state contracts, and must confirm that the result remains
immutable, read-only, deterministic, provider-neutral, and paper-only.

No implementation may begin merely because this specification exists or passes
formal audit.

## 20. Governance conclusion

The read-only market-data adapter is a narrow evidence boundary. It can carry
source-supplied normalized market observations for candidate discovery and
paper-only evaluation while preserving point-in-time context, provenance,
immutability, freshness, and SHA-256 integrity.

It creates no decision, authorization, execution, settlement, accounting,
economic-result, or live-trading path. The specification is complete and awaits
its separate formal audit. Until that audit passes and a separate
implementation authorization is issued, no code is permitted.