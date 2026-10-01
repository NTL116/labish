import Breadcrumb from "@/components/breadcrumb";
import Footer from "@/components/footer";
import SideRail from "@/components/side-rail";
import { saveSapConnectionAction, testSapConnectionAction } from "./actions";

const STATUS_MESSAGES: Record<string, { text: string; tone: "ok" | "error" }> = {
  "test-ok": {
    text: "SAP Service Layer connection verified successfully.",
    tone: "ok",
  },
  saved: {
    text: "Configuration verified and saved. The gateway is now active.",
    tone: "ok",
  },
  "test-failed": {
    text: "SAP Service Layer test login failed. Check the connection details.",
    tone: "error",
  },
  "save-failed": {
    text: "Could not verify and save the configuration. Check the connection details.",
    tone: "error",
  },
  error: {
    text: "The submitted form was incomplete. Please fill in every field.",
    tone: "error",
  },
};

const inputClass =
  "mt-2 block w-full border-0 border-b border-swiss-slate/30 bg-transparent px-0 py-3 text-sm normal-case tracking-normal text-swiss-ink outline-none transition-colors placeholder:text-swiss-slate/70 focus:border-swiss-ink";

const labelClass =
  "block font-sans text-[9px] font-medium uppercase tracking-[0.14em] text-swiss-slate";

export default async function SetupPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string }>;
}) {
  const { status } = await searchParams;
  const message = status ? STATUS_MESSAGES[status] : undefined;

  return (
    <article className="stationery-sheet">
      <section className="canvas-left flex flex-col gap-10">
        <Breadcrumb />
        <div className="space-y-6">
          <h1 className="font-serif text-4xl font-light">System Setup</h1>
          <p className="max-w-md font-sans text-sm text-swiss-slate">
            Connect the platform to the SAP Business One Service Layer and
            provide a fallback service-center number shown to visitors
            whenever connectivity is degraded.
          </p>
          {message ? (
            <p
              role="alert"
              className={`max-w-md font-sans text-[10px] font-medium uppercase tracking-[0.14em] ${
                message.tone === "ok" ? "text-emerald-700" : "text-red-700"
              }`}
            >
              {message.text}
            </p>
          ) : null}
          <form className="max-w-sm space-y-5 pt-2">
            <label className={labelClass}>
              Service Layer URL
              <input
                name="service_layer_url"
                type="url"
                required
                placeholder="https://sap.example.com:50000/b1s/v1"
                className={inputClass}
              />
            </label>
            <label className={labelClass}>
              Company Database
              <input
                name="company_db"
                type="text"
                required
                className={inputClass}
              />
            </label>
            <label className={labelClass}>
              Username
              <input
                name="username"
                type="text"
                required
                autoComplete="off"
                className={inputClass}
              />
            </label>
            <label className={labelClass}>
              Password
              <input
                name="password"
                type="password"
                required
                autoComplete="new-password"
                className={inputClass}
              />
            </label>
            <label className={labelClass}>
              Fallback Phone Number
              <input
                name="fallback_phone_number"
                type="tel"
                placeholder="+1 (555) 010-7000"
                className={inputClass}
              />
            </label>
            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                formAction={testSapConnectionAction}
                className="inline-flex min-h-10 items-center rounded-[6px] border border-swiss-ink px-5 font-sans text-[10px] font-medium uppercase tracking-[0.15em] text-swiss-ink transition-opacity hover:opacity-75"
              >
                Test Connection
              </button>
              <button
                type="submit"
                formAction={saveSapConnectionAction}
                className="inline-flex min-h-10 items-center rounded-[6px] bg-swiss-ink px-5 font-sans text-[10px] font-medium uppercase tracking-[0.15em] text-swiss-cream transition-opacity hover:opacity-75"
              >
                Save Configuration
              </button>
            </div>
          </form>
        </div>
      </section>

      <SideRail />
      <Footer />
    </article>
  );
}
