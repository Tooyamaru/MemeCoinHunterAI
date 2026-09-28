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

The preferred deployment is same-origin:

```text
browser
  -> /hunter-room/*                  static Hunter Room bundle
  -> /api/v1/operator/paper-cases   FastAPI Operator Facade
  -> /api/v1/paper-lifecycle-results
```

A reverse proxy may serve the static bundle and FastAPI under one HTTPS origin.
Hunter Room defaults to a blank API base, which means relative same-origin
requests. A separate API base remains available for controlled testing, but any
cross-origin production deployment requires an explicitly reviewed origin/CORS
policy.

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
