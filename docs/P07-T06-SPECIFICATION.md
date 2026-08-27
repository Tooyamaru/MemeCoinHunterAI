# P07-T06 — Paper Simulation Result / Performance Outcome Contract

**Status:** IMPLEMENTATION AUTHORIZED
**Contract:** `p07-t06-v1`

## Purpose
P07-T06 defines the immutable, deterministic paper-simulation outcome
boundary consumed by future P08 learning.

## Inputs
- accepted P07-T01 simulation input
- accepted P07-T02 fill outcome
- accepted P07-T03 position/exposure transition
- accepted P07-T04 ledger record
- accepted P07-T05 reconciliation result

## Rules
- deterministic and provider-neutral;
- immutable;
- preserve provenance and contract versions;
- preserve UNKNOWN, failure, partial-fill, and reconciliation-disagreement states;
- never create authorization or live execution authority;
- never modify T01–T05 records;
- no network, database, wallet, RPC, DEX, signing, broadcast, or live trading;
- no scoring, ranking, learning, or model promotion.

## Output
A canonical `PaperSimulationResult` containing:
- contract version;
- input/outcome/transition/ledger/reconciliation identities;
- overall simulation status;
- filled and unfilled quantities;
- resulting paper position identity;
- reconciliation status;
- provenance;
- deterministic digest.

P07-T06 is the final paper-outcome contract before P08.
