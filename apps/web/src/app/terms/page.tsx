import Breadcrumb from "@/components/breadcrumb";
import Footer from "@/components/footer";
import SideRail from "@/components/side-rail";

export default function TermsPage() {
  return (
    <article className="stationery-sheet">
      <section className="canvas-left space-y-12">
        <Breadcrumb />
        <div className="max-w-2xl space-y-8">
          <header className="space-y-4">
            <h1 className="font-serif text-4xl font-light">Terms of Use</h1>
          </header>
          <section className="space-y-3">
            <h2 className="font-sans text-[10px] font-medium uppercase tracking-widest text-swiss-ink">
              Use of this site
            </h2>
            <p className="font-sans text-sm leading-6 text-swiss-slate">
              This website provides general information about Labish and its
              portfolio. By accessing it, you agree to use the site lawfully
              and not to interfere with its operation or security.
            </p>
          </section>
          <section className="space-y-3">
            <h2 className="font-sans text-[10px] font-medium uppercase tracking-widest text-swiss-ink">
              Contact and communications
            </h2>
            <p className="font-sans text-sm leading-6 text-swiss-slate">
              By using this site, you acknowledge the communications practices
              described in our Privacy Policy. If you submit contact details or
              request a response, Labish may contact you about that inquiry by
              email, postal mail, telephone, or another reasonable method using
              the information you provide. Marketing messages are subject to
              separate consent where required by law.
            </p>
          </section>
          <section className="space-y-3">
            <h2 className="font-sans text-[10px] font-medium uppercase tracking-widest text-swiss-ink">
              Information and intellectual property
            </h2>
            <p className="font-sans text-sm leading-6 text-swiss-slate">
              Site content is provided for informational purposes and may be
              updated without notice. Unless otherwise stated, the content and
              presentation are owned by Labish or its respective licensors and
              may not be reproduced for commercial use without permission.
            </p>
          </section>
          <section className="space-y-3">
            <h2 className="font-sans text-[10px] font-medium uppercase tracking-widest text-swiss-ink">
              No offer or advice
            </h2>
            <p className="font-sans text-sm leading-6 text-swiss-slate">
              Nothing on this website constitutes an offer, solicitation,
              investment recommendation, or professional advice. Decisions
              should not be made solely on the basis of website content.
            </p>
          </section>
        </div>
      </section>
      <SideRail />
      <Footer />
    </article>
  );
}