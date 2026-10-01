# Install Gap Document — Debian Installability of Labish

**Desired outcome:** A user on a fresh Debian host installs Labish with a **single command** that pulls this repository from GitHub/Gitea (e.g. `curl -fsSL https://<host>/<owner>/labish/raw/main/install.sh | bash` or `bash <(wget -qO- ...)`) and ends up with a working stack — PostgreSQL, Redis, Qdrant, FastAPI, Dramatiq worker, Next.js, and nginx — ready to use.

**Current state (per `runtime_logs.md`):** A manual install attempt stalled roughly halfway. The bootstrapper (`apps/api/app/setup.py`) got through system packages, the venv, backend pip install, and `npm install`, then **aborted at `npm run generate-client`** and never reached the database, SAP-ingestion, or systemd steps. No service was ever started; the application was never reachable.

---

## 1. Observed failure (the proximate blocker)

- `npm run generate-client` (`@hey-api/openapi-ts`) fetches the OpenAPI spec from `http://127.0.0.1:8000/openapi.json` (`apps/web/openapi-ts.config.ts`). On a fresh install **the backend is not running yet**, so the fetch fails ("Request failed with status 500: fetch failed") — a chicken-and-egg dependency baked into the install order.
- `setup.py` offers an `OPENAPI_INPUT` override but there is **no checked-in OpenAPI spec file** in the repo to point it at, and the installer neither starts a temporary backend nor exports the schema offline.
- Because `run()` raises `BootstrapError` and `main()` aborts on the first error, this single failure **killed the whole bootstrap** — steps 4–6 (alembic migrations, SAP ingestion, systemd linking, `/etc/labish/*.env` scaffolding) were never executed.
- Minor UX issue: openapi-ts's interactive "Open a GitHub issue?" crash prompt blocked an otherwise scriptable flow.

## 2. Database provisioning gap

- Nothing in `setup.py`, the README, or deployment docs **creates the PostgreSQL role or the `labish` database**. The default DSN (`postgresql+asyncpg://127.0.0.1:5432/labish`, `apps/api/app/core/config.py`) carries no credentials, and Debian's PostgreSQL defaults to peer auth — `alembic upgrade head` would have failed even if the bootstrap had reached it.
- The Payload CMS side of `apps/web` needs its **own** `DATABASE_URI` and `PAYLOAD_SECRET` (`src/payload.config.ts`, defaulting to empty strings) — these are documented nowhere in the install flow.

## 3. Frontend production gap

- `setup.py` runs `npm install` + `generate-client` but **never runs `npm run build`**, while `deployment/systemd/nextjs.service` runs `npm run start`, which fails without a prior production build.
- `next build` fetches Google Fonts at build time, so it **fails on offline/restricted hosts** — no vendored fonts or fallback.
- Node toolchain is unpinned: apt pulled Debian's nodejs/npm 9.2 plus hundreds of `node-*` debs, while the operator's shell actually resolved **nvm Node v26**. `package.json` has no `engines` field; `setup.py` uses whatever `npm` is first on `PATH`. Result: two divergent Node stacks and no guarantee the systemd unit (`/usr/bin/npm`) uses the same one.

## 4. Qdrant gap

- `deployment/systemd/qdrant.service` expects `/usr/local/bin/qdrant`, but **no automated install exists**: `setup.py` doesn't check for Qdrant, the README says to download the release binary manually, and the `AGENTS.md` snippet is broken (`curl -L https://github.com | tar -xz`). The runtime log shows Qdrant was **never installed**.
- The backend as installed (see pip list in the log) contains **no `qdrant-client` or `langgraph`**, contradicting the dependency list in `AGENTS.md` §3 — docs and `apps/api/pyproject.toml` have drifted.

## 5. Deployment artifacts don't match the real host

- Systemd units hardcode `User=nathan`, `Group=nathan`, and `WorkingDirectory=/home/nathan/my-application/...`; the actual host user was `nathanlabish` and the repo lived at `~/Documents/labish-main`. `setup.py` symlinks the units **verbatim with no templating/substitution**, so even a successful bootstrap would produce units that fail on start.
- `deployment/nginx.conf` hardcodes `server_name my-application.local`; no step installs/enables it (README gives manual commands only, and `setup.py` doesn't touch nginx despite probing for it).
- `/etc/labish/*.env` files are scaffolded as **empty comment-only placeholders** with no documented list of required keys (`LABISH_DATABASE_URL`, `LABISH_JWT_*` key paths, `LABISH_REDIS_URL`, `NEXT_PUBLIC_SITE_URL`, `PORT`, `PAYLOAD_SECRET`, `DATABASE_URI`). No step generates **persistent RS256 JWT keys** — production would silently run on an ephemeral dev keypair regenerated at each restart, invalidating sessions.

## 6. Process/usability gaps evident in the log

- The operator had to guess invocation (`python3 app/setup.py` from the wrong directory failed; path confusion cost several attempts). There is no top-level `install.sh` / `make install` entry point, and the README's "Host provisioning" section diverges from `setup.py` (e.g. `pip install -e .` vs `.[dev]`; README omits the bootstrapper entirely).
- The venv requirement is enforced by a hard abort rather than the script creating/activating the venv itself.
- `apt` emitted `pg_lsclusters: not found` during PostgreSQL configuration — transient Debian packaging ordering, likely benign, but the installer should verify the cluster actually initialized.
- `npm install` surfaced 18 vulnerabilities (5 high) and unapproved install scripts — not blocking, but part of a "ready to ship" delta.

## 7. Delta summary

| # | Desired | Current | Severity |
|---|---------|---------|----------|
| 1 | Client generation works on fresh install | Requires a live backend; no spec fallback; aborts whole bootstrap | **Blocker** (observed failure) |
| 2 | DB role/db created + migrated automatically | No role/db creation; credential-less DSN; migrations never ran | **Blocker** |
| 3 | Frontend built and startable via systemd | No `npm run build` step; Google Fonts breaks offline builds; Node unpinned | **Blocker** |
| 4 | Qdrant installed and running | No install automation; broken docs; service points at missing binary | High |
| 5 | Systemd/nginx configs valid for the target host | Hardcoded `nathan` / `/home/nathan/my-application` / `my-application.local` | High |
| 6 | Populated env files + persistent JWT keys | Empty placeholders, undocumented keys, ephemeral keys only | High |
| 7 | Single, resumable, documented install entry point | Multi-step, interactive, fail-fast script; README/AGENTS/pyproject drift | Medium |

**Bottom line:** the delta is not one bug but an install pipeline that assumes an already-running, already-configured system. The blockers (OpenAPI generation ordering, database provisioning, frontend production build) plus host-specific hardcoding in `deployment/` must be closed before a single-command install from a GitHub/Gitea repo is achievable.

---

## 8. Development checklist for a single-command install

Target invocation (one line, fresh Debian host):

```bash
curl -fsSL https://<git-host>/<owner>/labish/raw/main/install.sh | sudo bash
```

### A. Entry point & orchestration

- [ ] Add a top-level `install.sh` that: verifies Debian + root/sudo, installs `git` + `curl` if missing, clones (or updates) the repository from the GitHub/Gitea remote into a well-known location (e.g. `/opt/labish`), then hands off to the bootstrapper non-interactively.
- [ ] Make `apps/api/app/setup.py` fully non-interactive under a single flag (`--yes` already exists; ensure *every* step honours it, including the openapi-ts crash prompt via `CI=1`/`--no-interactive` equivalents).
- [ ] Make the bootstrapper **resumable and non-fail-fast**: collect step failures, continue independent steps, and print a final actionable summary instead of aborting on the first `BootstrapError`.
- [ ] Have the bootstrapper create and use the `apps/api/venv` itself when absent, instead of aborting with "no virtual environment is active".
- [ ] Add an idempotency guarantee: re-running the one-liner on a provisioned host must be a safe no-op/upgrade.
- [ ] Per the AGENTS.md installer-sync rule, keep `install.sh` a thin wrapper — all provisioning logic stays in `apps/api/app/setup.py`.

### B. Break the OpenAPI chicken-and-egg (Blocker 1)

- [ ] Add an offline schema export step: generate `openapi.json` from the FastAPI app in-process (no server needed) and feed it to `generate-client` via `OPENAPI_INPUT` — or commit a generated `openapi.json` artifact kept in sync by CI.
- [ ] Update `setup.py` `check_frontend()` to use the offline spec by default during provisioning and fall back to the live URL only in dev workflows.

### C. Database provisioning (Blocker 2)

- [ ] Add a `setup.py` step that creates the PostgreSQL role and `labish` database (via `sudo -u postgres psql`), generates a strong password, and writes the resulting `LABISH_DATABASE_URL` into `/etc/labish/api.env`.
- [ ] Verify the PostgreSQL cluster is initialized and running (`pg_lsclusters` / `systemctl status postgresql`) before running migrations.
- [ ] Run `alembic upgrade head` non-interactively using the provisioned DSN.
- [ ] Provision the Payload CMS database/role and write `DATABASE_URI` + a generated `PAYLOAD_SECRET` into `/etc/labish/web.env`.

### D. Frontend production readiness (Blocker 3)

- [ ] Add `npm run build` to the bootstrapper after client generation, with `NEXT_PUBLIC_SITE_URL` sourced from install configuration.
- [ ] Vendor fonts locally (self-host via `next/font/local`) so `next build` succeeds without internet access to Google Fonts.
- [ ] Pin the Node.js toolchain: add an `engines` field to `apps/web/package.json`, install a pinned Node version (NodeSource or `nvm` in a deterministic path) from the installer, and point the `nextjs.service` unit at that exact binary.

### E. Qdrant automation

- [ ] Add a Qdrant install step to `setup.py`: download a pinned release binary (with checksum verification) to `/usr/local/bin/qdrant`, or document/automate the apt/docker alternative.
- [ ] Fix the broken Qdrant install snippet in `AGENTS.md` and align the backend dependency list (`qdrant-client`, `langgraph`) between `AGENTS.md` and `apps/api/pyproject.toml` — either add the packages or correct the docs.

### F. Templated deployment artifacts

- [ ] Convert `deployment/systemd/*.service` and `deployment/nginx.conf` into templates; have `setup.py` render them with the actual install user, repository path, venv path, node path, and server name, then install the rendered copies (not verbatim symlinks).
- [ ] Add an nginx provisioning step: install the rendered site config into `sites-available`, symlink into `sites-enabled`, run `nginx -t`, and reload.
- [ ] Enable and start all services (`qdrant`, `fastapi`, `worker`, `nextjs`, `nginx`) at the end of the bootstrap, then run a health check against `/health` and the site root.

### G. Secrets & environment files

- [ ] Generate a persistent RS256 keypair at install time (e.g. `/etc/labish/keys/`, mode 0600), and write `LABISH_JWT_PRIVATE_KEY_PATH`/`LABISH_JWT_PUBLIC_KEY_PATH` into `api.env` so sessions survive restarts.
- [ ] Populate `/etc/labish/{api,web,qdrant}.env` with every required key (documented defaults + generated secrets) instead of empty comment-only placeholders; document the full key list in the README.

### H. Documentation & verification

- [ ] Rewrite the README install section around the one-liner, replacing the divergent manual steps; keep a documented "manual path" that matches what `setup.py` actually does.
- [ ] Add a CI job that exercises the full install on a clean Debian container/VM (headless, `--yes`) and asserts all services come up healthy — preventing regressions in installability.
- [ ] Triage the 18 `npm audit` findings and the unapproved install scripts so a fresh install is not born with known high-severity vulnerabilities.
