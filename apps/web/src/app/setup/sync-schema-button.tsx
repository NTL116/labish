"use client";

import { useFormStatus } from "react-dom";

/**
 * High-visibility execution button for the SAP schema sync.
 *
 * Client component so `useFormStatus` can surface dynamic progress
 * messaging while the ingestion round-trip is in flight.
 */
export default function SyncSchemaButton() {
  const { pending } = useFormStatus();

  return (
    <div className="space-y-3">
      <button
        type="submit"
        disabled={pending}
        aria-busy={pending}
        className="inline-flex min-h-12 w-full items-center justify-center rounded-[6px] bg-swiss-ink px-6 font-sans text-[11px] font-semibold uppercase tracking-[0.18em] text-swiss-cream transition-opacity hover:opacity-75 disabled:cursor-wait disabled:opacity-50"
      >
        {pending
          ? "Syncing SAP Schema…"
          : "Sync SAP Schema & Re-Ingest Data Dictionary"}
      </button>
      {pending ? (
        <p
          role="status"
          className="font-sans text-[10px] font-medium uppercase tracking-[0.14em] text-swiss-slate"
        >
          Pulling $metadata, rebuilding the data dictionary and
          regenerating TypeScript definitions…
        </p>
      ) : null}
    </div>
  );
}
