# Labish Services

Standalone FastAPI services for the Labish application.

## Requirements

- Python 3.11 or newer; Python 3.13.5 is the current development version.
- `pip` and the standard-library `venv` support for that Python installation.

On Debian or Ubuntu, if virtual environment creation fails because `ensurepip`
is unavailable, install the matching venv package first (for example,
`python3.13-venv` when using Python 3.13).

## Local development

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
uvicorn app.main:app --reload --port 8000
```

Run tests with:

```bash
pytest
```

The initial service exposes `GET /health`. Responses include `X-Request-ID` and
`X-Response-Time-Ms` headers from the request metadata middleware.
