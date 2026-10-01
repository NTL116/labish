"""SMTP client skeleton for host-level email delivery."""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailResult:
    success: bool
    error: str | None = None


class SMTPClient:
    def send_email(self, to_address: str, subject: str, body: str) -> EmailResult:
        try:
            # TODO(phase-later): real smtplib delivery via host SMTP.
            raise NotImplementedError("SMTP delivery not configured")
        except Exception as exc:  # graceful degradation — never crash callers
            logger.warning("Email delivery to %s failed: %s", to_address, exc)
            return EmailResult(success=False, error=str(exc))
