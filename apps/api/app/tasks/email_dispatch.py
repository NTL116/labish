import uuid

import dramatiq

import app.tasks.broker  # noqa: F401  (ensures the broker is configured)
from app.integrations.email.smtp_client import SMTPClient


@dramatiq.actor
def send_welcome_email_task(user_id: str, email: str) -> None:
    """Send a welcome email to a newly created user."""
    client = SMTPClient()
    client.send_email(
        to_address=email,
        subject="Welcome to Labish",
        body=f"Welcome! Your account {uuid.UUID(user_id)} is ready.",
    )
