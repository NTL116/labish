"""Automated SAP metadata re-ingestion cycle.

Background Dramatiq actor that re-runs the metadata ingestion engine on
a cycle or cron routine so the data dictionary, UDF catalogue, and the
frontend ``sap.d.ts`` type definitions stay synchronized with SAP B1
without manual intervention.
"""

import asyncio
import logging

import dramatiq

import app.tasks.broker  # noqa: F401  (ensures the broker is configured)
from app.shared.ingest_sap_metadata import ingest_from_saved_config

logger = logging.getLogger(__name__)


@dramatiq.actor(actor_name="sync_sap_metadata_task")
def sync_sap_metadata_task() -> None:
    """Fetch SAP $metadata updates and refresh dictionary + types."""
    result = asyncio.run(ingest_from_saved_config())
    if result.success:
        logger.info(
            "SAP metadata cycle complete: %s entities, %s complex types "
            "synchronized.",
            result.entities,
            result.complex_types,
        )
    else:
        # Graceful degradation: a SAP outage must never crash the
        # Dramatiq process loop; the next cycle simply retries.
        logger.warning("SAP metadata cycle skipped: %s", result.error)
