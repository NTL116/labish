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

## Deployment

Production host configuration lives in [`deployment/`](deployment/):

- `nginx.conf` — reverse proxy routing `/api/*`, `/auth/*`, and `/health`
  to FastAPI (127.0.0.1:8000) and everything else to Next.js (127.0.0.1:3000).
- `systemd/fastapi.service` — Uvicorn application gateway.
- `systemd/worker.service` — Dramatiq background workers (`dramatiq app.tasks.main`).
- `systemd/qdrant.service` — local Qdrant vector search daemon.
- `systemd/nextjs.service` — Next.js production server (`npm run start`).

### Host provisioning

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib redis-server nodejs npm \
  python3-venv python3-pip nginx

# Install Qdrant locally (download the release binary for your platform
# from https://github.com/qdrant/qdrant/releases, then):
sudo mv qdrant /usr/local/bin/

# Backend virtual environment
cd apps/api
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -e .

# Frontend production build
cd ../web
npm install
npm run build
```

### Enabling the services

Unit files reference `/etc/labish/*.env` environment files for all
configuration (database URL, JWT key paths, Redis URL, site URL) — create
those first, then:

```bash
sudo cp deployment/systemd/*.service /etc/systemd/system/
sudo cp deployment/nginx.conf /etc/nginx/sites-available/labish
sudo ln -s /etc/nginx/sites-available/labish /etc/nginx/sites-enabled/labish
sudo systemctl daemon-reload
sudo systemctl enable --now qdrant fastapi worker nextjs
sudo nginx -t && sudo systemctl reload nginx
```