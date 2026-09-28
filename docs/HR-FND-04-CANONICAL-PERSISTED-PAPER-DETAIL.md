# HR-FND-04 — Canonical Persisted Paper Detail

Status: IMPLEMENTATION / READ-ONLY CONTROLLED PAPER

## Purpose

Project selected persisted lifecycle artifacts into a more operator-readable
Hunter Room detail without creating a new analytics owner or inferring P&L.

## Canonical sources

The UI reads only fields already present in the RTI-06 detail response:

- `FILL_OUTCOME` for fill status, side, quantities, effective price, fill time
  and canonical asset identity;
- `STATE_TRANSITION` for transition status/time, quantity effect and accounting
  effect fields;
- `RESULTING_PAPER_STATE` for resulting position/cost-basis and exposure state.

The projection is client-side presentation only. It does not rewrite stored
payloads, recompute owner results, or fetch any provider.

## P&L boundary

No realized or unrealized P&L is shown by this milestone. Although canonical
state contains quantities, cost basis, trade value, proceeds and valuation
fields, HR-FND-04 does not infer profitability from them. A future P&L surface
requires an explicit canonical ownership/projection decision rather than a
frontend calculation.

## Failure behavior

If a persisted artifact is absent or its canonical JSON cannot be decoded, the
corresponding UI fields remain unavailable. Hunter Room does not synthesize
default values or substitute another artifact.

## Authority

This remains read-only controlled-paper presentation. It does not invoke
prepare, run, persistence, discovery, providers, wallet/signing, DEX execution,
settlement, or live/economic trading.

G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED. G3/G4/P09 remain NOT
AUTHORIZED.
