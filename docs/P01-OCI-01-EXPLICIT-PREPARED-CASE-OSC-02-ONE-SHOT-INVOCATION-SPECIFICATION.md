# P01-OCI-01 — Explicit Prepared-Case OSC-02 One-Shot Invocation

**Status:** COMPLETE / CLOSED / CI PASS

**Implementation:** COMPLETE / CLOSED / CI PASS — PR #68 squash-merged at
`c041e0e11a98bc477e155ead07a182499a2d1352`; CI #219 PASS (1,701 Python
3.13 tests, whitespace, TypeScript typechecks, workspace builds).

**Contract:** `p01-oci-01-v1`

## 1. Responsibility and entry point

Specify one explicit, in-memory application handoff from the **exact canonical CIP-01 result** to the existing OSC-02 owner. This is an invocation of an already prepared case, never an automatic continuation of CIP-01.

```
controller explicitly invokes OCI(exact P01Cip01Result)
    → validate CIP result and preparedness
    → pass its exact P01Osc02Request to OSC-02.run once
    → preserve exact P01Osc02Result
    → STOP
```

The implemented entry point is `PreparedPaperCaseInvocationService.run(request: P01Oci01Request) -> P01Oci01Result`. It owns only canonical handoff, at-most-once local delegation, and CIP→OSC provenance. OSC-02 retains all RTI-14 eligibility, RTI-15 admission and RTI-16 lifecycle ownership. OCI never reinterprets those outcomes.

## 2. Exact input

Immutable `P01Oci01Request` contains **only**:

- `cip_result: P01Cip01Result` — exact previously produced canonical object;
- `contract_version: str = "p01-oci-01-v1"`.

The OSC invocation ID is exactly `cip_result.request.invocation_id` and `cip_result.osc02_request.invocation_id`; no new ID, alternate request, extra policy, paper facts, approval, or defaults are accepted. Caller/controller responsibility is to obtain the exact CIP result and trigger this handoff **explicitly** at most once for the intended experiment. Construction of the request object has no side effect; only the explicit `run` call may invoke OSC-02.

This in-memory boundary neither reserves IDs nor proves globally unique execution. An external caller may trigger a separate run with the same case; OCI must not claim cross-invocation exactly-once or durable idempotency.

## 3. Validation before owner calls

Enforce exact type and contract versions. Revalidate the exact CIP result with its existing canonical immutable constructor (including nested PFX/PFS, digests, shared RTI-11, request shape and object links) without rerunning any owner service. Preserve **the same object**, not an equal-valued clone. Malformed, tampered, unsupported-version, missing input, mismatch of CIP result/request/OSC invocation identity or canonical digests is standardized `ValueError` before OSC-02. Do not disclose raw nested validation exception text.

If `REQUEST_PREPARED`, require its exact non-null canonical `P01Osc02Request`, empty CIP reasons, correct CIP terminal stage, exact source field identities and canonical `input_digests`. CIP already owns cross-result eligibility/time/policy/source/state checks; OCI validates the canonical result and exact handoff links, without adding a second semantic validator or rebuilding the OSC request.

For other canonical CIP outcomes (`PREFIX_NOT_ELIGIBLE`, `FACTS_NOT_MATERIALIZED`, `PREPARATION_UNAVAILABLE`), return a bounded non-invocation result. They contain no OSC request and OSC-02 call count is zero. Validate input first even for terminal cases; never reinterpret PFX rejection or PFS refusal.

## 4. Exact delegation and cardinality

For one ready CIP result, call exactly `PrevalidatedRiskCapitalSuffixCaller.run(cip_result.osc02_request)` once, passing that exact object by identity. The service may accept an injected OSC-02 seam for focused tests, but must verify callable `run` before invocation. No retry, fallback, second request construction, alternate OSC-01 route, or RTI-04 shortcut.

| Owner or operation | Maximum calls per OCI invocation |
| --- | ---: |
| Existing OSC-02 `run` | 1 if ready; 0 otherwise |
| CIP-01 `prepare`, PFX-01, PFS-01 | 0 |
| RTI-11/12/13/14 directly | 0 |
| RTI-15/16 or lifecycle directly | 0 |
| OSC-01, OSP, RTI-03/04, provider/persistence | 0 |

Within the **single** OSC-02 call, OSC-02's existing contract permits RTI-15 at most once and RTI-16 at most once, with RTI-16 only after `ADMISSION_MATERIALIZED`. OCI must not pre-execute or call them again. The internal owner cardinality is OSC-02's responsibility and remains unchanged.

## 5. Owner result validation and outcomes

A returned OSC object must be the exact `P01Osc02Result`, canonical by its existing constructor, and its `request is cip_result.osc02_request` (object identity). Match contract, invocation ID and canonical input digests. Preserve the **exact returned object**; no replacement, cloning, recomputation, or semantic rewrite. The closed OCI outcomes are:

| OCI outcome | Condition | OSC calls | Exact OSC result |
| --- | --- | ---: | --- |
| `OSC_RESULT_RETURNED` | One valid canonical OSC-02 result, including its success **or terminal stop** | 1 | Present by identity |
| `CASE_NOT_PREPARED` | Canonical CIP result has a non-ready outcome | 0 | Absent |
| `OSC_UNAVAILABLE` | Unexpected OSC exception or invalid/noncanonical owner return | 1 | Absent |

OCI `OSC_RESULT_RETURNED` means only that OSC-02 returned a canonical result. It does **not** mean admission, lifecycle, fill, trade, profit, persistence, or economic success. The exact OSC outcome (`LIFECYCLE_RETURNED`, `UPSTREAM_STOPPED`, or `OWNER_UNAVAILABLE`), reasons, stage and exact RTI-15/16 references remain in that owner result. If OSC-02 reports `OWNER_UNAVAILABLE`, OCI still returns `OSC_RESULT_RETURNED` with that exact canonical result: no reclassification, fallback or retry.

OSC-02 `ValueError` is a standardized validation failure `ValueError`, never an ordinary bounded outcome; do not leak its raw message. Unexpected owner exception or invalid/noncanonical owner return becomes `OSC_UNAVAILABLE` with finite safe reason `OSC-02_UNAVAILABLE`. Cancellation/interrupt propagates. Invalid injected seam is `ValueError` before service invocation.

## 6. Output, identity and deterministic provenance

Immutable `P01Oci01Result` contains:

- the exact `P01Oci01Request`, through which the exact CIP/PFX/PFS results remain reachable;
- one closed OCI outcome; finite safe reason code(s); a terminal stage (`CIP-01` for non-ready, `OSC-02` otherwise);
- optional **exact** `P01Osc02Result` only for `OSC_RESULT_RETURNED`;
- contract `p01-oci-01-v1` and deterministic SHA-256 `result_digest`.

Recommended finite reasons: empty for returned canonical OSC result, `CASE_NOT_PREPARED` for canonical CIP stop, and `OSC-02_UNAVAILABLE` for owner unavailability. Exact upstream CIP and OSC reasons remain in the preserved owner objects; no invented approval, lifecycle, or failure reason. Output constructor validates outcome/terminal stage/reasons/result presence and exact object links.

Digest binds: OCI contract, outcome, safe reasons and stage; CIP contract, outcome, invocation ID and result digest; explicit absence/presence of the exact prepared OSC request; on success the exact OSC contract, outcome, reasons, terminal stage, result digest and canonical input digest map; explicit absence of OSC result otherwise. CIP result digest itself binds PFX/PFS and RTI-11/14, selected source, simulation policy, exact paper inputs and OSC request digests. OSC result digest binds its RTI-14/15/16 chain. Canonical serialization fixes field names/order and nulls; no wall clock, object address, provider, environment, exception text, retry counter or mutable global state.

Same canonical input and same canonical OSC owner response give the same OCI digest. Different valid OSC owner responses may produce different OCI digests; OCI does not fabricate an OSC response or promise that a later invocation reproduces an owner outcome. Neither digest is durable replay storage, execution proof, globally unique invocation reservation, nor economic provenance.

## 7. Failure boundary and STOP

Input validation precedes eligibility and delegate calls. A canonical terminal CIP result gives `CASE_NOT_PREPARED`, not validation failure. Malformed/tampered/identity/version mismatch and OSC owner `ValueError` remain validation failures. Unexpected/invalid owner response gives bounded `OSC_UNAVAILABLE`. No retries and no state shared between invocations.

Hard STOP is **the exact canonical `P01Osc02Result` in memory**, if OSC-02 returns one; if not ready or unavailable, STOP at OCI's bounded result. An OSC lifecycle result, if present, stays owned by OSC-02/RTI-16. No automatic persistence/OSP, readback, P08 learning, full replay archive, publication or subsequent gate is added.

Forbidden: autonomous discovery/selection, provider/network/polling, hidden paper facts, recurring invocation, scheduler/worker/queue, API/WebSocket/dashboard, RTI-04, wallet/signing/RPC/DEX, transaction/broadcast, live trading and economic realization. G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED; G3/G4/P09 remain NOT AUTHORIZED.

## 8. Future implementation and focused verification

The controller authorized bounded implementation: one thin application module,
one focused test module, minimal application export and governance closure.
CIP, OSC, RTI, PFS and Risk/Capital owners remain unchanged; operational paper
experiment invocation is not authorized by implementation tests.

Test matrix: canonical ready CIP passes exact same request object once; successful OSC lifecycle result remains exact; each OSC canonical terminal outcome remains exact without wrapper rewriting; each canonical CIP non-ready outcome causes zero calls; tampered CIP/version/digest/identity fails before owner; owner `ValueError` standardized; unexpected owner exception and wrong/noncanonical/foreign-request result bounded with one call; deterministic digest for fixed owner response; no repeated calls on failure; zero direct PFX/PFS/RTI/lifecycle/persistence/provider calls. Relevant regression: CIP-01 and OSC-02 focused suites plus RTI-15/16 identity/validation tests. No real provider or runtime invocation in tests.

`SPECIFICATION COMPLETE; LIMITED IMPLEMENTATION IN REVIEW`
