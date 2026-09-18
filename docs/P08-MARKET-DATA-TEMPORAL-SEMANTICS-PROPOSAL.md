# P08 — Market-Data Temporal Semantics Contract Proposal

**Status:** CORRECTED / BOUNDED IMPLEMENTATION IN PROGRESS
**Date:** 2026-09-18
**Existing contract preserved:** `p08-read-only-market-data-observation-v1`
**Proposed contract:** `p08-market-data-temporal-evidence-v1`

## 1. Decision and bounded scope

This proposal authorizes only a pure conversion and validation boundary over
the current `dexscreener-inspection-v1` report. It does not change P08 v1,
the inspector, the API, the UI, or any downstream consumer.

The implementation is limited to:

```text
core/data/market_data_temporal_evidence.py
tests/test_market_data_temporal_evidence.py
tests/fixtures/market_data/temporal_evidence.json
```

The implementation performs no network access, provider calls, persistence,
subprocess execution, dependency installation, source selection, ranking,
aggregation, deduplication, analysis, decision, authorization, paper
admission, execution, settlement, accounting, or realized-P&L behavior.

## 2. Evidence boundary

The existing inspector already reports:

- the source-shaped pair payload;
- the transport receipt time;
- the raw-payload SHA-256 supplied by the inspector;
- pair creation source evidence;
- explicit unavailable evidence;
- `p08_acceptance: "NOT_ATTEMPTED"`.

The temporal boundary makes those distinctions immutable and
machine-checkable. It does not create missing market semantics.

P08 v1 still owns its own required envelopes, profile-controlled required
fields, `observed_at`, freshness, provenance, and acceptance rules. The
fixture’s four structural metric names are not a universal production
requirement that all be `PRESENT` for every future profile.

## 3. Current-source temporal contract

The implementation supports only the current DexScreener inspector contract:

```text
tool_version = "dexscreener-inspection-v1"
source       = "DexScreener"
p08_acceptance = "NOT_ATTEMPTED"
```

Unsupported versions, unsupported sources, attempted P08 acceptance,
contradictory P08 timing evidence, malformed reports, and contradictory pair
identity fail closed.

### 3.1 Source time and receipt time

`source_observed_at` is always explicit `null`. This first implementation does
not implement `KNOWN`, source attestations, or generic source-coverage claims.
Every output uses:

```text
source_freshness.status = "UNKNOWN"
source_freshness.reason =
  "NO_DOCUMENTED_MARKET_FIELD_OBSERVATION_TIMESTAMP"
```

The transport `receipt.received_at` is preserved as `received_at`. Receipt
recency is computed only as:

```text
evaluation_time - received_at
```

`evaluation_time` is caller-supplied, timezone-aware, and rejected when it
precedes receipt. Receipt recency never becomes P08 `observed_at` or `data_age`.

Receipt time, pair creation data, trade timestamps, HTTP dates, processing
time, and the system clock cannot populate `source_observed_at`.

### 3.2 Pair records and identities

Conversion produces one temporal record for every returned pair, preserving
report order. It never selects, ranks, aggregates, or silently deduplicates.

Each record preserves:

- request `chain_id` and `token_address` as explicit chain/token identity;
- `market_subject_id = "{chain_id}:{pairAddress}"`, preserving address case;
- an `occurrence_id` derived from source, raw-payload digest, report index,
  market subject, and the source pair projection.

The market subject identifies the pair identity. The occurrence identity keeps
duplicate or conflicting entries separately identifiable. `source_event_id`
remains `null` because the current report does not supply one.

### 3.3 Volume, age, and digest evidence

`volume_window.source_label` preserves `h24` when the current pair report
contains that rolling label. `exact_window` is always `null`; no UTC endpoints
are inferred.

`asset_age` is always `UNAVAILABLE` with the inspector’s documented
token-origin reason. Pair creation is preserved separately as
`pair_created_at_source_value`, without converting or asserting timestamp-unit
semantics. Pair creation never populates token-origin age.

The inspector’s `raw_payload_sha256` is preserved as supplied. The temporal
module does not claim independent raw-byte verification because it receives the
report, not the original response bytes. A deterministic digest of the bounded
temporal evidence projection is available for replay and comparison.

## 4. Output and compatibility rules

The output is an immutable report containing a tuple of immutable temporal
records. A valid report with zero pairs is an explicit empty result.

The output always exposes `p08_acceptance: "NOT_ATTEMPTED"`. Temporal evidence
cannot construct, upgrade, validate, or admit a
`p08-read-only-market-data-observation-v1` observation.

`UNKNOWN` source freshness permits evidence preservation, inspection, and audit
only. It does not establish P08 validity, point-in-time market semantics,
discovery admission, opportunity analysis, P06 decisions, Risk/Capital
approval, P07 simulation admission, paper admission, or execution authority.

## 5. Focused acceptance tests

The focused offline tests cover:

1. conversion of a report produced by the actual inspector with mocked transport;
2. empty reports and one-record-per-pair multi-pair conversion;
3. duplicate and conflicting pair preservation;
4. identity, version, timestamp, digest-format, and contradictory-evidence rejection;
5. receipt-time equality, recency, and future-receipt rejection;
6. UNKNOWN source freshness despite recent receipt;
7. no receipt, pair, or trade-time substitution for source observation time;
8. unavailable token-origin age and unknown rolling volume endpoints;
9. immutable inputs, deterministic output, canonical serialization, and digest stability;
10. no automatic P08 acceptance or downstream authorization.

## 6. Remaining boundary

This implementation does not connect market data to analysis or paper trading.
A future source with documented field-level observation time, exact volume
window endpoints, and approved token-origin semantics would require a separate
source contract, focused tests, specification audit, and implementation
authorization before any P08 v1 mapping could be considered.