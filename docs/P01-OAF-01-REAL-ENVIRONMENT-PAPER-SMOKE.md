# P01-OAF-01 — Real-Environment Controlled-Paper Smoke Harness

Status: IMPLEMENTATION / EXPLICIT OPERATOR ACTION ONLY

## Purpose

Provide one bounded CLI for exercising the deployed Operator Facade without
adding polling, retries, autonomous discovery, or a second domain owner.

The CLI consumes a complete explicit prepare JSON file. It never invents
paper-policy defaults. By default it performs only:

`readiness -> prepare -> review`

The operator must add `--confirm-run` to invoke one paper run, and must add
both `--confirm-run --confirm-persist` to permit one persistence action and
one readback.

## Example

```bash
export OPERATOR_BEARER_TOKEN='set-in-secret-storage'
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

For a full eligible chain the harness performs exactly:

1. one authenticated GET operator readiness preflight;
2. one POST prepare;
3. one GET review;
4. one POST run;
5. one GET post-run review;
6. one POST persist;
7. one GET durable readback.

The readiness endpoint performs no provider connectivity probe; it reports only
configured application/database/operator service readiness. If readiness is not
`READY`, the harness stops before prepare.

There is no retry, polling, fallback provider, second run, or second persist.

A canonical preparation STOP returns immediately. A non-persistable run returns
without calling persistence. Transport/HTTP/schema failures stop immediately.

## Boundary

This is controlled paper simulation only. It does not authorize wallet/signing,
transaction submission, DEX routing, settlement, economic realization, or live
trading. It does not change G2/G3/G4/P09 authority.
