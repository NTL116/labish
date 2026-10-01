"""FastAPI REST controller endpoints.

Routes handle HTTP validation, status codes, and routing only — no
direct SQL construction or external service calls.
"""

from app.routes.auth import router as auth_router
from app.routes.system import router as system_router

__all__ = ["auth_router", "system_router"]
