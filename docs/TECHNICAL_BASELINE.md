# Technical Baseline

## Selected stack

- **Runtime:** Python 3.13
- **API:** FastAPI served by Uvicorn
- **Configuration and validation:** Pydantic Settings
- **Logging:** Standard-library Python logging with timestamp, level, logger name, and message
- **Testing:** pytest and FastAPI-compatible `TestClient`
- **Dependency management:** One root `pyproject.toml` with `uv.lock`; development-only test tools are kept in the dev dependency group

## Application structure

- `backend/api/` — HTTP application and routes
- `backend/core/` — configuration, logging, and infrastructure boundaries shared by the API and future workers
- `core/` — future domain logic such as data, signals, opportunity, decision, risk, execution, and learning; currently empty
- `apps/dashboard/` — future dashboard surface; the visual dashboard is deferred to a later P01 task
- `workers/` — future process entrypoints; no workers are implemented yet
- `database/` — future migrations and database assets
- `tests/` — targeted foundation and future domain tests
- `scripts/` — setup and maintenance scripts

This ownership model avoids duplicate `core` responsibilities: `backend/core` owns runtime infrastructure, while root `core` will own domain behavior.

## Runtime foundation

The current entrypoint is `backend.api.main:app`. It exposes only:

```text
GET /health
```

Run it with:

```bash
uv run uvicorn backend.api.main:app --host "${APP_HOST:-0.0.0.0}" --port "${PORT:-${APP_PORT:-8000}}"
```

The health endpoint reports process status only. It does not fake checks for databases, blockchains, wallets, or other services that are not implemented.

## Database strategy

The application uses an explicit database configuration boundary and does not open a connection or create trading tables in P01-T01. PostgreSQL is the planned shared development and production database. A later task will select the PostgreSQL driver/ORM, migration workflow, connection/session lifecycle, and isolated test database strategy. SQLite is not the permanent architecture.

## Configuration and secrets

Configuration is environment-based with safe development defaults. `.env` is ignored by Git; `.env.example` contains names and non-secret defaults only. Current names are `APP_ENV`, `APP_HOST`, `APP_PORT`, `APP_VERSION`, `DATABASE_URL`, and `LOG_LEVEL`. No wallet, Solana, DEX, or trading secret names are needed yet.

## Workers and lifecycle

Early development keeps one repository and a simple API process. Future independent processes can be added without moving domain ownership: scanner, market-data, signal, decision, risk, paper/execution, and learning workers. Each future process will have its own entrypoint and reuse the infrastructure boundaries rather than becoming a microservice prematurely.

## Replit and future Railway compatibility

After cloning into a blank Replit workspace, run `bash scripts/replit_setup.sh`, configure environment values through secrets when needed, and start the API with the command above. Replit supplies the runtime port through `PORT` when a workflow is added. The stateless FastAPI/Uvicorn process and environment-based configuration can later move to Railway without requiring a framework rewrite.

## Rejected or deferred alternatives

- **Large frontend framework:** deferred because P01-T01 only needs a runtime baseline; the dashboard gets its own focused task.
- **SQLite as the application database:** rejected as the permanent direction because PostgreSQL is required later; no temporary database is needed yet.
- **Microservices and external observability:** deferred until real workload and operational needs justify them.
