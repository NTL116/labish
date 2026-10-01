# Install Gap Document — Debian Installability of Labish

**Desired outcome:** A user on a fresh Debian host installs Labish with a **single command** that pulls this repository from GitHub/Gitea (e.g. `curl -fsSL https://<host>/<owner>/labish/raw/main/install.sh | bash` or `bash <(wget -qO- ...)`) and ends up with a working stack — PostgreSQL, Redis, Qdrant, FastAPI, Dramatiq worker, Next.js, and nginx — ready to use.

**Current state (per `install_logs`):** The one-liner now works nearly end-to-end. `install.sh` cloned the repo into `/opt/labish` and handed off to `apps/api/app/setup.py --yes`, which created the venv and re-executed itself inside it, installed Qdrant v1.13.4 (checksum-verified), installed backend dependencies, exported the OpenAPI schema offline and generated the frontend client from it, generated persistent RS256 JWT keys under `/etc/labish/keys`, provisioned the PostgreSQL role plus the `labish` and `labish_payload` databases, ran all three alembic migrations, built the Next.js production bundle, populated `/etc/labish/{api,web,qdrant}.env`, rendered and started the four systemd units, and passed the backend/frontend health checks. The run was resumable, non-interactive, and ended with a step-by-step summary.

**One step failed:** `systemctl enable --now nginx` exited 1 after `nginx -t` passed, so the public HTTP gateway never came up — the stack is reachable only on `127.0.0.1:8000` / `127.0.0.1:3000`. A handful of smaller defects also surfaced in the log (see below).

All seven items in the previous delta table (OpenAPI chicken-and-egg, DB provisioning, frontend build, Qdrant install, template rendering, env/JWT scaffolding, entry point/resumability) are now **closed**. What remains is the nginx failure plus polish items observed in this run.

---

## 1. Observed failure: nginx did not start (the remaining blocker)

- `setup.py` rendered and installed the site, disabled the stock default site, and `nginx -t` reported the configuration as valid — yet `systemctl enable --now nginx` failed with exit code 1 (`install_logs` lines 383–388). The installer printed only "see systemctl status / journalctl" and moved on; **no diagnostics were captured**, so the root cause (port 80 conflict, stale pidfile/socket, masked unit, partially-running nginx from the apt install, etc.) is unknown.
- `check_nginx` (`apps/api/app/setup.py` ~line 1065) runs `enable --now` followed by `reload`; if nginx is already running in a wedged state from package install, `start` can fail where `restart` would succeed. There is no retry or `systemctl restart nginx` fallback.
- The post-install health check (`check_health`, setup.py ~line 1078) only probes `http://127.0.0.1:8000/health` and `http://127.0.0.1:3000/` — **it never checks the nginx gateway on port 80**, so the log claims "All health checks passed; the stack is up" while the user-facing entry point is down.

## 2. Status-reporting defects in the summary

- **SAP ingestion reported `[OK]` despite failing.** The step printed `Ingestion failed: No validated SAP configuration is saved` and a warning, yet the bootstrap summary recorded `[OK ] SAP ingestion` (log lines 357–358 vs 403). A step that warns-and-continues should be recorded as `SKIP`/`WARN` with its reason, not `OK` — otherwise re-run triage is misleading.
- The final message "All health checks passed; the stack is up" printed even though nginx had already failed in the same run; the health step and the closing summary should be consistent about overall stack state.

## 3. Node toolchain drift (warning-level, will become a failure)

- The installer accepted Debian's Node **v20.19.2 / npm 9.2** because `NODE_MAJOR_MIN = 20` (setup.py line 102), but `npm install` emitted five `EBADENGINE` warnings: `@hey-api/openapi-ts@0.99.0` and its deps now require **node >= 22.18**, and `commander@15` requires >= 22.12 (log lines 255–279). The build happened to succeed, but the pinned NodeSource major is already 22 (`NODE_MAJOR_PINNED = 22`) and `AGENTS.md` §3 documents NodeSource 22.x — the minimum-accepted version has drifted below what the dependency tree actually supports.

## 4. Secret hygiene in installer output

- `run()` echoes every command before executing it, so the generated PostgreSQL password was printed in cleartext: `CREATE ROLE labish LOGIN PASSWORD 'doiCE4...'` (log line 237). Anyone capturing the install log (CI, terminal scrollback, support tickets — including this very file) now holds a live DB credential. The echo must redact secret-bearing arguments, and the exposed password on this host should be rotated.

## 5. Minor defects and warnings observed in the log

- **tarfile DeprecationWarning** during the Qdrant extract (log lines 32–33): `tar.extract(member, path=tmp)` needs `filter="data"` before Python 3.14 changes the default.
- **Deprecated/EOL npm packages**: `eslint@9.39.5` is flagged as no longer supported, and `@esbuild-kit/*` has merged into `tsx` (log lines 280–282) — dependency refresh needed in `apps/web/package.json`.
- Health coverage is thin even where it exists: Qdrant (`:6333`) and the Dramatiq worker are started but never health-checked; only FastAPI and Next.js are probed.
- `chown -R` over the whole repo and `/var/lib/qdrant` runs unconditionally on every bootstrap (log lines 361–363) — harmless but slow on re-runs; could be made conditional.

## 6. Delta summary

| # | Desired | Current | Severity |
|---|---------|---------|----------|
| 1 | nginx gateway up on port 80 after install | `systemctl enable --now nginx` fails; no diagnostics captured; no restart fallback | **Blocker** (observed failure) |
| 2 | Health check proves the user-facing stack works | Only probes :8000/:3000 directly; declares "stack is up" with nginx down; Qdrant/worker unchecked | High |
| 3 | Summary statuses match what actually happened | Failed SAP ingestion recorded as `[OK]` | Medium |
| 4 | Node toolchain satisfies the dependency tree | Node 20 accepted; @hey-api packages require >= 22.18 (EBADENGINE) | Medium |
| 5 | No secrets in installer output | Generated DB password echoed in cleartext | Medium (security) |
| 6 | Clean, warning-free install | tarfile deprecation; EOL eslint/@esbuild-kit deps; unconditional chown -R | Low |

**Bottom line:** the single-command install pipeline now exists and works — one failed step (nginx) stands between the current state and the stated goal, plus a short list of correctness and hygiene fixes surfaced by this first real end-to-end run.

> **Status update:** the checklist below has been implemented in `apps/api/app/setup.py`, `apps/web/package.json` and `.github/workflows/install-smoke.yml`, and validated on a clean `debian:12` container (nginx gateway answering on port 80, summary free of `FAIL`, DB password redacted). Remaining open items are operator actions on the affected host and two upstream-blocked dependency refreshes (noted inline).

---

## 7. Development checklist (updated from the `install_logs` run)

### A. Fix the nginx provisioning step (Blocker)

- [x] Reproduce and diagnose the `systemctl enable --now nginx` failure on a fresh Debian host; on failure, have `check_nginx` automatically capture and print `systemctl status nginx`, `journalctl -xeu nginx -n 50`, and `ss -ltnp 'sport = :80'` so the summary is actionable without a second SSH session.
- [x] Make nginx startup robust: fall back to `systemctl restart nginx` when `enable --now` fails (handles a wedged daemon left by the apt install), and verify the unit is `active` afterwards instead of assuming success.
- [x] Detect and report port-80 conflicts (another server, a lingering default-site worker) before attempting the start.
- [ ] Re-run the one-liner on the affected host after the fix and confirm the summary reports `[OK  ] nginx`. *(Operator action; if it still fails, the summary now includes the captured diagnostics.)*

### B. Harden the post-install health check

- [x] Add a gateway probe through nginx (`http://127.0.0.1:80/` and `/api/health` or equivalent) so the health step validates the path users actually hit, not just the upstreams.
- [x] Add a Qdrant liveness probe (`http://127.0.0.1:6333/healthz` or `/readyz`) and a worker check (`systemctl is-active worker` at minimum).
- [x] Only print "the stack is up" when **every** started service — including nginx — passed; otherwise state exactly which entry points are degraded.

### C. Fix summary status reporting

- [x] Change `check_sap_ingestion` (and any other warn-and-continue step) to record a `SKIP`/`WARN` outcome with its reason instead of `OK` when the step did not actually complete, so the `--- Bootstrap summary ---` is trustworthy for re-run triage.
- [x] Ensure the process exit code and final message reflect the true aggregate state (it already returns 1 on failure — keep the human-readable output consistent with that).

### D. Align the Node toolchain with the dependency tree

- [x] Raise `NODE_MAJOR_MIN` in `setup.py` to match what `apps/web`'s dependency tree requires (>= 22.18 per the `EBADENGINE` warnings), so the installer upgrades Debian's Node 20 to the pinned NodeSource 22.x instead of accepting it.
- [x] Update the `engines` field in `apps/web/package.json` to the same floor, and keep `setup.py`/`AGENTS.md` in sync per the installer-sync rule.

### E. Secret hygiene

- [x] Redact secret-bearing arguments in `run()`'s command echo (mask the psql `PASSWORD '...'` literal and any future secret parameters) so generated credentials never land in install logs.
- [ ] Rotate the PostgreSQL `labish` role password exposed in this captured log, and scrub/avoid committing logs containing live credentials. *(Operator action on the affected host: `sudo /opt/labish/install.sh --rotate-db-password` or `setup.py --yes --rotate-db-password` regenerates the credential, rewrites `/etc/labish/{api,web}.env` and restarts the services.)*

### F. Cleanup items

- [x] Pass `filter="data"` to the Qdrant `tar.extract(...)` call in `setup.py` to silence the Python 3.14 tarfile deprecation and harden the extraction.
- [ ] Refresh `apps/web` dev dependencies: move off EOL `eslint@9.39.x` and the deprecated `@esbuild-kit/*` packages (superseded by `tsx`). *(Blocked upstream: `eslint@10` crashes `eslint-plugin-react` as bundled by `eslint-config-next@16.3.x`, and `@esbuild-kit/esm-loader` is a transitive dependency of `drizzle-kit` (via `@payloadcms/db-postgres`) up to the latest `0.31.11`. Revisit when those release fixes.)*
- [x] Make the `chown -R` of `/opt/labish` and `/var/lib/qdrant` conditional (skip when ownership is already correct) to keep re-runs fast.

### G. Regression protection

- [x] Extend (or add) the clean-Debian CI install job to assert the nginx gateway answers on port 80 and that the bootstrap summary contains no `FAIL` lines, so this failure class is caught before release.
