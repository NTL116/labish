# SAP Data Dictionary

Generated single source of truth for SAP Business One entity shapes.

One JSON file per `<EntityType>` / `<ComplexType>` parsed from the
Service Layer `$metadata` document, named after the true underlying SAP
physical database table (`ocrd.json` for BusinessPartners, `oinv.json`
for Invoices, ...). Each file lists every property (native fields and
`U_*` User-Defined Fields) with its EDM type, TypeScript type,
nullability, max length, and key/UDF flags.

Regenerate with `POST /settings/sap/ingest`, the
`sync_sap_metadata_task` Dramatiq actor, or
`python -m app.shared.ingest_sap_metadata`. The same pass compiles
`apps/web/src/types/sap.d.ts` for the frontend workspace.
