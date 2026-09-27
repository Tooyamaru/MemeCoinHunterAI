# Post-OAF Controlled-Paper End-to-End Verification Gate

Status: SPECIFICATION / VERIFICATION GATE
Date: 2026-09-27
Base checkpoint: `bd9ce83ee0f2ecfb43e1bf4a865101580fd53864`

## Purpose

Define the bounded verification that follows the merged Operator Facade, persistence handoff, Hunter Room foundation, governance reconciliation, and post-OAF readiness audit.

This gate verifies the already-merged controlled-paper operator chain as one bounded system. It does not authorize a new trading authority or autonomous runtime.

## Canonical chain under verification

1. Explicit authenticated prepare.
2. Review of the prepared case with no hidden provider refresh.
3. Explicit run-once.
4. Explicit persist-once of the exact lifecycle result through the existing RTI-03 owner.
5. Readback through the existing persisted lifecycle read owner/API.
6. Hunter Room presentation of the exact controlled-paper state/result.

The verification must preserve the existing owner boundaries and must not recompute or semantically rewrite canonical upstream results.

## Required verification properties

- one explicit operator action per state transition;
- no automatic retry or polling;
- run-once remains one-shot for a prepared case;
- persist-once cannot silently execute the lifecycle again;
- persisted digest identity matches the exact lifecycle result selected for persistence;
- readback returns the canonical persisted result through existing read owners;
- Hunter Room reflects transport outcomes without inventing economic interpretation;
- authentication remains fail-closed;
- safe errors do not expose internal exception details;
- deterministic/canonical identities and provenance remain continuous across the chain;
- existing process-local registry limitations remain explicit and are not represented as restart-safe exactly-once semantics.

## Negative-path verification

The verification must cover at minimum:

- unauthenticated prepare/review/run/persist;
- unknown or invalid opaque handle;
- review before a valid prepared case exists;
- second run attempt for a one-shot case;
- persist before a successful lifecycle result exists;
- second persist attempt;
- unavailable persistence/readback owner;
- malformed or mismatched lifecycle identity/digest;
- Hunter Room rendering of bounded failure states without triggering hidden actions.

## STOP boundary

This gate stops after controlled-paper readback and Hunter Room presentation.

It does **not** authorize or open:

- scheduler, worker loop, background refresh, polling, or automatic retry;
- autonomous token discovery/hunting;
- wallet, signing, RPC transaction submission, DEX execution, broadcast, or settlement;
- economic realization or live P&L authority;
- G2, G3, G4, or P09;
- live trading.

## Repository reconciliation finding

The post-OAF readiness audit is merged and `main` CI is green at the base checkpoint. `PROJECT_STATE.md` still contains stale wording that describes the run API / persistence / Hunter Room completion chain as `IN REVIEW` and defers production Hunter Room packaging until that chain is merged and verified. Those statements no longer describe the repository state after PRs #86-#90.

A documentation reconciliation must therefore record the merged/CI-passing state before any later production/deployment authority is inferred. This stale wording is a governance/documentation defect, not evidence that the merged implementation is absent.

## Acceptance criteria

This gate may be considered verified only when:

1. repository `main` remains the source of truth;
2. focused end-to-end tests or an equivalent bounded verification exercise prove the canonical chain above;
3. relevant regression and workspace CI pass;
4. no forbidden boundary becomes reachable;
5. governance documentation is reconciled to the actual merged state;
6. any next gate is selected separately from the evidence produced here.

## Controller boundary

Creating this gate does not itself authorize new production code, provider polling, deployment, autonomous hunting, or live/economic execution. Any implementation needed solely to add bounded verification coverage must receive its own explicit controller authorization if it changes test or runtime behavior.
