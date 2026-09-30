# P01-OAF-01 — Provider-Backed Controlled-Paper Smoke Execution Packet

Status: OPERATIONAL PREPARATION COMPLETE / EXECUTION NOT AUTHORIZED BY THIS DOCUMENT

## Purpose

Prepare the exact bounded operational checklist for the next repository gate:
one explicit provider-backed controlled-paper smoke in a known single-process
environment.

This document does not itself authorize or execute provider access. It does not
open wallet, signing, DEX routing, settlement, economic realization, autonomous
hunting, or live trading.

## Required runtime configuration

The application reads these environment-backed settings under the current
implementation:

- `APP_ENV`: use the intended controlled environment. Staging/production
  requires explicit acknowledgement of the process-local registry constraint.
- `DATABASE_URL`: must point to the database used for RTI-03 persistence and
  readback.
- `OPERATOR_BEARER_TOKEN`: controller credential for the authenticated
  Operator Facade. Never place the value in source control or CLI URLs.
- `OPERATOR_PROCESS_LOCAL_REGISTRY_ACK=true`: required in staging/production
  for the current process-local case registry. This is only an acknowledgement;
  it does not provide sticky routing, restart durability, distributed locking,
  or cross-process exactly-once semantics.
- `SOLANA_RPC_URL`: trusted server-side Solana JSON-RPC endpoint used by the
  bounded prepare path.
- `SOLANA_RPC_TIMEOUT_SECONDS`: optional bounded RPC timeout; current default
  is 5 seconds and configured values are limited to 30 seconds.
- `SOLANA_RPC_MAX_RESPONSE_BYTES`: optional bounded RPC response limit;
  current default is 262144 bytes and configured values are limited to 1048576.
- `COINGECKO_DEMO_API_KEY`: server-side credential for the existing bounded
  exact-pool OHLCV diagnostic.

The smoke CLI itself reads the operator bearer from `OPERATOR_BEARER_TOKEN` by
default and accepts a different environment-variable name only through
`--token-env`.

## Deployment topology checkpoint

At the current repository checkpoint, root `.replit` declares:

```toml
[deployment]
deploymentTarget = "autoscale"
```

That target is **not** accepted as the qualifying smoke environment for the
current OAF case model. The active case registry and exact-object lifecycle are
process-local and require one stable application process from prepare through
persist. `OPERATOR_PROCESS_LOCAL_REGISTRY_ACK=true` acknowledges that
constraint but does not turn autoscale into sticky single-process routing.

Do not run the provider-backed smoke against the current autoscale topology.
Select/provision a known single-process environment first. This packet does not
silently change the deployment type or cost model.

A portable repository-owned option is now available for a local or VM host:

```bash
uv run python scripts/operator_single_process_runtime.py \
  --expected-environment staging \
  --check-only
uv run python scripts/operator_single_process_runtime.py \
  --expected-environment staging \
  --host 127.0.0.1 \
  --port 8000
```

The check-only command first requires `APP_ENV` to exactly match the explicit
`--expected-environment`, then validates the required
database/operator/Solana/CoinGecko configuration without provider connectivity.
The launch command enforces the same environment identity before starting the
existing FastAPI app with exactly one Uvicorn worker and reload disabled. It
does not run the smoke itself and does not authorize provider access.

For that local path, use `http://127.0.0.1:8000` as the smoke base URL. The
smoke harness permits plain HTTP only for localhost/loopback targets.

## Deployment preconditions

Before any provider-backed prepare is authorized:

1. Run exactly one stable application process for the full
   prepare -> review -> run -> persist lifetime of the case.
2. Disable autoscale/multi-worker behavior for that active-case path unless a
   separately authorized architecture replaces the process-local registry.
3. Confirm the database is connected and durable RTI-03 readback is available.
   Authenticated operator readiness must report the database check as
   `connected`; an unconfigured database is a STOP for this gate.
4. Confirm the deployed base URL uses HTTPS for any non-local target.
5. Keep all bearer/provider credentials in runtime secret storage only.
6. Prepare one explicit JSON payload outside source control. The payload must
   name the controller-selected candidate, exact pool, PFX/CIP invocation
   identities, explicit timestamps, simulation assumptions, and bounded
   request/policy parameters required by the existing prepare contract.
7. Do not enable retries, polling, fallback providers, background workers, or
   autonomous discovery.

## Stage A — no-provider preflight

Before operational authorization for provider access, run:

```bash
uv run python scripts/operator_paper_smoke.py \
  --base-url https://your-controlled-paper-host.example \
  --prepare-payload /secure/path/prepare.json \
  --expected-environment staging \
  --preflight-only
```

Required result:

- authenticated readiness returns `READY`;
- readiness environment exactly matches the explicit `--expected-environment`;
- readiness uses `p01-oaf-01-operator-readiness-v1`;
- readiness reports database `connected`, case registry `enabled`, and
  prepare/run/persist services `configured`;
- `process_local_registry=true`;
- readiness reports no provider-connectivity probe and remains simulation-only;
- validation returns `VALID` under
  `p01-oaf-01-prepare-validation-v1`;
- validation performs no case mutation and no provider-connectivity check;
- candidate, token, chain, exact pool, PFX invocation, and CIP invocation
  identities exactly match the submitted payload.

Any mismatch is a STOP. Preflight-only must make no Solana or CoinGecko request.

## Stage B — separately authorized provider-backed smoke

Only after an explicit operational authorization and intentionally available
runtime secrets may the full smoke be run:

```bash
uv run python scripts/operator_paper_smoke.py \
  --base-url https://your-controlled-paper-host.example \
  --prepare-payload /secure/path/prepare.json \
  --expected-environment staging \
  --confirm-provider-prepare \
  --confirm-run \
  --confirm-persist
```

The expected environment must already have matched authenticated readiness, and
the `--confirm-provider-prepare` flag is mandatory before the first trusted
prepare/provider request. Run/persist confirmation cannot bypass this gate.

For an eligible full chain the harness performs exactly eight requests:

1. readiness;
2. no-I/O validation;
3. provider-backed prepare;
4. first review;
5. run once;
6. post-run review;
7. persist once;
8. durable RTI-03 readback.

There is no retry, polling, fallback provider, second run, or second persist.

## Accepted prepare outcomes

Two bounded prepare outcomes are valid:

- `PREPARATION_STOPPED`: accepted only under
  `p01-oaf-01-post-prepare-v1`, with `simulation_only=true` and at least one
  non-empty reason code. The smoke ends immediately.
- successful prepare: must use `p01-oaf-01-trusted-prepare-v1`, reach
  `REVIEW_READY`, remain simulation-only, preserve the validated
  candidate/token/chain/pool identities, return canonical case/CIP digests, and
  expose the exact review path for the opaque handle.

## Success evidence to retain

For a successful full eligible chain, retain the smoke JSON output and the
associated deployment/runtime evidence needed to show:

- readiness/validation contract versions and status;
- prepared handle and case digest;
- candidate/token/chain/pool identity continuity;
- CIP digest continuity into first review;
- run-once contract, terminal state/outcome, OCI/OSC/lifecycle digests, and
  simulation-only status;
- post-run review continuity for the same case and lifecycle digests;
- persist-once contract, `PERSIST_TERMINAL`, durable
  `STORED`/`ALREADY_STORED`, persistence digest, lifecycle digest, and
  artifact count;
- RTI-03 `FOUND` readback for the exact lifecycle digest, canonical result
  digest, matching run lifecycle root, and matching artifact count.

Do not retain bearer tokens, RPC URLs containing credentials, API keys, or
provider authorization headers in evidence artifacts.

## Mandatory STOP conditions

Stop the operational attempt immediately if any of the following occurs:

- readiness is not `READY`;
- validation is not `VALID`;
- process-local single-process assumptions are not satisfied;
- any required secret/configuration is missing;
- any contract version, identity, digest, state, simulation boundary, source
  label, or artifact-count check fails;
- Solana source facts are unavailable, malformed, stale, or temporally invalid;
- exact current-token membership or P03 eligibility cannot be established;
- CoinGecko authentication, source, temporal, identity, or history requirements
  fail;
- persistence does not return durable `STORED`/`ALREADY_STORED`;
- durable readback does not return the exact persisted lifecycle root.

No automatic retry is permitted by this gate.

## Closure criterion for the operational gate

The operational smoke gate may be marked verified only after one explicitly
authorized attempt either:

- returns a valid bounded `PREPARATION_STOPPED` with recorded reason codes; or
- completes the full eligible chain through exact durable RTI-03 readback.

A STOP is evidence that the fail-closed operational boundary worked. It is not
permission to loosen eligibility, freshness, identity, risk, or provider
requirements.

## Authority boundary

This packet prepares a controlled paper/simulation verification only.

P08 G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED. G3/G4/P09 remain NOT
AUTHORIZED. No wallet, signing, broadcast, DEX execution, settlement, economic
realization, autonomous hunting, scheduler, worker, or live trading authority
is granted.
