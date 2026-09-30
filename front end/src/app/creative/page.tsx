import Image from "next/image";
import Breadcrumb from "@/components/breadcrumb";
import Footer from "@/components/footer";
import SideRail from "@/components/side-rail";

export default function CreativePage() {
  return (
    <article className="stationery-sheet">
      <section className="canvas-left flex flex-col gap-10">
        <Breadcrumb />
        <div className="grid grid-cols-1 items-center gap-8 sm:grid-cols-12">
          <div className="space-y-6 sm:col-span-6">
            <h1 className="font-serif text-4xl font-light">Creative</h1>
            <p className="max-w-lg font-sans text-sm leading-6 text-swiss-slate">
              A considered collection of photography and fine art, presented as
              part of the Labish cultural record.
            </p>
          </div>
          <figure className="relative aspect-[4/5] overflow-hidden rounded-[6px] border border-swiss-slate/15 bg-swiss-ink/5 sm:col-span-6">
            <Image
              src="https://assets.philamuseum.org/images/r7hgx2l2/production/d34e93fc5ded628fdb118370889a227b0e1e3448-3200x1800.jpg?w=1600&fit=max&auto=format"
              alt="Abstract artwork from the Labish collection"
              fill
              priority
              sizes="(max-width: 640px) 100vw, 36vw"
              className="object-cover"
            />
          </figure>
        </div>
      </section>

      <SideRail />
      <Footer />
    </article>
  );
}