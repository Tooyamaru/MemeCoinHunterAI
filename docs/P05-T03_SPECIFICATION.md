# P05-T03 — Opportunity Hard-Risk and Disqualification Boundary

## 1. Purpose and scope

P05-T03 is the deterministic hard-risk boundary for one normalized
opportunity candidate. It converts the already-derived upstream eligibility
status, together with the normalized candidate state, into a bounded viability
outcome:

- `ELIGIBLE`
- `DISQUALIFIED`
- `INSUFFICIENT_EVIDENCE`

This boundary consumes existing contracts only. It does not collect, inspect,
reevaluate, or reinterpret the underlying safety evidence. It preserves the
provenance supplied by the upstream eligibility output and produces an
immutable, versioned result.

The implementation authority is:

- `core/opportunity/opportunity_risk.py`
- `core/opportunity/opportunity_normalization.py`
- `core/risk/safety_evidence.py`
- `core/risk/safety_eligibility.py`
- `tests/test_opportunity_risk.py`

## 2. Upstream and downstream contracts

### Upstream

The evaluator accepts exactly one `NormalizedOpportunityCandidate` from
P05-T02. The normalized candidate preserves a P05-T01 opportunity candidate
and its upstream references, including the derived safety eligibility output.

The consumed normalized candidate must use contract version
`p05-t02-v1`. Its candidate must be a valid P05-T01 candidate, and its
eligibility must be a `DerivedEligibilityOutput` with a supported
`EligibilityStatus` and mandatory evidence references.

P05-T03 relies on the upstream `DerivedEligibilityOutput` contract and its
already-derived `ELIGIBLE`, `INELIGIBLE`, or `UNKNOWN` status. P05-T03 does not
re-run P03-T02 evaluation or P03-T03 eligibility derivation.

### Downstream

The result is a `CandidateRiskEvaluation`. It is a hard-risk/viability
boundary result only. It is not authoritative, is not a decision, and does
not authorize or request any action.

## 3. Exact input contract

The primary function is:

```python
evaluate_hard_risks(
    candidate: NormalizedOpportunityCandidate,
    *,
    evaluated_at: datetime | None = None,
) -> CandidateRiskEvaluation
```

`evaluate_candidate_risk` is an alias of the same evaluator.

The input must satisfy all of the following checks implemented by the
boundary:

1. It is a `NormalizedOpportunityCandidate`.
2. Its normalized-candidate contract version is `p05-t02-v1`.
3. `candidate_id` is a non-empty string.
4. The preserved candidate representation digest is a non-empty string.
5. The candidate state is an `OpportunityCandidateState`.
6. Eligibility is a `DerivedEligibilityOutput`.
7. Eligibility status is an `EligibilityStatus`.
8. Eligibility contains at least one evidence reference, and every reference
   is a non-empty string.
9. The candidate contains at least one valid `OpportunityUpstreamReference`.
10. The normalized candidate's canonical and deterministic representations are
    equal.

The input's eligibility status is one of:

- `EligibilityStatus.ELIGIBLE`
- `EligibilityStatus.INELIGIBLE`
- `EligibilityStatus.UNKNOWN`

The candidate reference time and any explicit `evaluated_at` value must be
timezone-aware. Invalid input or an unsupported status raises `ValueError`;
the evaluator does not substitute a permissive result.

## 4. Existing upstream eligibility mapping

The implementation applies this exact mapping:

| Upstream eligibility status | Candidate state condition | Viability status | Rejection reason | Boundary risk flag |
|---|---|---|---|---|
| `ELIGIBLE` | `VALID` | `ELIGIBLE` | `None` | none |
| `ELIGIBLE` | anything other than `VALID` | `INSUFFICIENT_EVIDENCE` | `INSUFFICIENT_CRITICAL_EVIDENCE` | `INSUFFICIENT_CRITICAL_EVIDENCE` |
| `INELIGIBLE` | any valid candidate state | `DISQUALIFIED` | `UPSTREAM_INELIGIBLE` | `UPSTREAM_INELIGIBLE` |
| `UNKNOWN` | any valid candidate state | `INSUFFICIENT_EVIDENCE` | `UNKNOWN_UPSTREAM_ELIGIBILITY` | `UNKNOWN_UPSTREAM_ELIGIBILITY` |

`OpportunityCandidateState.ELIGIBLE` is an enum alias for the value
`VALID`; the implementation specifically checks the `VALID` state.

For a non-eligible result, `rejection_reason` is required. For an eligible
result, `rejection_reason` must be `None`.

## 5. Fail-closed behavior

P05-T03 never turns uncertainty or an invalid candidate into eligibility:

- An `INELIGIBLE` upstream status always produces `DISQUALIFIED`.
- An `UNKNOWN` upstream status always produces `INSUFFICIENT_EVIDENCE`.
- An upstream `ELIGIBLE` status produces `ELIGIBLE` only when the candidate
  state is `VALID`.
- An upstream `ELIGIBLE` status with any other candidate state produces
  `INSUFFICIENT_EVIDENCE`.
- Missing or malformed mandatory evidence references reject the input with
  `ValueError`.
- A non-`NormalizedOpportunityCandidate`, an unsupported contract version, an
  invalid state/status, or a non-deterministic representation rejects the
  input with `ValueError`.

## 6. Exact output fields

`CandidateRiskEvaluation` is a frozen dataclass with exactly these fields:

| Field | Type | Contract behavior |
|---|---|---|
| `candidate_id` | `str` | Copied from the normalized candidate. |
| `evaluated_at` | `datetime` | The effective evaluation time, normalized to UTC. |
| `input_candidate_digest` | `str` | Copied from `candidate.representation_digest`. |
| `risk_flags` | `tuple[str, ...]` | Sorted, unique boundary and preserved reason flags. |
| `viability_status` | `CandidateViabilityStatus` | The hard-risk outcome. |
| `rejection_reason` | `str \| None` | `None` only for `ELIGIBLE`; required otherwise. |
| `evidence_references` | `tuple[str, ...]` | Copied from upstream eligibility, then sorted and deduplicated by the immutable result. |
| `evaluator_version` | `str` | `p05-t03-rules-v1`. |
| `contract_version` | `str` | `p05-t03-v1`. |

The result exposes convenience predicates `is_eligible`,
`is_disqualified`, and `is_insufficient_evidence`. It also exposes
`is_authoritative`, which is always `False`.

The result has no score, ranking, decision, action, buy, sell, or hold field.

## 7. `CandidateViabilityStatus` values

The only supported values are:

| Enum member | Value | Meaning in this boundary |
|---|---|---|
| `CandidateViabilityStatus.ELIGIBLE` | `ELIGIBLE` | Upstream eligibility is `ELIGIBLE` and candidate state is `VALID`. |
| `CandidateViabilityStatus.DISQUALIFIED` | `DISQUALIFIED` | Upstream eligibility is `INELIGIBLE`. |
| `CandidateViabilityStatus.INSUFFICIENT_EVIDENCE` | `INSUFFICIENT_EVIDENCE` | Upstream eligibility is `UNKNOWN`, or upstream eligibility is `ELIGIBLE` while candidate state is not `VALID`. |

These values do not represent a trading decision or authorization.

## 8. `CandidateRiskFlag` values

The boundary defines exactly these named flags:

| Enum member | Value | Used when |
|---|---|---|
| `CandidateRiskFlag.UPSTREAM_INELIGIBLE` | `UPSTREAM_INELIGIBLE` | Upstream eligibility is `INELIGIBLE`. |
| `CandidateRiskFlag.UNKNOWN_UPSTREAM_ELIGIBILITY` | `UNKNOWN_UPSTREAM_ELIGIBILITY` | Upstream eligibility is `UNKNOWN`. |
| `CandidateRiskFlag.INSUFFICIENT_CRITICAL_EVIDENCE` | `INSUFFICIENT_CRITICAL_EVIDENCE` | Upstream eligibility is `ELIGIBLE`, but candidate state is not `VALID`. |

For a non-eligible mapping, the applicable boundary flag is always included.
When the upstream eligibility output contains more than one reason code, the
additional upstream reason codes are preserved in `risk_flags` alongside the
boundary flag. Flags are sorted and deduplicated by the result contract. With
zero or one upstream reason code, no additional reason code is added by this
boundary.

P05-T03 does not define or infer safety domains. Any preserved reason codes
remain upstream-provided values.

## 9. Contract and evaluator versions

The immutable result must use:

```text
contract_version:  p05-t03-v1
evaluator_version: p05-t03-rules-v1
```

The input normalized candidate must use the upstream contract version:

```text
p05-t02-v1
```

Unsupported P05-T03 contract or evaluator versions are rejected by the result
contract, and an unsupported P05-T02 input contract is rejected by the
evaluator.

## 10. Deterministic timestamp behavior

P05-T03 has no wall-clock dependency:

- If `evaluated_at` is omitted, the evaluator uses
  `candidate.reference_time`.
- If `evaluated_at` is provided, that explicit value is used.
- The effective timestamp must be timezone-aware.
- The effective timestamp is normalized to UTC.

Repeated evaluation of the same candidate without an explicit timestamp
therefore produces the same timestamp and the same canonical result.

## 11. Input candidate digest and provenance

`input_candidate_digest` is exactly the normalized candidate's
`representation_digest`; P05-T03 does not replace it with a new candidate
identity or recompute a different input identifier.

The result's `evidence_references` come directly from
`candidate.eligibility.evidence_references`, with the result contract applying
tuple conversion, sorting, and deduplication. The evaluator does not discard
the upstream evidence references when the result is disqualified or
insufficient.

The normalized candidate itself preserves its upstream references and
representation digest. P05-T03 does not mutate the candidate, its eligibility
output, or the upstream evidence.

## 12. Immutability and versioning

`CandidateRiskEvaluation` is declared with `@dataclass(frozen=True)`.
Its risk flags and evidence references are stored as tuples, and its
canonical representation is an immutable mapping. The canonical
representation contains all output fields in this specification, using the
enum value for `viability_status`.

The result exposes:

- `canonical_representation`
- `deterministic_representation`
- `representation_digest`
- `digest`

The representation digest is a deterministic SHA-256 digest of the canonical
representation. Equivalent repeated evaluations produce equal results,
canonical representations, and representation digests.

Version fields are part of the canonical representation, so changing the
contract or evaluator version is an explicit versioned contract change rather
than an implicit mutation.

## 13. Explicit non-responsibilities

P05-T03 does not:

- collect or perform external I/O;
- access a network, provider, RPC, API, database, wallet, or execution system;
- reevaluate upstream safety evidence;
- resolve evidence conflicts or invent evidence domains;
- add scoring, ranking, weighting, prioritization, prediction, or opportunity
  quality calculations;
- produce `BUY`, `SELL`, `HOLD`, or any other decision;
- authorize capital, a trade, a wallet action, or execution;
- sign, broadcast, or submit anything;
- perform capital or position management;
- provide authoritative safety proof or caller authorization;
- replace the upstream candidate digest or evidence provenance.

## 14. Testable acceptance criteria

The existing `tests/test_opportunity_risk.py` tests define the acceptance
behavior for this boundary. The implementation satisfies the following
criteria:

1. A candidate with all required upstream evidence passing produces an
   `ELIGIBLE` result with no risk flags and no rejection reason.
2. An `INELIGIBLE` upstream result produces `DISQUALIFIED` with
   `UPSTREAM_INELIGIBLE`.
3. Multiple upstream failure reasons are preserved alongside the boundary
   risk flag, and evidence references are preserved.
4. An `UNKNOWN` upstream result is never eligible and produces
   `INSUFFICIENT_EVIDENCE` with
   `UNKNOWN_UPSTREAM_ELIGIBILITY`.
5. A candidate that is not `VALID` cannot pass merely because upstream
   eligibility is `ELIGIBLE`; it produces
   `INSUFFICIENT_EVIDENCE` with
   `INSUFFICIENT_CRITICAL_EVIDENCE`.
6. Missing or invalid candidate input raises `ValueError`.
7. Malformed normalized evidence references are rejected.
8. Repeated evaluation without a wall-clock dependency is deterministic,
   including timestamp, canonical representation, and digest.
9. An explicit evaluation time is accepted and normalized to UTC.
10. The candidate ID, input candidate digest, and upstream evidence references
    are preserved in the result.
11. The result is immutable, has no decision/action/score/ranking fields, and
    reports `is_authoritative is False`.
12. Evaluating a candidate does not mutate the candidate or its upstream
    eligibility/evidence provenance.

The focused verification command for P05-T03 is:

```text
uv run pytest -q \
  tests/test_opportunity_candidate.py \
  tests/test_opportunity_normalization.py \
  tests/test_opportunity_risk.py
```