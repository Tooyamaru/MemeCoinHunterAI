# HR-FND-02 — Standalone Hunter Room Packaging

Status: IMPLEMENTATION / CONTROLLED PAPER ONLY

## Purpose

Package the already verified HR-FND-01 Hunter Room as a standalone static web
application without duplicating the UI or adding a second dependency graph.

The existing `@workspace/mockup-sandbox` package remains the design-preview
host, but it now has a separate standalone build mode that renders Hunter Room
directly and emits an isolated `dist-hunter-room/` bundle.

## Commands

From the repository root:

```bash
BASE_PATH=/hunter-room PORT=8082 pnpm --filter @workspace/mockup-sandbox run dev:hunter-room
BASE_PATH=/hunter-room PORT=8082 NODE_ENV=production pnpm --filter @workspace/mockup-sandbox run build:hunter-room
BASE_PATH=/hunter-room PORT=8082 pnpm --filter @workspace/mockup-sandbox run preview:hunter-room
```

The normal workspace `build` command builds both the mockup preview and the
standalone Hunter Room bundle, so GitHub CI verifies both packaging modes.

## Runtime topology

The preferred browser/API topology is same-origin. The managed artifact can route
the standalone Hunter Room at `/hunter-room` and the Python Operator Facade
under `/api/v1` (plus `/health` and `/ready`):

```text
browser
  -> /hunter-room/*                  static Hunter Room bundle
  -> /api/v1/operator/paper-cases   FastAPI Operator Facade
  -> /api/v1/paper-lifecycle-results
```

In another hosting environment, an equivalent reverse proxy may serve the static
bundle and FastAPI under one HTTPS origin. Hunter Room defaults to a blank API
base, which means relative same-origin requests. A separate API base remains
available for controlled testing, but any cross-origin production deployment
requires an explicitly reviewed origin/CORS policy.

### Process-local operator case boundary

The OAF prepared-case registry intentionally preserves exact in-memory Python
object identity between prepare, review, run and persist. It is finite,
process-local and not restart-safe or cross-process.

For `staging` and `production`, operator case mutation is therefore disabled
unless `OPERATOR_PROCESS_LOCAL_REGISTRY_ACK=true`. This setting is an explicit
deployment acknowledgement, not a distributed-safety mechanism. It may only be
enabled when the deployment guarantees one stable application process for the
entire active case lifetime.

Autoscaling, multi-worker, process-restart or request-routing topologies that
can move one case between processes remain unsupported for OAF mutation until a
separately governed durable/reconstructable case-state contract exists. Durable
RTI-03 lifecycle readback is unaffected because it is database-backed.

## Secret handling

The operator bearer token remains session-memory input in the current
single-controller UI. It is not written to source control, URLs, localStorage,
or the case handle. Deployment secrets such as `OPERATOR_BEARER_TOKEN`,
`SOLANA_RPC_URL`, and `COINGECKO_DEMO_API_KEY` remain server-side runtime
configuration.

## Boundary

This packaging gate does not add autonomous discovery, polling, background
refresh, retry, wallet/signing, transaction submission, DEX routing, economic
settlement, or live trading. The UI remains an explicit controlled-paper
operator surface. G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED; G3/G4/P09
remain NOT AUTHORIZED.

## Next verification

After this bundle is CI-green, a deployment environment may perform one
explicit paper-only smoke verification using real server-side provider
configuration:

`Prepare -> Review -> Run once -> Persist once -> Readback`.

That operational check must not add hidden retries or new domain authority.
