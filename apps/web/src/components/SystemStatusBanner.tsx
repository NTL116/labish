import { Suspense } from "react";
import { sapStatusSettingsSapStatusGet } from "@/lib/api";
import { configureApiClient } from "@/lib/session";

const BANNER_TIMEOUT_MS = 3000;

async function StatusBannerContent() {
  let isDegraded = false;
  let phoneNumber: string | null = null;

  try {
    configureApiClient();
    const { data } = await sapStatusSettingsSapStatusGet({
      // A hung backend must never stall public page streaming.
      signal: AbortSignal.timeout(BANNER_TIMEOUT_MS),
      cache: "no-store",
    });
    if (data) {
      isDegraded = !data.is_validated || !data.is_connected;
      phoneNumber = data.fallback_phone_number ?? null;
    } else {
      isDegraded = true;
    }
  } catch {
    // Backend unreachable: degrade gracefully, keep the page serving.
    isDegraded = true;
  }

  if (!isDegraded) {
    return null;
  }

  return (
    <aside
      role="status"
      aria-live="polite"
      className="w-full border-b border-amber-300 bg-amber-50 px-4 py-3 text-center font-sans text-[11px] font-medium uppercase tracking-[0.12em] text-amber-900"
    >
      Our systems are currently experiencing an optimization delay. For
      immediate assistance, please call our service center directly
      {phoneNumber ? (
        <>
          {" at "}
          <a
            href={`tel:${phoneNumber.replace(/[^+\d]/g, "")}`}
            className="underline underline-offset-2"
          >
            {phoneNumber}
          </a>
        </>
      ) : null}
      .
    </aside>
  );
}

/**
 * Global warning banner surfaced on every page when the platform is not
 * yet configured or the SAP Service Layer connection has dropped.
 *
 * Wrapped in Suspense so the status probe streams in after the page
 * shell: public pages and their JS assets always load normally.
 */
export default function SystemStatusBanner() {
  return (
    <Suspense fallback={null}>
      <StatusBannerContent />
    </Suspense>
  );
}
