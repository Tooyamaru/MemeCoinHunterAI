# Post-P01-RTI-11 Next-Gate Selection

## Status

- **Base state:** P01-RTI-11 COMPLETE / CLOSED / CI PASS
- **Selection result:** P01-RTI-12 recommended and approved for formal specification
- **Recommended gate:** P01-RTI-12 — Deterministic P05 Opportunity-Context Continuation
- **Implementation at selection time:** NOT AUTHORIZED

## Repository finding

P01-RTI-11 terminates at P05-T05.

P06-T02 and P01-RTI-01 both consume P05-T08 `OpportunityContext`.

P05-T06, P05-T07, and P05-T08 are already complete/closed deterministic local
owners without external I/O. Therefore a direct jump from P05-T05 to a concrete
runtime caller, P06, or paper-path composition would skip the existing
P05-T05 → P05-T08 dependency chain.

## Candidate assessment

| Candidate | Readiness | Primary risk | Decision |
| --- | --- | --- | --- |
| Concrete RTI-11 caller | Partial | Caller/config/credential authority unresolved | Defer |
| P05-T05 → P05-T08 continuation | High | Low | **Recommended** |
| Opportunity → P06 | Not yet ready | Would skip P05-T08 dependency | Defer until P05-T08 continuation |
| Opportunity → paper path | Low | High sequencing/authority risk | Defer |
| Persistence/publication | Low | New authority and side effects | Ineligible |
| Read-only inspection | Low current value | No persistence owner for this surface | Defer |
| Additional governance hardening | High | Low | Available but lower sequencing value |

## Recommended bounded shape

P01-RTI-12 should:

1. accept exactly one canonical `P01Rti11CompositionResult`;
2. process only exact `COMPOSED`;
3. pass exact `composition.score` once to P05-T06;
4. create a fresh invocation-local P05-T07 history;
5. append the exact record once and require `STORED`;
6. pass the exact record and exact history once to P05-T08;
7. stop at exact `OpportunityContext`;
8. not execute RTI-11, provider, P06, paper lifecycle, persistence, API, or any runtime caller.

## Residual decisions identified by selection

Formal specification must lock:

- handling of valid RTI-11 non-`COMPOSED` results;
- minimal RTI-12 result vocabulary;
- validation failure versus bounded owner failure semantics;
- exact deterministic result-digest binding;
- owner exception semantics;
- fresh history isolation with no shared mutable state.

## Governance boundary

The recommended gate must not open:

- concrete provider/runtime caller;
- persistence/publication;
- API/WebSocket;
- P06;
- Risk/Capital;
- P07/paper lifecycle;
- worker/scheduler/queue;
- dashboard/Hunter Room;
- wallet/signing/RPC/DEX;
- execution/live trading;
- economic realization;
- G2/G3/G4/P09.

G2 remains **BLOCKED / UNRESOLVED / NOT AUTHORIZED**.

## Controller disposition

The controller approved the P01-RTI-12 direction, authorized formal
specification, later approved the completed formal specification, and
separately authorized limited implementation.

This selection document itself creates no implementation or runtime behavior.
