# P08 — Market-Data Temporal Semantics Contract Proposal

**Status:** PROPOSED / NOT IMPLEMENTATION AUTHORIZED
**Date:** 2026-09-18
**Existing contract preserved:** `p08-read-only-market-data-observation-v1`
**Proposed contract:** `p08-market-data-temporal-evidence-v1`

## 1. Decision requested

Approve a narrowly scoped, pre-admission evidence contract for source timing and
receipt timing. This proposal does not adopt the contract, change P08 v1, or
authorize code, provider access, or downstream use.

The recommended next implementation is one pure, provider-neutral temporal
evidence module that consumes the existing inspection report. It adds a
machine-checkable distinction between source freshness and receipt recency
without creating another provider adapter or pretending that undocumented
source timing exists.

## 2. Correct evidence boundary

### 2.1 What is normative versus what is exercised

P08 v1 structurally requires metric envelopes named `price`, `liquidity`,
`volume`, and `asset_age`. It does **not** make all four `PRESENT` for every
possible evaluation: `EvaluationContext.required_fields` selects the fields
required by a consumer profile.

The normative rules are:

- Section 10.1 requires every field selected by a discovery profile to be
  `PRESENT`, unit-valid, semantically versioned, provenance-valid, and fresh.
- Section 10.2 requires `price`, `liquidity`, `volume`, and `asset_age` when a
  paper-evaluation profile uses market conditions.
- Optional `holders` and `transactions` are not universal requirements.

The current implementation has `_REQUIRED_METRICS` for the four structural
envelope names, but the only `EvaluationContext` constructor outside the
validator is the focused test fixture in
`tests/test_read_only_market_data.py`. That fixture names all four fields for
`paper-evaluation-v1`; it is evidence of the exercised test shape, not a
production profile registry or universal policy.

No production construction of `EvaluationContext` was found. No production
consumer of `ReadOnlyMarketDataObservation` was found either. Existing
`core/data/discovery.py` and `core/data/orchestration.py` consume separate
P02 `DiscoveryObservation` and `AdapterObservation` contracts; their
`_validate_observation` functions are not the P08 validator.

Therefore:

1. The four envelope names remain structurally required by P08 v1.
2. There is currently no production consumer proving that all four must be
   `PRESENT` in every evaluation.
3. A future authorized market-condition discovery or paper profile must still
   declare and require the fields specified by P08 Sections 10.1 and 10.2.
4. This proposal does not weaken, reinterpret, or change that behavior.

### 2.2 What each metric is needed for

| Evidence | Genuine operation if a profile selects it | Current production consumer |
|---|---|---|
| `price` | Point-in-time quote or market-condition evaluation | None found |
| `liquidity` | Point-in-time liquidity condition under an approved valuation semantic | None found |
| `volume` | Activity condition with an explicit measurement window | None found |
| `asset_age` | Age-based condition using explicit token-origin reference semantics | None found |
| `holders` | Optional holder-based condition only when explicitly authorized | None found |
| `transactions` | Optional transaction-count condition with an explicit window | None found |
| Receipt recency | Inspection, observability, and audit display only | Existing inspector |

Passing P08 validation is evidence only. It is not P05 eligibility, a P06
decision, Risk/Capital approval, paper admission, or an execution instruction.
P05, P06, Risk/Capital, and P07 remain owners of their own contracts and gates.

## 3. Proposed temporal-evidence contract

The new contract is deliberately separate from
`ReadOnlyMarketDataObservation`. It is an evidence record for source and
receipt timing, not an alternate accepted P08 observation.

Its canonical top-level mapping is:

```json
{
  "contract_version": "p08-market-data-temporal-evidence-v1",
  "source_id": "source identity",
  "source_event_id": "source event or null",
  "token_identity": "canonical token identity",
  "market_subject_id": "explicit pool/market subject identity",
  "source_observed_at": "UTC timestamp or null",
  "received_at": "UTC receipt timestamp",
  "source_freshness": {
    "status": "KNOWN or UNKNOWN",
    "reason": "canonical reason or null"
  },
  "receipt_recency": {
    "reference_time": "UTC timestamp",
    "age_seconds": "DecimalText"
  },
  "volume_window": {
    "source_label": "h24 or null",
    "exact_window": "TimeWindow or null"
  },
  "asset_age": {
    "status": "PRESENT or UNAVAILABLE",
    "amount": "DecimalText or null",
    "unit": "canonical unit or null",
    "reference_semantics": "canonical meaning or null",
    "source_field": "source field or null"
  },
  "pair_created_at": "UTC timestamp or null",
  "raw_payload_digest": "Digest256"
}
```

### 3.1 Required invariants

1. `source_observed_at` is nullable because a provider may not document a
   source observation time. It is never filled from `received_at`,
   `pair_created_at`, `last_trade_timestamp`, HTTP `Date`, processing time, or
   the system clock.
2. `received_at` is always a receipt time. Its name, type, and provenance must
   make it impossible to present it as source observation time.
3. `source_freshness.status` is `KNOWN` only when the source contract
   explicitly states that `source_observed_at` describes the represented source
   fields. It is `UNKNOWN` when `source_observed_at` is null.
4. `source_freshness.reason` is null for `KNOWN` and required for `UNKNOWN`.
5. When `source_observed_at` is present, it must not be later than
   `received_at`. This contract does not make a known source time fresh; it
   only records the source claim.
6. `receipt_recency.age_seconds` is calculated only as
   `reference_time - received_at`. `reference_time` must not precede
   `received_at`. This value is never used as P08 `data_age`.
7. `volume_window.source_label` preserves labels such as `h24`. A null
   `exact_window` means exact UTC endpoints are unknown; endpoints are never
   inferred from the label or receipt time.
8. `asset_age` is token-origin age evidence. `pair_created_at` is separate
   pair or pool age evidence. Pair creation never populates `asset_age`.
9. `asset_age.status = "UNAVAILABLE"` requires all age value fields to be null.
   A consumer may store and display this status only when its own profile
   permits it; it cannot be promoted into a valid P08 v1 observation.
10. `market_subject_id` is explicit and required for each record. Multiple
    pools or pairs produce multiple records or remain in the existing
    inspection report. The contract performs no selection, ranking,
    aggregation, or conflict resolution.
11. The digest covers the approved source payload bytes or the approved
    bounded evidence projection, as declared by the source-specific contract.
    It is not permission to retrieve a payload or repair missing semantics.

### 3.2 What `UNKNOWN` prevents

`source_freshness.status = "UNKNOWN"` permits evidence storage, display,
inspection, and audit. It does not establish:

- P08 `observed_at`;
- P08 `data_age` or stale/fresh status;
- that price, liquidity, volume, and any other fields were observed at the
  same source instant;
- eligibility for a profile requiring point-in-time market semantics;
- P08 v1 `VALID`;
- discovery admission, opportunity scoring, decision creation, Risk/Capital
  approval, or paper admission.

Receipt recency can answer “how recently did this process receive the report?”
It cannot answer “how fresh was the market observation when evaluated?”

## 4. Compatibility with P08 v1

`p08-read-only-market-data-observation-v1` remains unchanged:

- its top-level `observed_at` remains mandatory;
- `observed_at <= availability_at <= cutoff_time` remains mandatory;
- source and provenance links remain exact;
- required fields remain caller/profile controlled;
- explicit unavailable or invalid metric envelopes continue to fail closed;
- no v1 input is auto-upgraded, migrated, or reinterpreted.

The temporal-evidence record may accompany an inspection report or a future
source-adapter result, but it cannot make a v1 observation valid. In particular,
an unknown source time cannot be converted into a v1 timestamp, and a v1
consumer cannot use `receipt_recency` as source freshness.

If a future provider supplies a documented source observation time, exact
volume-window endpoints, and approved asset-age semantics, a separate
source-to-P08 adapter may map those values into P08 v1. That mapping still
requires its own source contract, focused tests, specification audit, and
implementation authorization.

## 5. Allowed and prohibited consumers

### Allowed

- The existing inspection report and UI.
- Offline source qualification and contract-audit tooling.
- Bounded audit/export records.
- A future explicitly authorized consumer whose profile treats source freshness
  as unknown and does not claim point-in-time market eligibility.
- A future source adapter using `source_observed_at` only after its source
  contract documents the covered fields and semantics.

### Prohibited

- Treating `received_at` or `receipt_recency` as P08 `observed_at` or `data_age`.
- Treating pair creation time as token-origin age.
- Treating a rolling label such as `h24` as exact UTC endpoints.
- Choosing one pair by liquidity, volume, arrival order, display metadata, or
  undocumented preference.
- Aggregating pools or combining fields from different source times.
- Feeding this record directly to P05, P06, Risk/Capital, P07, execution,
  ranking, discovery admission, or paper admission.
- Changing P08 v1 `required_fields` to make an incomplete source appear
  accepted.

## 6. One smallest useful implementation

The existing DexScreener inspector already stores source fields, raw-payload
digest, local receipt time, pair creation evidence, explicit unavailable
evidence, and `p08_acceptance: "NOT_ATTEMPTED"`. A second provider adapter would
duplicate that limited evidence-storage/display capability.

The smallest useful implementation should therefore add only:

```text
core/data/market_data_temporal_evidence.py
tests/test_market_data_temporal_evidence.py
tests/fixtures/market_data/temporal_evidence.json
```

The module would define the immutable contract, canonical serialization,
digest verification, and a pure conversion/validation boundary over explicit
inspection evidence. It would not perform HTTP requests, select providers,
construct a P08 v1 observation, or call downstream consumers.

The existing inspection module and its transport remain unchanged. An
integration with the inspector may be added only if the implementation
authorization explicitly names that integration; the first implementation
should be able to validate a deterministic fixture without network access.

### 6.1 Offline acceptance tests

The focused tests must cover:

1. Exact version, field set, canonical text, UTC timestamp, decimal, mapping,
   and digest rules.
2. `source_observed_at = null` producing `source_freshness = UNKNOWN` with an
   explicit reason.
3. A documented source time producing `KNOWN`, while a source time later than
   receipt is rejected.
4. Receipt recency using only an explicit reference time and `received_at`.
5. Proof that receipt time, HTTP `Date`, pair creation time, and
   `last_trade_timestamp` cannot populate `source_observed_at`.
6. Preservation of `h24` or other rolling labels with `exact_window = null`.
7. Rejection of invented or contradictory window endpoints.
8. `asset_age = UNAVAILABLE` remaining distinct from `pair_created_at`.
9. Explicit market-subject identity, duplicate subjects, and conflicting
   subjects without selection or aggregation.
10. Stable serialization and digest behavior across equivalent inputs.
11. A v1 validation regression proving that the new record cannot make an
    observation with unavailable or unknown source timing `VALID`.
12. Zero network calls and no imports from P05, P06, P07, Risk/Capital,
    execution, persistence, or provider clients.

## 7. Concrete capability added

The current inspector answers “what did the source report, and when did this
process receive it?” in a human- and test-inspectable report.

This proposal adds a separately versioned, machine-checkable answer to:

- whether the source supplied a usable observation time;
- whether source freshness is known or unknown;
- how recent receipt was at an explicit reference time;
- whether a rolling volume label has exact or unknown endpoints; and
- whether age evidence is token-origin age or pair age.

It adds no authority and does not create a second path to admission.

## 8. Decision required next

The next decision is whether to authorize implementation of
`p08-market-data-temporal-evidence-v1` using only the three files in Section 6.
Authorization must explicitly keep P08 v1 unchanged and prohibit downstream
admission.

Separately, a future valid P08 market adapter still requires a source whose
documented semantics satisfy P08 v1, or a separately audited and authorized
new P08 contract version. This proposal does not select that source and does
not authorize that work.