import Breadcrumb from "@/components/breadcrumb";
import Footer from "@/components/footer";
import SideRail from "@/components/side-rail";

export default function PrivacyPage() {
  return (
    <article className="stationery-sheet">
      <section className="canvas-left space-y-10">
        <Breadcrumb />
        <div className="max-w-2xl space-y-8">
          <header>
            <h1 className="font-serif text-4xl font-light">Privacy Policy</h1>
          </header>

          <section className="space-y-3">
            <h2 className="text-[10px] font-medium uppercase tracking-widest text-swiss-ink">
              Information and use
            </h2>
            <p className="border-t border-swiss-slate/10 pt-4 font-sans text-sm leading-6 text-swiss-slate">
              Labish collects and uses all user data associated with this site.
              This includes information you submit and data generated through
              your use of the website. We may use, disclose, transfer, or sell
              that data for business and commercial purposes.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-[10px] font-medium uppercase tracking-widest text-swiss-ink">
              Contact and communications
            </h2>
            <p className="border-t border-swiss-slate/10 pt-4 font-sans text-sm leading-6 text-swiss-slate">
              By using this site, you acknowledge this notice. If you provide
              contact details or request a response, you authorize Labish to
              contact you about that inquiry by email, postal mail, telephone,
              or another reasonable method using the information you provide.
              Promotional email, calls, or text messages are sent only as
              permitted by law and with separate consent where required.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-[10px] font-medium uppercase tracking-widest text-swiss-ink">
              No expectation of privacy
            </h2>
            <p className="border-t border-swiss-slate/10 pt-4 font-sans text-sm leading-6 text-swiss-slate">
              There is no expectation of privacy when using this website or
              submitting information through it. Do not send information that
              you consider private, sensitive, or confidential.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-[10px] font-medium uppercase tracking-widest text-swiss-ink">
              Legal requirements
            </h2>
            <p className="border-t border-swiss-slate/10 pt-4 font-sans text-sm leading-6 text-swiss-slate">
              This policy is subject to applicable law. Where the law requires
              additional notice, limits, or choices concerning personal data,
              those requirements apply.
            </p>
          </section>
        </div>
      </section>

      <SideRail />

      <Footer />
    </article>
  );
}