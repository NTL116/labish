"""SAP Service Layer client skeleton.

Core enterprise infrastructure engine. Independent of AI status.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SAPResult:
    success: bool
    doc_entry: int | None = None
    error: str | None = None


class SAPServiceLayerClient:
    """Direct HTTP communication with the SAP Service Layer."""

    def create_sales_order(self, order_data: dict) -> SAPResult:
        try:
            # TODO(phase-later): real SAP Service Layer HTTP call.
            raise NotImplementedError("SAP Service Layer not configured")
        except Exception as exc:  # graceful degradation — never crash callers
            logger.warning("SAP create_sales_order failed: %s", exc)
            return SAPResult(success=False, error=str(exc))
