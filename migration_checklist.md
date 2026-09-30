# Migration Checklist — Aligning Labish with the `AGENTS.md` Blueprint

This document is the result of a code audit comparing the current repository against the
AI-Native Enterprise Architecture Blueprint (2026 Final) defined in `AGENTS.md`.
No application code has been modified yet; this file is the plan of record for the migration.

---

## 1. Gap Analysis

### 1.1 Repository Layout

| Blueprint (`AGENTS.md`) | Current Repository | Gap |
|---|---|---|
| `apps/web/` — Next.js frontend workspace | `front end/` (directory name contains a space) | Wrong location and non-standard name; must move to `apps/web/` |
| `apps/api/` — Unified FastAPI engine & workers | `Services/` | Wrong location/name; must move to `apps/api/` |
| `deployment/` — nginx + systemd unit files | **Missing entirely** | No `nginx.conf`, no `systemd/` units (`fastapi.service`, `worker.service`, `qdrant.service`, `nextjs.service`) |

### 1.2 Backend (`Services/` vs. `apps/api/`)

The backend is a single-file FastAPI app (`Services/app/main.py`) exposing only `GET /health`.
Nearly the entire blueprint package structure is missing:

| Blueprint module | Status | Notes |
|---|---|---|
| `app/core/` (config, security keys, RS256 JWT via PyJWT + passlib) | **Missing** | No auth/security layer exists at all |
| `app/db/` (engine pools, unified DB config) | **Missing** | No database connectivity (no PostgreSQL / asyncpg) |
| `app/models/` (SQLModel single-source schemas) | **Missing** | No SQLModel; no models of any kind |
| `app/routes/` (REST controllers) | **Missing** | `/health` endpoint lives directly in `main.py` instead of a router module |
| `app/events/` (past-tense event payloads) | **Missing** | No event schemas |
| `app/tasks/` (Dramatiq actors with `_task` suffix) | **Missing** | No Dramatiq, no Redis broker |
| `app/shared/` (contracts, `prompts/`) | **Missing** | No versioned contracts or prompt files |
| `app/integrations/` (`sap/`, `email/`, `storage/`) | **Missing** | No integration subsystems |
| `app/ai/` (`agents/`, `workflows/`, `tools/`, `mcp/`) | **Missing** | No LangGraph, no AI layer, no Qdrant client |
| `alembic/` (migrations hub) | **Missing** | No Alembic configuration |
| `main.py` as thin Uvicorn router initializer | **Deviates** | Contains middleware + endpoint logic inline |

Dependency gaps in `Services/pyproject.toml` vs. blueprint `requirements.txt`:
missing `sqlmodel`, `asyncpg`, `alembic`, `dramatiq[redis]`, `redis`, `pyjwt[crypto]`,
`passlib[bcrypt]`, `langgraph`, `qdrant-client`. (Packaging via `pyproject.toml`/hatchling
vs. the blueprint's plain `requirements.txt` — decide which to keep during Phase 1.)

Existing conforming assets to preserve: request-metadata middleware (`X-Request-ID`,
`X-Response-Time-Ms`), `GET /health`, and the pytest suite in `Services/tests/`.

### 1.3 Frontend (`front end/` vs. `apps/web/`)

| Blueprint requirement | Current state | Gap |
|---|---|---|
| Located at `apps/web/` | Located at `front end/` | Must be relocated |
| `middleware.ts` for secure cookie routing | **Missing** | No middleware file; login form (`src/app/login`, `src/app/portal`) is a non-functional static form with no auth wiring |
| `@hey-api/openapi-ts` generated API client + `npm run generate-client` script | **Missing** | No API client generation; data is hard-coded in `src/data/*.ts` (news, people, companies, artworks, photographs) instead of coming from the FastAPI backend |
| App Router pages | ✅ Present (`src/app/`) | Conforms (pages live under `src/app/` rather than `app/`; acceptable App Router variant) |
| Strict `tsconfig.json` | ✅ Present | Conforms |

### 1.4 Cross-Cutting / Engineering-Rule Gaps

- **Anti-drift boundaries** cannot yet be enforced — the route, task, integration, and AI layers do not exist to be separated.
- **No event-driven flow**: nothing publishes state transitions through Redis.
- **No schema tracking**: no Alembic revisions possible without models/db layer.
- **No frontend/backend contract sync**: no OpenAPI client generation pipeline.
- **No host deployment specs**: nginx and systemd configurations absent.

---

## 2. Actionable Migration Checklist

Execute phases sequentially. Each phase should leave the repo in a working, testable state.

### Phase 0: Workspace Restructure (Monorepo Layout) ✅ Complete

- [x] Create the `apps/` directory at the repository root
- [x] Move `Services/` to `apps/api/` (preserve git history with `git mv`)
- [x] Move `front end/` to `apps/web/` (removes the problematic space in the path)
- [x] Update root `README.md` paths and commands to reference `apps/api` and `apps/web`
- [x] Verify backend tests (`pytest`) and frontend build (`npm run build`) still pass from the new locations

### Phase 1: Shared Contracts & Models ✅ Complete

- [x] Add backend dependencies: `sqlmodel`, `pyjwt[crypto]`, `passlib[bcrypt]` (kept `pyproject.toml` as the dependency source)
- [x] Create `apps/api/app/models/` package with singular-noun SQLModel classes, each `table=True` model carrying an indexed auto-generated UUID `id` primary key (start with `User`)
- [x] Create `apps/api/app/events/` package with past-tense event payload schemas (e.g., `UserCreatedEvent`) as plain SQLModel classes
- [x] Create `apps/api/app/shared/` package for versioned contract snapshots and `shared/prompts/` for externalized prompt files (no raw prompt strings in Python)
- [x] Add unit tests validating model defaults (UUID generation, field constraints)

### Phase 2: Database Layer ✅ Complete

- [x] Add `asyncpg` and `alembic` dependencies (plus `pydantic-settings`, and `aiosqlite`/`pytest-asyncio` for test isolation)
- [x] Create `apps/api/app/db/` with unified engine/session configuration reading settings from `app/core/config`
- [x] Create `apps/api/app/core/` with environment configuration module
- [x] Initialize Alembic in `apps/api/alembic/` wired to the SQLModel metadata
- [x] Generate the initial migration (`alembic revision --autogenerate`) for Phase 1 models
- [x] Add a test/CI-friendly database strategy (env-driven DSN with in-memory SQLite fallback in the `test` environment) so `pytest` passes without a live PostgreSQL

### Phase 3: FastAPI Refactor (Routes, Security, Middleware, Tasks)

- [ ] Slim down `app/main.py` to an entry point that only wires middleware and includes routers
- [ ] Move `GET /health` into `apps/api/app/routes/` (e.g., `routes/system.py`) — routes perform no SQL or external calls directly
- [ ] Keep the existing request-metadata middleware (`X-Request-ID`, `X-Response-Time-Ms`) and relocate it appropriately (e.g., `app/core/`)
- [ ] Implement `app/core/security.py`: RS256 JWT sign/verify with PyJWT (private-key signing, public-key verification) and bcrypt password hashing via passlib — no `fastapi-users`
- [ ] Add auth routes (login/token issuance) in `app/routes/` backed by the `User` model
- [ ] Add `dramatiq[redis]` and `redis` dependencies; create `apps/api/app/tasks/` with a Redis broker setup and context-named task files; all actors use `@dramatiq.actor` and the `_task` suffix
- [ ] Create `apps/api/app/integrations/` skeleton (`sap/`, `email/`, `storage/`) — pure, deterministic Python with typed inputs/outputs and `try/except` graceful-degradation wrappers around all network calls
- [ ] Create `apps/api/app/ai/` skeleton (`agents/`, `workflows/`, `tools/`, `mcp/`); tools wrap `app/integrations/` clients only; add `langgraph` and `qdrant-client` dependencies when the first agent lands
- [ ] Update/extend the pytest suite to cover routes, security, and middleware after the refactor

### Phase 4: Frontend Updates

- [ ] Add `@hey-api/openapi-ts` as a dev dependency in `apps/web/`
- [ ] Add a `generate-client` npm script that generates the TypeScript client from the FastAPI OpenAPI schema; never hand-code overlapping interface definitions
- [ ] Create `apps/web/middleware.ts` (or `src/middleware.ts`) for secure-cookie route protection of authenticated areas (`/portal`)
- [ ] Wire the login form (`src/app/login`) to the backend auth endpoint, storing the session in a secure HTTP-only cookie
- [ ] Incrementally replace hard-coded `src/data/*.ts` datasets with data fetched from backend routes via the generated client (news, people, companies, artworks, photographs)
- [ ] Run `npm run lint` and `npm run build` to validate each change

### Phase 5: Deployment Configuration

- [ ] Create `deployment/nginx.conf` reverse-proxying `/` → Next.js (port 3000) and `/api/` → FastAPI (port 8000)
- [ ] Create `deployment/systemd/fastapi.service` (Uvicorn, ordered after postgresql/redis/qdrant)
- [ ] Create `deployment/systemd/worker.service` (Dramatiq worker cluster)
- [ ] Create `deployment/systemd/qdrant.service` (local Qdrant daemon)
- [ ] Create `deployment/systemd/nextjs.service` (Node production server)
- [ ] Document host provisioning steps (apt packages, venv setup, Qdrant install) in the root `README.md`

---

## 3. Sequencing Notes

- Phase 0 is a prerequisite for everything else (paths in all later phases assume `apps/`).
- Phases 1 → 2 → 3 are strictly sequential (models → db → routes/tasks depend on each other).
- Phase 4 depends on Phase 3 routes existing to generate a meaningful client.
- Phase 5 can be drafted in parallel but should be finalized last, once ports/paths are settled.
