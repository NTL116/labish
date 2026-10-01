from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request


def register_middleware(app: FastAPI) -> None:
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
