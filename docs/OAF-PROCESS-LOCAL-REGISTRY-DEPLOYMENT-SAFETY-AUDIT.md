# OAF Process-Local Registry Deployment Safety Audit

Status: IMPLEMENTATION HARDENING / CONTROLLED PAPER ONLY

Repository checkpoint: `bdcaedcbd7260758d6619591d4311fd2039edcbf` (main after HR-FND-04).

## Repository evidence

- `OperatorPaperCaseRegistry` explicitly documents itself as finite, process-local,
  identity-preserving operational control state rather than durable persistence.
- `OperatorPaperCaseRecord` retains the exact prepared case object, and terminal
  run validation requires the OCI request to retain the exact prepared CIP object
  identity.
- run-once and persist-once services depend on that same in-memory record and
  exact lifecycle-bearing object graph.
- RTI-03 durable lifecycle persistence is separate and database-backed; it does
  not reconstruct an active pre-run OAF case.
- the repository `.replit` currently names an autoscale deployment target, which
  cannot by itself guarantee that every request for one active case reaches the
  same process or survives process restart.

## Decision

The current OAF mutation path is authorized only for one stable application
process over the entire prepare -> review -> run -> persist lifetime.

Staging/production must fail closed unless the deployer explicitly acknowledges
this process-local constraint. Development and test remain enabled so repository
tests and controlled local work keep their existing behavior.

`OPERATOR_PROCESS_LOCAL_REGISTRY_ACK=true` is only an acknowledgement. It does
not create sticky routing, restart durability, distributed locking, or exactly-
once semantics across processes.

## Why no database-backed registry is added here

A naive serialize/deserialize registry would break or silently weaken current
identity invariants. The active object graph contains canonical owners whose
application wrappers deliberately validate shared exact object identity, not
only digest equality. Pickle-style persistence would also be an inappropriate
trusted-runtime boundary.

A future durable/reconstructable active-case design therefore requires its own
explicit contract deciding:

1. which canonical objects are persisted;
2. whether exact identity constraints are replaced by canonical digest/lineage
   equivalence at specific boundaries;
3. reconstruction/version-migration behavior;
4. atomic distributed claim semantics for run and persist;
5. restart and uncertain-outcome behavior.

No such redesign is authorized by this hardening gate.

## Readiness behavior

When an operator bearer is configured in staging/production but the process-
local acknowledgement is absent:

- the active OAF registry and prepare/run/persist services are not created;
- `/ready` returns not-ready with `process_local_ack_required`;
- authenticated case review fails with bounded `503` instead of dereferencing a
  missing registry.

Existing durable paper lifecycle readback remains database-owned and available
under its existing contract.

## Authority

This gate changes deployment safety only. It does not add autonomous discovery,
polling, retries, distributed workers, wallet/signing, DEX routing, settlement,
economic realization, or live trading.

G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED. G3/G4/P09 remain NOT
AUTHORIZED.
