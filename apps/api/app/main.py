from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request

app = FastAPI(
    title="Labish Services",
    version="0.1.0",
    description="Backend services for the Labish application.",
)


@app.middleware("http")
async def add_request_metadata(request: Request, call_next):
    request_id = uuid4().hex
    started_at = perf_counter()
    request.state.request_id = request_id

    response = await call_next(request)
    elapsed_ms = (perf_counter() - started_at) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
    return response


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}