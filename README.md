# Labish

Labish is organized as two applications:

- `front end/` — Next.js corporate and family website.
- `Services/` — FastAPI services.

## Front End

```bash
cd "front end"
npm install
npm run dev
```

The site is available at [http://localhost:3000](http://localhost:3000). Run
`npm run lint` and `npm run build` from `front end/` to validate a release.

Set `NEXT_PUBLIC_SITE_URL` to the deployed site origin for canonical news
sharing links.

## Services

Use Python 3.11 or newer. See [`Services/README.md`](Services/README.md) for
virtual environment setup, dependency installation, local server, and tests.