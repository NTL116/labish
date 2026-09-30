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