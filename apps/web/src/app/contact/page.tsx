import Breadcrumb from "@/components/breadcrumb";
import Footer from "@/components/footer";
import { officeAddress } from "@/data/people";
import SideRail from "@/components/side-rail";

export default function ContactPage() {
  return (
    <article className="stationery-sheet">
      <section className="canvas-left flex flex-col gap-10">
        <Breadcrumb />
        <div className="max-w-2xl space-y-6">
          <h1 className="font-serif text-4xl font-light">Contact</h1>
          <div className="max-w-sm pt-4">
            <p className="mb-3 font-sans text-[10px] font-medium uppercase tracking-widest text-swiss-ink">
              Correspondence
            </p>
            <address className="space-y-1 border-t border-swiss-slate/10 pt-4 font-sans text-sm not-italic leading-relaxed text-swiss-slate">
              {officeAddress.map((line) => <p key={line}>{line}</p>)}
            </address>
          </div>
        </div>
      </section>

      <SideRail />

      <Footer />
    </article>
  );
}