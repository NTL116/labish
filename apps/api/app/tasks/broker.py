"""Dramatiq broker configuration.

Uses a Redis broker in normal environments and an in-memory StubBroker
in the ``test`` environment so the suite never requires a live Redis.
"""

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.brokers.stub import StubBroker

from app.core.config import get_settings


def configure_broker() -> dramatiq.Broker:
    settings = get_settings()
    if settings.environment == "test":
        broker: dramatiq.Broker = StubBroker()
    else:
        broker = RedisBroker(url=settings.redis_url)
    dramatiq.set_broker(broker)
    return broker


broker = configure_broker()
