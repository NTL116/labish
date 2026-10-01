import uuid
from typing import Optional

from sqlmodel import Field, SQLModel


class SAPConfig(SQLModel, table=True):
    """SAP Business One Service Layer connection configuration.

    Single-tenant: one validated row acts as the gateway configuration
    and the single source of truth for federated identity. The password
    is stored encrypted (see ``app.core.security.encrypt_secret``).
    """

    id: Optional[uuid.UUID] = Field(
        default_factory=uuid.uuid4, primary_key=True, index=True
    )
    service_layer_url: str
    company_db: str
    username: str
    password: str  # encrypted at rest via core.security.encrypt_secret
    is_validated: bool = False
