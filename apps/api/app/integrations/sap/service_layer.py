"""SAP Business One Service Layer client.

Core enterprise infrastructure engine. Independent of AI status.

Pure, deterministic integration layer: accepts strictly typed Python
inputs and returns strictly typed Python structures. All network
operations are wrapped in structured ``try/except`` blocks so a failure
in SAP never crashes the FastAPI or Dramatiq process loop.
"""

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 15.0


@dataclass(frozen=True)
class SAPResult:
    success: bool
    doc_entry: int | None = None
    error: str | None = None


@dataclass(frozen=True)
class SAPLoginResult:
    """Outcome of a Service Layer login challenge."""

    success: bool
    session_id: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class SAPIdentity:
    """Federated identity resolved against SAP B1 master data."""

    authenticated: bool
    role: str | None = None  # "admin" | "staff" | "client"
    subject: str | None = None
    error: str | None = None


class SAPServiceLayerClient:
    """Direct HTTP communication with the SAP Service Layer."""

    def __init__(
        self,
        service_layer_url: str | None = None,
        company_db: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self.service_layer_url = (service_layer_url or "").rstrip("/")
        self.company_db = company_db
        self.username = username
        self.password = password
        self._session_id: str | None = None

    # -- low-level -----------------------------------------------------

    def _client(self) -> httpx.AsyncClient:
        headers = {}
        if self._session_id:
            headers["Cookie"] = f"B1SESSION={self._session_id}"
        return httpx.AsyncClient(
            base_url=self.service_layer_url,
            headers=headers,
            timeout=_REQUEST_TIMEOUT,
        )

    async def login(
        self,
        username: str | None = None,
        password: str | None = None,
    ) -> SAPLoginResult:
        """Send a live login challenge to the external SAP Service Layer."""
        if not self.service_layer_url or not self.company_db:
            return SAPLoginResult(
                success=False, error="SAP Service Layer is not configured"
            )
        payload = {
            "CompanyDB": self.company_db,
            "UserName": username if username is not None else self.username,
            "Password": password if password is not None else self.password,
        }
        try:
            async with self._client() as client:
                response = await client.post("/Login", json=payload)
            if response.status_code == 200:
                session_id = response.json().get("SessionId")
                if username is None and password is None:
                    self._session_id = session_id
                return SAPLoginResult(success=True, session_id=session_id)
            return SAPLoginResult(
                success=False,
                error=f"SAP login rejected (HTTP {response.status_code})",
            )
        except Exception as exc:  # graceful degradation — never crash callers
            logger.warning("SAP Service Layer login failed: %s", exc)
            return SAPLoginResult(success=False, error=str(exc))

    async def _get(self, path: str, params: dict | None = None) -> dict | None:
        try:
            async with self._client() as client:
                response = await client.get(path, params=params)
            if response.status_code == 200:
                return response.json()
            logger.warning(
                "SAP Service Layer GET %s returned HTTP %s",
                path,
                response.status_code,
            )
            return None
        except Exception as exc:  # graceful degradation — never crash callers
            logger.warning("SAP Service Layer GET %s failed: %s", path, exc)
            return None

    # -- identity federation lookups -----------------------------------

    async def find_employee_by_email(self, email: str) -> dict | None:
        """Look up an internal staff record in SAP's EmployeesInfo."""
        data = await self._get(
            "/EmployeesInfo",
            params={"$filter": f"eMail eq '{email}'", "$top": "1"},
        )
        if data and data.get("value"):
            return data["value"][0]
        return None

    async def is_superuser(self, user_code: str) -> bool:
        """Check the SAP B1 Users object administrative/SuperUser flag."""
        data = await self._get(
            "/Users",
            params={"$filter": f"UserCode eq '{user_code}'", "$top": "1"},
        )
        if data and data.get("value"):
            return data["value"][0].get("Superuser") == "tYES"
        return False

    async def find_business_partner_by_contact_email(
        self, email: str
    ) -> dict | None:
        """Match an email against the BusinessPartners contacts matrix.

        Covers Leads (cLid), Customers (cCustomer), and Vendors
        (cSupplier) via both the card-level and contact-employee emails.
        """
        data = await self._get(
            "/BusinessPartners",
            params={
                "$filter": (
                    f"EmailAddress eq '{email}' or "
                    f"ContactEmployees/any(c: c/E_Mail eq '{email}')"
                ),
                "$top": "1",
            },
        )
        if data and data.get("value"):
            partner = data["value"][0]
            if partner.get("CardType") in ("cLid", "cCustomer", "cSupplier"):
                return partner
        return None

    # -- high-level federation -----------------------------------------

    async def authenticate_identity(
        self, email: str, password: str
    ) -> SAPIdentity:
        """Resolve a federated identity for the submitted credentials.

        1. Internal staff: match EmployeesInfo by email, then verify the
           submitted password with a live login challenge as the linked
           SAP user; elevate to admin when the Users SuperUser flag is on.
        2. Business partner: match the BusinessPartners contacts matrix
           (Lead/Customer/Vendor) and assign the client role.
        """
        service_login = await self.login()
        if not service_login.success:
            return SAPIdentity(authenticated=False, error=service_login.error)

        employee = await self.find_employee_by_email(email)
        if employee is not None:
            user_code = (
                employee.get("ApplicationUserID")
                or employee.get("UserCode")
                or email
            )
            challenge = await self.login(
                username=str(user_code), password=password
            )
            if not challenge.success:
                return SAPIdentity(
                    authenticated=False, error="Invalid SAP credentials"
                )
            role = (
                "admin" if await self.is_superuser(str(user_code)) else "staff"
            )
            return SAPIdentity(authenticated=True, role=role, subject=email)

        partner = await self.find_business_partner_by_contact_email(email)
        if partner is not None:
            contact_password = partner.get("Password")
            contacts = partner.get("ContactEmployees") or []
            matched_contact = next(
                (c for c in contacts if c.get("E_Mail") == email), None
            )
            if matched_contact is not None:
                contact_password = (
                    matched_contact.get("Password") or contact_password
                )
            if contact_password is None or contact_password != password:
                return SAPIdentity(
                    authenticated=False, error="Invalid SAP credentials"
                )
            return SAPIdentity(
                authenticated=True, role="client", subject=email
            )

        return SAPIdentity(
            authenticated=False, error="No matching SAP identity"
        )

    # -- documents ------------------------------------------------------

    def create_sales_order(self, order_data: dict) -> SAPResult:
        try:
            # TODO(phase-later): real SAP Service Layer HTTP call.
            raise NotImplementedError("SAP Service Layer not configured")
        except Exception as exc:  # graceful degradation — never crash callers
            logger.warning("SAP create_sales_order failed: %s", exc)
            return SAPResult(success=False, error=str(exc))
