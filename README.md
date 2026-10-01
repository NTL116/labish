# Labish

Labish is organized as two applications:

- `apps/web/` — Next.js corporate and family website.
- `apps/api/` — FastAPI services.

## Front End

```bash
cd apps/web
npm install
npm run dev
```

The site is available at [http://localhost:3000](http://localhost:3000). Run
`npm run lint` and `npm run build` from `apps/web/` to validate a release.

Set `NEXT_PUBLIC_SITE_URL` to the deployed site origin for canonical news
sharing links.

## Services

Use Python 3.11 or newer. See [`apps/api/README.md`](apps/api/README.md) for
virtual environment setup, dependency installation, local server, and tests.

## Installation (single command)

On a fresh Debian host, install the entire stack — PostgreSQL, Redis,
Qdrant, FastAPI, the Dramatiq worker, Next.js, and nginx — with one command:

```bash
curl -fsSL https://raw.githubusercontent.com/NTL116/labish/main/install.sh | sudo bash
```

`install.sh` is a thin wrapper: it installs `git`/`curl`/`python3`, clones
the repository into `/opt/labish` (override with `LABISH_INSTALL_DIR`), and
hands off to the provisioning engine `apps/api/app/setup.py --yes`, which:

1. Installs missing system packages via apt (PostgreSQL, Redis, nginx, openssl).
2. Installs a pinned Node.js toolchain (NodeSource 22.x) when the host node is
   missing or older than Node 20.
3. Downloads the pinned Qdrant release (checksum-verified) to
   `/usr/local/bin/qdrant`.
4. Creates `apps/api/venv` and installs backend dependencies.
5. Exports `openapi.json` offline (no running backend needed) and runs
   `npm install`, `npm run generate-client`, and `npm run build`.
6. Generates a persistent RS256 JWT keypair under `/etc/labish/keys/`.
7. Creates the PostgreSQL role and the `labish` + `labish_payload`
   databases with a generated password and runs `alembic upgrade head`.
8. Populates `/etc/labish/{api,web,qdrant}.env` with every required key.
9. Renders the `deployment/` systemd and nginx templates with the real
   user/paths/server name, installs them, enables and starts all services,
   and health-checks `/health` and the site root.

The bootstrapper is **resumable and idempotent**: a failing step is recorded
and the remaining steps still run, a final summary lists anything that needs
attention, and re-running the one-liner on a provisioned host is a safe
no-op/upgrade. Useful knobs (env vars for `install.sh`, flags for
`setup.py`): `LABISH_SERVER_NAME`/`--server-name`, `LABISH_SITE_URL`/
`--site-url`, `LABISH_SERVICE_USER`/`--service-user`, and `--skip-*` flags
for each step.

### Environment files

The systemd units read all configuration from `/etc/labish/*.env` (populated
automatically by the installer; existing values are preserved on re-runs):

| File | Key | Purpose |
|------|-----|---------|
| `api.env` | `LABISH_ENVIRONMENT` | `production` |
| `api.env` | `LABISH_DATABASE_URL` | asyncpg DSN for the `labish` database (generated credentials) |
| `api.env` | `LABISH_REDIS_URL` | Redis broker/cache URL |
| `api.env` | `LABISH_JWT_PRIVATE_KEY_PATH` / `LABISH_JWT_PUBLIC_KEY_PATH` | persistent RS256 keypair in `/etc/labish/keys/` |
| `web.env` | `NODE_ENV`, `PORT` | Next.js production runtime |
| `web.env` | `NEXT_PUBLIC_SITE_URL` | public site origin (canonical links) |
| `web.env` | `DATABASE_URI` | Payload CMS PostgreSQL DSN (`labish_payload`) |
| `web.env` | `PAYLOAD_SECRET` | generated Payload CMS secret |
| `qdrant.env` | `QDRANT__SERVICE__HTTP_PORT`, `QDRANT__STORAGE__*` | Qdrant service/storage paths under `/var/lib/qdrant` |

## Deployment

Production host configuration lives in [`deployment/`](deployment/) as
**templates** rendered by `apps/api/app/setup.py` (never installed verbatim):

- `nginx.conf.template` — reverse proxy routing `/api/*`, `/auth/*`, and `/health`
  to FastAPI (127.0.0.1:8000) and everything else to Next.js (127.0.0.1:3000);
  `${SERVER_NAME}` is substituted at install time.
- `systemd/fastapi.service.template` — Uvicorn application gateway.
- `systemd/worker.service.template` — Dramatiq background workers (`dramatiq app.tasks.main`).
- `systemd/qdrant.service.template` — local Qdrant vector search daemon.
- `systemd/nextjs.service.template` — Next.js production server (`npm run start`)
  pinned to the installer-provisioned Node toolchain.

### Manual path

The manual steps below mirror what `setup.py` automates (the bootstrapper is
the source of truth — prefer `sudo python3 apps/api/app/setup.py --yes`):

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib redis-server \
  python3-venv python3-pip nginx openssl

# Pinned Node.js toolchain (NodeSource 22.x)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo bash -
sudo apt install -y nodejs

# Pinned Qdrant release binary
curl -fsSL -o qdrant.tar.gz \
  https://github.com/qdrant/qdrant/releases/download/v1.13.4/qdrant-x86_64-unknown-linux-gnu.tar.gz
tar -xzf qdrant.tar.gz qdrant && sudo install -m 0755 qdrant /usr/local/bin/qdrant

# Backend virtual environment
cd apps/api
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -e '.[dev]'

# Offline OpenAPI export + frontend production build
LABISH_ENVIRONMENT=test venv/bin/python -c \
  'import json,sys; from app.main import app; json.dump(app.openapi(), sys.stdout)' \
  > ../web/openapi.json
cd ../web
npm install
OPENAPI_INPUT=./openapi.json npm run generate-client
npm run build
```

Then run `sudo python3 apps/api/app/setup.py --yes --skip-frontend` to
provision the database, secrets, environment files, systemd units, and nginx
— or perform those steps by hand following the list in the installation
section above.
