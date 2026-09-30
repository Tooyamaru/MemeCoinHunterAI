# P01-OAF-01 — Real-Environment Controlled-Paper Smoke Harness

Status: OFFLINE HARDENING COMPLETE / EXPLICIT OPERATOR ACTION ONLY

## Purpose

Provide one bounded CLI for exercising the deployed Operator Facade without
adding polling, retries, autonomous discovery, or a second domain owner.

The CLI consumes a complete explicit prepare JSON file. It never invents
paper-policy defaults. By default it performs only:

`readiness -> validate -> prepare -> review`

The validation call is the existing authenticated no-I/O canonical payload
preflight. It does not probe Solana/CoinGecko and does not mutate an operator
case.

Use `--preflight-only` to stop after authenticated readiness plus no-I/O
canonical payload validation. This mode performs no trusted prepare/provider
call and creates no operator case.

The operator must add `--confirm-run` to invoke one paper run, and must add
both `--confirm-run --confirm-persist` to permit one persistence action and
one readback. `--preflight-only` cannot be combined with either confirmation.

## Example

No-provider preflight only:

```bash
export OPERATOR_BEARER_TOKEN='set-in-secret-storage'
uv run python scripts/operator_paper_smoke.py \
  --base-url https://your-controlled-paper-host.example \
  --prepare-payload /secure/path/prepare.json \
  --preflight-only
```

Full explicit controlled-paper sequence:

```bash
uv run python scripts/operator_paper_smoke.py \
  --base-url https://your-controlled-paper-host.example \
  --prepare-payload /secure/path/prepare.json \
  --confirm-run \
  --confirm-persist
```

The token is read from the environment and is never accepted as a URL argument. Non-local smoke targets require HTTPS, and the harness refuses HTTP redirects so the bearer cannot be forwarded to a different endpoint.
Use `--token-env SOME_OTHER_SECRET_NAME` only when deployment policy requires
another environment variable name.

## Cardinality

Preflight-only mode performs exactly two authenticated requests:

1. one GET operator readiness preflight;
2. one POST no-I/O prepare-payload validation.

It then stops before the trusted prepare/provider path.

For a full eligible chain the harness performs exactly:

1. one authenticated GET operator readiness preflight;
2. one authenticated POST no-I/O prepare-payload validation;
3. one POST prepare;
4. one GET review;
5. one POST run;
6. one GET post-run review;
7. one POST persist;
8. one GET durable readback.

The readiness endpoint performs no provider connectivity probe; it reports only
configured application/database/operator service readiness. If readiness is not
`READY`, the harness stops before validation or prepare.

The validation endpoint performs no provider/source I/O and creates no case. If
the explicit payload is not `VALID`, the harness stops before prepare. The
harness also verifies the readiness/validation contract versions and safety
claims, requires process-local registry readiness for the current phase, and
checks that validation projects the exact explicit candidate, token, chain,
pool, PFX invocation, and CIP invocation identities from the submitted payload.
Any mismatch stops before trusted prepare/provider access.

There is no retry, polling, fallback provider, second run, or second persist.

A canonical preparation STOP returns immediately only when it uses the
post-prepare STOP contract, remains simulation-only, and carries at least one
explicit non-empty reason code. Any malformed or boundary-breaking STOP is
rejected. A successful prepare must use the trusted-prepare contract, remain
simulation-only, reach `REVIEW_READY`, project the exact
candidate/token/chain/pool identity validated before provider access, return a
canonical CIP digest, and expose the exact review path for the opaque handle. The first review must retain the registry contract, the same
handle/case digest, the same candidate/token/chain/pool identity, the same CIP
digest, the simulation-only boundary, and the expected historical-price-proxy
source label. Any mismatch stops before run.

Across later run, post-run review, and persist, the harness requires the same
opaque case handle and exact case digest. Run must use the run-once contract,
remain simulation-only, and reach the terminal controlled-paper outcome. The
post-run review must retain the case-registry contract, terminal run state,
simulation-only boundary, and controlled source label. For persist-eligible
runs, OCI/OSC/lifecycle digests from the run response must exactly match the
post-run review before persistence is attempted. A non-persistable terminal run
returns without calling persistence.

Persistence must use the persist-once contract, remain simulation-only, reach
`PERSIST_TERMINAL`, expose a canonical persistence digest and non-negative
artifact count, and report `STORED` or `ALREADY_STORED`. Durable readback is
then attempted only for the exact canonical lifecycle path. The readback must
use the RTI-03 contract, return `FOUND` for the same lifecycle digest, expose a
canonical result digest, project the same lifecycle root in its run snapshot,
and keep the run artifact count equal to both the returned artifact list and
the persistence artifact count. Any contract, identity, path, artifact-count,
or durable-storage mismatch stops immediately. Transport/HTTP/schema failures
also stop immediately.

## Operational execution packet

The exact runtime configuration, no-provider preflight, provider-backed
cardinality, mandatory STOP conditions, and evidence-retention checklist for the
next separately authorized operational gate are recorded in
`docs/P01-OAF-01-PROVIDER-BACKED-SMOKE-EXECUTION-PACKET.md`.

That packet is preparation only. It does not itself authorize a provider-backed
invocation.

## Offline Closure

The harness is considered offline-hardening complete for the current governed
single-process controlled-paper scope. The remaining verification is operational:
one separately authorized provider-backed smoke in a known single-process
environment with intentionally available runtime secrets. No provider-backed
smoke is performed by this document or by repository CI.

## Boundary

This is controlled paper simulation only. It does not authorize wallet/signing,
transaction submission, DEX routing, settlement, economic realization, or live
trading. It does not change G2/G3/G4/P09 authority.
