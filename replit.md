# Meme Coin Hunter AI — Memecoin Inspection

Read-only workspace for inspecting all source-returned DexScreener pairs for a token without ranking, approval, or trading behavior.

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server (managed workflow port 8080)
- `pnpm --filter @workspace/memecoin-inspection run dev` — run the frontend (managed workflow port 19234)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- The managed artifact workflows provide `PORT` and `BASE_PATH`; one-off frontend builds need both values, for example `PORT=19234 BASE_PATH=/ pnpm --filter @workspace/memecoin-inspection run build`.
- `pnpm --filter @workspace/api-server run test` — run mocked HTTP bridge/endpoint checks
- `pnpm --filter @workspace/memecoin-inspection run test` — run Chromium-backed mocked frontend interaction checks against `APP_URL` (defaults to the proxied preview)
- `uv run pytest -q tests/test_dexscreener_inspection.py` — run the focused Python inspector checks

## Operator Facade and Hunter Room

The Python FastAPI Operator Facade is a separate controlled-paper surface from
the TypeScript Memecoin Inspection bridge. Run it with
`uv run uvicorn backend.api.main:app --host 0.0.0.0 --port <port>` and provide
operator/Solana/CoinGecko values through Replit Secrets or equivalent runtime
secret storage.

The current HR-FND-01 functional preview lives at
`artifacts/mockup-sandbox/src/components/mockups/HunterRoom.tsx` and is
rendered by the mockup sandbox at `/preview/HunterRoom`. Its bearer token is
held only in component memory. For an action-capable deployment, serve the
Hunter Room through a trusted same-origin/reverse-proxy arrangement or another
explicitly reviewed transport boundary; do not weaken operator authentication
or enable permissive credentialed CORS merely to make the preview connect.

The Operator Facade is paper/simulation-only. It has explicit prepare, review,
run-once, persist-once and lifecycle readback actions; it does not poll,
auto-retry, sign, broadcast, route live trades or open G2/G3/G4/P09.

## Stack

- pnpm workspaces, Node.js 20, Python 3.13, TypeScript 5.9
- API: Express 5
- Frontend: React, Vite, Tailwind CSS
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `artifacts/memecoin-inspection` — responsive inspection UI
- `artifacts/api-server/src/routes/inspection.ts` — validated Express bridge to the fixed Python inspector module
- `core/data/dexscreener_inspection.py` and `core/data/dexscreener_transport.py` — source-shaped inspection and bounded transport contracts
- `lib/api-spec/openapi.yaml` — API source of truth; generated clients and validators live in `lib/api-client-react` and `lib/api-zod`

## Architecture decisions

- The UI requires an explicit submit and renders every returned pair in source order; it does not rank or select a pair.
- The bridge validates request input before spawning `python3 -m core.data.dexscreener_inspection`, bounds execution, and validates the returned report against generated Zod schemas.
- Receipt timestamps are labeled “Data received at”; P08 acceptance remains `NOT_ATTEMPTED` with a null observation time.

## Product

Users enter a chain and token address, submit one inspection, and review source metrics, unavailable values, findings, response metadata, and collapsible provenance details.

## User preferences

No additional preferences recorded.

## Gotchas

- Do not add wallet, signing, trading, downstream admission, or automatic live-request behavior to this inspection app.
- Build generated workspace declarations before package-level typechecks with `pnpm run typecheck:libs`.
- The API bridge resolves `python3` from the Python 3.13 Replit module; verify with `python3 --version` in the API workflow environment.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
