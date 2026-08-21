# P05-T08 — Final Evidence-First Opportunity Context

**Status:** COMPLETE / CLOSED / AUDITED PASS
**Phase:** P05 — Opportunity Engine
**Task:** P05-T08
**Provider posture:** Provider-neutral; deterministic; pure/local; no external I/O
**Contract version:** `p05-t08-v1`
**Evaluator version:** `p05-t08-context-v1`

## 1. Purpose and scope

P05-T08 is the final authorized P05 boundary before P06. It links one validated
P05-T06 evidence-first opportunity record to its P05-T07 local history and
exposes the complete upstream context needed by the future Decision Engine.

```text
P05-T06 Opportunity Record
        ↓
P05-T07 Opportunity Record History
        ↓
P05-T08 Final Evidence-First Opportunity Context
        ↓
P06 Decision Engine
```

The output is analytical context, not a trading decision. It does not aggregate
multiple candidates or alter any upstream contract.

## 2. Input and output contract

The materializer accepts exactly one `OpportunityRecord` and one
`OpportunityRecordHistory`. The resulting frozen `OpportunityContext` preserves
by identity:

- candidate, chain, token, and point-in-time reference identity;
- the P05-T03 risk evaluation, status, flags, rejection/reason context, and
  evidence references;
- the P05-T04 feature evaluation and exact authorized feature identities;
- the P04 signal snapshot and provenance;
- the P05-T05 score, ruleset, evaluator, and digest provenance;
- the P05-T06 record and digest;
- the P05-T07 history and digest linkage; and
- timestamps and any uncertainty/invalidation context already represented by
  upstream contracts.

## 3. Validation and fail-closed behavior

The boundary rejects non-canonical, tampered, unsupported, incomplete, or
inconsistent inputs. It validates all linked P05-T03 through P05-T07 contract
and evaluator versions, exact feature `(feature_id, feature_version)` pairs,
candidate identity, record digest, history digest, and direct object identity.

No synthetic evidence, replacement status, decision, confidence, ranking,
authorization, or execution meaning is created.

## 4. Determinism, immutability, and non-scope

P05-T08 has no wall-clock reads, randomness, filesystem, network, provider,
API, database, RPC, wallet, LLM, signing, broadcasting, or mutation behavior.
Equivalent validated inputs produce equivalent canonical representations and
SHA-256 digests.

It does not rank, compare, prioritize, aggregate, predict probability of
profit, produce BUY/SELL/HOLD/WATCH, authorize capital or execution, or bypass
the future deterministic Decision Engine.

## 5. Acceptance criteria

1. One validated P05 record and one validated P05-T07 history are required.
2. Complete risk, feature, signal, score, record, and history provenance is
   preserved by identity.
3. Digests, contract versions, evaluator versions, timestamps, and identity
   linkages are exact and deterministic.
4. Tampering, unsupported versions, invalid feature authorization, invalid risk
   state, incomplete evidence, and inconsistent linkage fail closed.
5. The frozen context has no decision, ranking, authorization, or execution
   semantics.