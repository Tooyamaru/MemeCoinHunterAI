# HR-FND-06 — Manual Prepare Payload Validation

Status: IMPLEMENTATION / CONTROLLED PAPER ONLY

## Purpose

Expose the authenticated no-I/O prepare payload validation endpoint directly
inside Hunter Room so the operator can verify local canonical input structure
before invoking the trusted prepare flow.

## Behavior

- the operator explicitly presses `Validate`;
- Hunter Room parses the current JSON payload locally;
- one authenticated POST is sent to
  `/api/v1/operator/paper-cases/validate`;
- a valid response shows bounded candidate/pool/selected-observation identity;
- the UI explicitly states that no provider, eligibility, RTI-11, PFX/PFS/CIP
  or case mutation was performed;
- validation is never automatic and does not enable a hidden prepare action.

`VALID` is not a market or eligibility verdict. It only means the explicit
payload passed the same transport/canonical decoder used by the real prepare
route.

## Boundary

This is operator usability only. No provider/source call, prepare mutation,
retry/polling, autonomous discovery, worker/scheduler, wallet/signing, DEX
routing, settlement, live trading or economic authority is added.

G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED. G3/G4/P09 remain NOT
AUTHORIZED.
