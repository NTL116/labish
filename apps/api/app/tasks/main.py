"""Worker entry point: `dramatiq app.tasks.main`.

Imports the broker configuration and every actor module so all tasks
register with the broker when the worker process starts.
"""

from app.tasks.broker import broker  # noqa: F401
from app.tasks.email_dispatch import send_welcome_email_task  # noqa: F401

__all__ = ["broker", "send_welcome_email_task"]
