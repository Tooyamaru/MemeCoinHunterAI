# A1 future provider-backed execution preparation gate

Status: OFFLINE PREPARATION IMPLEMENTED; provider execution NOT AUTHORIZED / NOT EXECUTED. G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED. G3/G4/P09 remain NOT AUTHORIZED. This document grants no execution authority.

## No-contact check-only command

`uv run --locked python -m scripts.a1_execution_preflight --check-only --manifest safe-manifest.json`

The exact manifest contains environment, expected_environment, workers=1, reload=false, and boolean declarations database_configured, operator_configured, solana_provider_configured, coingecko_provider_configured, process_local_acknowledged, simulation_only and offline_preparation_authorized. Environment must match; staging/production requires the process-local acknowledgement. All required configuration declarations must be true. Never put credentials or endpoint secrets in the manifest.

The parser caps input at 32 KiB and rejects unknown fields/duplicate keys/malformed values. It reads only that local safe manifest: no Settings/environment/secret access, database access, provider connection or runtime launch. Success is OFFLINE_CONFIGURATION_CHECKED, provider_contacted=false, provider_execution_authorized=false. Database connection, qualifying runtime, cluster/program verification, collection budget, reference lifecycle and persistence/readback remain PENDING. Declarative booleans are not operational attestations. There is no provider-call switch.

## Required future controller packet

Before any provider contact, all preparation items must be concrete and reviewable:

1. Select one qualifying stable single-process runtime, one worker, no reload/restart/autoscale; retain process-local case ownership.
2. Establish exact environment identity and operator authentication/readiness using existing controlled-paper gates.
3. Establish connected durable database where required and exact persistence/readback owner availability.
4. Separately authorize provider-backed paper preparation/execution; intentionally provision secrets in that runtime without exposing them in manifests or lineage.
5. Qualify the explicitly selected HTTP adapter in that runtime: exact timeout/byte cap, redirects disabled, zero retry, no endpoint fallback, no hidden transport calls. A1-HTTP-01 now supplies a concrete stdlib opener with offline conformance tests and fixed same-origin private RPC routing/Demo header authentication, but no automatic wiring or actual endpoint qualification. Select `SOLANA_RPC_URL` and `COINGECKO_DEMO_API_KEY` in protected runtime storage only. The public RPC origin must be credential-free; secrets in hostname/userinfo or unsupported header-auth profiles are not accepted. See `AUTONOMOUS-PAPER-A1-HTTP-ADAPTER-SPECIFICATION.md`.
6. Use the landed common P03/RTI-11 **precollection before T** and exact-owner pure replay with the same whole-cycle ledger. These stages are complete offline, not endpoint-qualified. Select safety response cap at most 256 KiB and exact timeout at most 30s. Reserve at most thirty safety calls/five diagnostics; no post-T networking. A1-AUD-01 now retains a durable collection audit packet linked to the existing lifecycle without changing closed RTI owners. Intentionally apply revision `0003_a1_collection_audit` to the qualified durable database under separate authority; explicitly attach/read the audit after canonical lifecycle persistence. Lifecycle-only readback does not prove source audit retention.
7. Demonstrate actual provider quota/credit/shared-use/latency fit for at most 46 RPC + 69 CoinGecko = 115 physical calls; aggregate deadline at most 180s, same-minute cutoff restriction and unchanged source freshness/skew. Published plan rate alone is insufficient.
8. Under that separate provider authorization, cluster verification must PASS before facts are admitted. Exact Raydium program LEVEL 1 must PASS; source/binary LEVEL 2 remains NOT VERIFIED and requires explicit acceptance of the narrow paper limitation.
9. Collection budget, no-retry and completed-receipt/reference lifecycle must PASS; freeze T only after collection, use pure replay thereafter.
10. Invoke exactly one `AutonomousPaperOneCycleService`; mandatory P03/P05/P06/Risk and simulation_only=true, at most one paper lifecycle. No scheduler or loop.
11. Retain exact persistence/readback digest and artifact evidence through the existing RTI owners and connected durable database.
12. Terminal STOP, including any preparation/budget/source/authority failure. No automatic retry or subsequent cycle.

The offline chain now includes common raw A1/P03/RTI-11 precollection, exact
original-owner replay and A1-AUD-01 source audit/lifecycle linkage. A1-HTTP-01
integration adds the concrete opener through fake HTTP connections, successful
canonical paper persistence/audit readback and independent Risk veto. Temporary
SQLite and synthetic raw source facts prove offline contracts only. They do not
satisfy real environment/database, actual provider/account, quota/latency or
operational adapter qualification.

After A1-HTTP-01 landing/CI, the remaining listed evidence is operational:
select the runtime/database/account/profile and obtain separate authorization
for qualification and one finite provider-backed paper attempt. Do not treat the
older selected-mint OAF smoke as proof of the common A1 collection/audit chain;
its own no-provider preflight remains reusable preparation. No provider-backed
autonomous cycle or controlled-paper smoke has run. No wallet/signing/broadcast/
DEX/settlement authority is included.
