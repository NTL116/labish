"""Automated SAP Metadata Ingestion Engine.

Standalone, asynchronous utility that pulls the complete raw OData
``$metadata`` XML schema document from the SAP Business One Service
Layer (via :class:`SAPServiceLayerClient`), then compiles it into the
two single-source-of-truth artifacts shared across the monorepo:

1. **Data dictionary** — one JSON file per ``<EntityType>`` /
   ``<ComplexType>`` (native fields and User-Defined Fields alike),
   keyed by the true underlying SAP physical database table
   (``BusinessPartners`` -> ``ocrd.json``, ``Invoices`` -> ``oinv.json``)
   and dumped into ``apps/api/app/shared/sap_dictionary/``.
2. **TypeScript definitions** — a unified, strictly-typed definition
   file compiled to ``apps/web/src/types/sap.d.ts`` mapping OData
   primitives to TypeScript primitives.

The engine can be executed from the management endpoint
(``POST /settings/sap/ingest``), the Dramatiq re-ingestion cycle actor
(``app.tasks.sap_sync``), the fresh-install wizard
(``apps/api/app/setup.py``), or directly::

    python -m app.shared.ingest_sap_metadata
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree

from app.integrations.sap.service_layer import SAPServiceLayerClient

logger = logging.getLogger(__name__)

# Resolved monorepo layout, anchored on this file's location:
# <repo>/apps/api/app/shared/ingest_sap_metadata.py
_SHARED_DIR = Path(__file__).resolve().parent
REPO_ROOT = _SHARED_DIR.parent.parent.parent.parent
DICTIONARY_DIR = _SHARED_DIR / "sap_dictionary"
TYPESCRIPT_OUTPUT = REPO_ROOT / "apps" / "web" / "src" / "types" / "sap.d.ts"

# EDMX namespaces used by the SAP B1 Service Layer $metadata document
# (OData v4 first, with the legacy v3 namespace as a fallback).
_SCHEMA_NAMESPACES = (
    "http://docs.oasis-open.org/odata/ns/edm",
    "http://schemas.microsoft.com/ado/2009/11/edm",
)

# Service Layer entity -> true underlying SAP B1 physical database table.
# Entities missing from this map fall back to a sanitized entity name.
ENTITY_TABLE_MAP: dict[str, str] = {
    "BusinessPartners": "OCRD",
    "Invoices": "OINV",
    "CreditNotes": "ORIN",
    "Orders": "ORDR",
    "Quotations": "OQUT",
    "DeliveryNotes": "ODLN",
    "Returns": "ORDN",
    "PurchaseOrders": "OPOR",
    "PurchaseInvoices": "OPCH",
    "PurchaseCreditNotes": "ORPC",
    "PurchaseDeliveryNotes": "OPDN",
    "PurchaseQuotations": "OPQT",
    "PurchaseReturns": "ORPD",
    "DownPayments": "ODPI",
    "PurchaseDownPayments": "ODPO",
    "IncomingPayments": "ORCT",
    "VendorPayments": "OVPM",
    "JournalEntries": "OJDT",
    "Items": "OITM",
    "ItemGroups": "OITB",
    "Warehouses": "OWHS",
    "PriceLists": "OPLN",
    "EmployeesInfo": "OHEM",
    "Users": "OUSR",
    "SalesPersons": "OSLP",
    "Projects": "OPRJ",
    "Activities": "OCLG",
    "ServiceCalls": "OSCL",
    "Contracts": "OCTR",
    "ChartOfAccounts": "OACT",
    "Currencies": "OCRN",
    "Countries": "OCRY",
    "States": "OCST",
    "PaymentTermsTypes": "OCTG",
    "SalesTaxCodes": "OSTC",
    "VatGroups": "OVTG",
    "BusinessPartnerGroups": "OCRG",
    "ContactEmployees": "OCPR",
    "ProductionOrders": "OWOR",
    "InventoryGenEntries": "OIGN",
    "InventoryGenExits": "OIGE",
    "StockTransfers": "OWTR",
    "BatchNumberDetails": "OBTN",
    "SerialNumberDetails": "OSRN",
    "UserFieldsMD": "CUFD",
    "UserTablesMD": "OUTB",
}

# OData primitive -> TypeScript primitive mapping used by the compiler.
ODATA_TO_TYPESCRIPT: dict[str, str] = {
    "Edm.String": "string",
    "Edm.Guid": "string",
    "Edm.Binary": "string",
    "Edm.DateTime": "string",
    "Edm.DateTimeOffset": "string",
    "Edm.Date": "string",
    "Edm.Time": "string",
    "Edm.TimeOfDay": "string",
    "Edm.Duration": "string",
    "Edm.Decimal": "number",
    "Edm.Double": "number",
    "Edm.Single": "number",
    "Edm.Int16": "number",
    "Edm.Int32": "number",
    "Edm.Int64": "number",
    "Edm.Byte": "number",
    "Edm.SByte": "number",
    "Edm.Boolean": "boolean",
}


@dataclass(frozen=True)
class IngestResult:
    """Outcome of a full metadata ingestion pass."""

    success: bool
    entities: int = 0
    complex_types: int = 0
    dictionary_files: tuple[str, ...] = field(default_factory=tuple)
    typescript_file: str | None = None
    error: str | None = None


def _physical_table(entity_name: str) -> str:
    """Map an entity description to its true SAP physical table name."""
    mapped = ENTITY_TABLE_MAP.get(entity_name)
    if mapped:
        return mapped.lower()
    # Fallback: sanitized lowercase entity name keeps unknown/UDT
    # entities addressable without colliding with filesystem rules.
    return re.sub(r"[^a-z0-9_]", "_", entity_name.lower())


def _edm_to_typescript(edm_type: str) -> str:
    """Map an OData primitive (or collection/complex ref) to TypeScript."""
    if edm_type.startswith("Collection(") and edm_type.endswith(")"):
        return f"{_edm_to_typescript(edm_type[len('Collection('):-1])}[]"
    if edm_type in ODATA_TO_TYPESCRIPT:
        return ODATA_TO_TYPESCRIPT[edm_type]
    if edm_type.startswith("Edm."):
        return "unknown"
    # Non-primitive: reference to another ComplexType/EntityType in the
    # same schema document (namespace-qualified).
    return _sanitize_type_name(edm_type.rsplit(".", 1)[-1])


def _sanitize_type_name(name: str) -> str:
    """Produce a valid TypeScript interface identifier."""
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"SAP_{cleaned}"
    return cleaned


def parse_metadata_xml(metadata_xml: str) -> dict[str, dict]:
    """Parse ``<EntityType>`` and ``<ComplexType>`` nodes from $metadata.

    Returns a mapping of type name -> structural description containing
    the node kind, resolved physical table, key fields, and every
    property (native fields and UDFs) with its core structural metadata.
    """
    root = ElementTree.fromstring(metadata_xml)
    parsed: dict[str, dict] = {}

    for namespace in _SCHEMA_NAMESPACES:
        schemas = root.findall(f".//{{{namespace}}}Schema")
        if not schemas:
            continue
        for schema in schemas:
            for kind in ("EntityType", "ComplexType"):
                for node in schema.findall(f"{{{namespace}}}{kind}"):
                    name = node.get("Name")
                    if not name:
                        continue
                    key_fields = [
                        ref.get("Name")
                        for ref in node.findall(
                            f"{{{namespace}}}Key/{{{namespace}}}PropertyRef"
                        )
                        if ref.get("Name")
                    ]
                    properties = []
                    for prop in node.findall(f"{{{namespace}}}Property"):
                        prop_name = prop.get("Name")
                        if not prop_name:
                            continue
                        edm_type = prop.get("Type", "Edm.String")
                        properties.append(
                            {
                                "name": prop_name,
                                "edm_type": edm_type,
                                "typescript_type": _edm_to_typescript(
                                    edm_type
                                ),
                                "nullable": prop.get("Nullable", "true")
                                != "false",
                                "max_length": prop.get("MaxLength"),
                                "is_key": prop_name in key_fields,
                                # Service Layer exposes UDFs with the
                                # canonical SAP "U_" column prefix.
                                "is_udf": prop_name.startswith("U_"),
                            }
                        )
                    parsed[name] = {
                        "entity": name,
                        "kind": kind,
                        "physical_table": _physical_table(name),
                        "key_fields": key_fields,
                        "properties": properties,
                    }
        if parsed:
            break

    return parsed


def write_dictionary(
    parsed: dict[str, dict], dictionary_dir: Path | None = None
) -> list[Path]:
    """Dump one clean JSON dictionary file per parsed type.

    Files are named after the true underlying SAP physical table
    (``ocrd.json``, ``oinv.json``, ...).
    """
    target_dir = dictionary_dir or DICTIONARY_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for description in parsed.values():
        path = target_dir / f"{description['physical_table']}.json"
        path.write_text(
            json.dumps(description, indent=2, sort_keys=False) + "\n"
        )
        written.append(path)
    return written


def compile_typescript(
    parsed: dict[str, dict], typescript_output: Path | None = None
) -> Path:
    """Compile the unified, strictly-typed ``sap.d.ts`` definition file."""
    output = typescript_output or TYPESCRIPT_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "// AUTO-GENERATED by apps/api/app/shared/ingest_sap_metadata.py",
        "// Single source of truth for SAP Business One entity shapes.",
        "// Do NOT edit by hand — run POST /settings/sap/ingest or the",
        "// sync_sap_metadata_task Dramatiq actor to regenerate.",
        "",
    ]
    for name in sorted(parsed):
        description = parsed[name]
        interface_name = _sanitize_type_name(name)
        lines.append(
            f"/** {description['kind']} `{name}` "
            f"(SAP table `{description['physical_table'].upper()}`). */"
        )
        lines.append(f"export interface {interface_name} {{")
        for prop in description["properties"]:
            optional = "?" if prop["nullable"] else ""
            ts_type = prop["typescript_type"]
            if prop["nullable"]:
                ts_type = f"{ts_type} | null"
            lines.append(f"  {prop['name']}{optional}: {ts_type};")
        lines.append("}")
        lines.append("")

    output.write_text("\n".join(lines))
    return output


async def ingest_sap_metadata(
    client: SAPServiceLayerClient,
    *,
    dictionary_dir: Path | None = None,
    typescript_output: Path | None = None,
) -> IngestResult:
    """Run a full ingestion pass: fetch, parse, dump JSON, compile TS."""
    login = await client.login()
    if not login.success:
        return IngestResult(
            success=False,
            error=login.error or "SAP Service Layer login failed",
        )

    metadata_xml = await client.get_metadata_xml()
    if not metadata_xml:
        return IngestResult(
            success=False,
            error="Could not fetch the SAP $metadata schema document",
        )

    try:
        parsed = parse_metadata_xml(metadata_xml)
    except ElementTree.ParseError as exc:
        logger.warning("SAP $metadata XML parse failed: %s", exc)
        return IngestResult(
            success=False, error=f"Invalid $metadata XML: {exc}"
        )
    if not parsed:
        return IngestResult(
            success=False,
            error="No EntityType/ComplexType nodes found in $metadata",
        )

    dictionary_files = write_dictionary(parsed, dictionary_dir)
    typescript_file = compile_typescript(parsed, typescript_output)

    entity_count = sum(
        1 for d in parsed.values() if d["kind"] == "EntityType"
    )
    complex_count = len(parsed) - entity_count
    logger.info(
        "SAP metadata ingested: %s entities, %s complex types, %s "
        "dictionary files, types compiled to %s",
        entity_count,
        complex_count,
        len(dictionary_files),
        typescript_file,
    )
    return IngestResult(
        success=True,
        entities=entity_count,
        complex_types=complex_count,
        dictionary_files=tuple(str(p) for p in dictionary_files),
        typescript_file=str(typescript_file),
    )


async def ingest_from_saved_config() -> IngestResult:
    """Load the validated SAPConfig row and run a full ingestion pass."""
    # Imported lazily so the parser/compiler stay usable standalone.
    from sqlmodel import select

    from app.core.security import decrypt_secret
    from app.db.session import get_sessionmaker
    from app.models import SAPConfig

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        result = await session.execute(
            select(SAPConfig).where(
                SAPConfig.is_validated == True  # noqa: E712
            )
        )
        config = result.scalars().first()

    if config is None:
        return IngestResult(
            success=False,
            error="No validated SAP configuration is saved",
        )

    client = SAPServiceLayerClient(
        service_layer_url=config.service_layer_url,
        company_db=config.company_db,
        username=config.username,
        password=decrypt_secret(config.password),
    )
    return await ingest_sap_metadata(client)


def main() -> int:
    """CLI entry point: ``python -m app.shared.ingest_sap_metadata``."""
    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(ingest_from_saved_config())
    if result.success:
        print(
            f"Ingested {result.entities} entities and "
            f"{result.complex_types} complex types; compiled "
            f"{result.typescript_file}."
        )
        return 0
    print(f"Ingestion failed: {result.error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
