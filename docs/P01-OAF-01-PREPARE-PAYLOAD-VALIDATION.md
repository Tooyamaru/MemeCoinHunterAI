# P01-OAF-01 — Prepare Payload Validation

Status: IMPLEMENTATION / AUTHENTICATED / NO PROVIDER I/O

## Purpose

Allow the operator to verify that one explicit Hunter Room prepare payload
matches the existing transport and canonical constructor constraints before
the trusted prepare path is allowed to touch Solana/RTI-11 or create a case.

## Endpoint

`POST /api/v1/operator/paper-cases/validate`

The endpoint uses the same `OperatorPrepareRequest` transport model and
`decode_operator_prepare_request()` decoder used by the real prepare route.
It therefore validates the explicit target, times, policy seed, risk/capital
states, execution observation, simulation configuration, replay identity,
simulation policy and genesis input through their existing constructors.

A valid response projects only a bounded identity summary and states:

- `provider_connectivity_checked=false`;
- `mutates_case=false`;
- `simulation_only=true`.

The endpoint does not require the trusted prepare service to be configured and
does not write a registry case.

## Important limitation

`VALID` means the explicit payload can be decoded through the local canonical
input constructors. It does not mean:

- the token/pool is eligible;
- Solana RPC or CoinGecko is reachable;
- RTI-11 will compose;
- the selected historical observation exists in future provider output;
- PFX/PFS/CIP will admit the case.

Those checks remain owned by the real trusted prepare flow.

## Boundary

Authentication remains mandatory. There is no provider/source call, case
mutation, retry, polling, wallet/signing, DEX routing, settlement, live trading
or economic authority.

G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED. G3/G4/P09 remain NOT
AUTHORIZED.
