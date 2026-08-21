# P05-T07 — Evidence-First Opportunity Record History

**Status:** COMPLETE / CLOSED / AUDITED PASS
**Phase:** P05 — Opportunity Engine
**Task:** P05-T07
**Provider posture:** Provider-neutral; deterministic; local; no external I/O
**Contract version:** `p05-t07-v1`

## 1. Purpose and scope

P05-T07 stores already-validated P05-T06 `OpportunityRecord` values in a
deterministic local history. It preserves each record and all nested evidence
by identity. It does not calculate, rank, compare, decide, authorize, or
execute.

```text
P05-T06 Evidence-First Opportunity Record
        ↓
validate and retain complete immutable record
        ↓
P05-T07 Opportunity Record History
```

The history is keyed by the record representation digest. Repeated insertion
of the same canonical record is reported as a duplicate and does not mutate
the stored value.

## 2. Input and output contract

The local insertion boundary accepts exactly one `OpportunityRecord` at a time.
It produces an immutable `OpportunityRecordHistoryResult` containing:

- `STORED`, `DUPLICATE`, or `INVALID_INPUT` outcome;
- whether the insertion was accepted;
- the directly preserved record, when valid;
- the complete deterministic history view;
- existing upstream reason context where applicable;
- the history digest and `p05-t07-v1` contract version.

The stored record retains candidate identity, hard-risk state and evidence,
authorized feature identity/version, signal provenance, score provenance,
timestamps, digests, contract versions, evaluator versions, and any upstream
uncertainty or invalidation context already represented by those contracts.

## 3. Validation and fail-closed behavior

Insertion rejects non-record inputs, unsupported versions, tampered records,
non-canonical representations, invalid nested provenance, and invalid or
uncertain upstream records. No replacement status, reason code, confidence,
decision, ranking, or execution meaning is invented.

The history validates a supplied record without reconstructing or normalizing
its upstream evidence. It preserves the original record object by identity.

## 4. Determinism and immutability

P05-T07 is pure with respect to the supplied record and has no wall-clock,
randomness, filesystem, database, network, provider, API, wallet, or external
service access. Results and history views are frozen tuples and deterministic
canonical digests. History ordering is based on canonical record
representations, not insertion timing.

## 5. Explicit non-responsibilities

P05-T07 does not:

- rank or compare candidates;
- aggregate or reduce candidate sets;
- produce BUY, SELL, HOLD, WATCH, or another action;
- produce confidence or a profit probability;
- authorize capital or execution;
- call providers or perform external I/O;
- perform LLM/AI decision behavior; or
- implement P06.

## 6. Acceptance criteria

1. Valid P05-T06 records are stored and preserved by identity.
2. Canonical representation and history digest are deterministic.
3. Duplicate records do not create a second history entry.
4. Tampered, invalid, uncertain, unsupported, or non-canonical inputs fail closed.
5. Upstream risk, feature, signal, score, timestamp, and provenance context is
   retained without mutation.
6. No ranking, decision, authorization, execution, provider, or AI behavior is
   introduced.