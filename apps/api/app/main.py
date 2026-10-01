from fastapi import FastAPI

from app.core.middleware import register_middleware
from app.routes import auth_router, system_router

app = FastAPI(
    title="Labish Services",
    version="0.1.0",
    description="Backend services for the Labish application.",
)

register_middleware(app)

app.include_router(system_router)
app.include_router(auth_router)
