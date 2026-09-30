import Image from "next/image";
import Breadcrumb from "@/components/breadcrumb";
import Footer from "@/components/footer";
import SideRail from "@/components/side-rail";

export default function HomePage() {
  return (
    <article className="stationery-sheet">
      <section className="canvas-left flex flex-col justify-between">
        <div className="space-y-10">
          <Breadcrumb />
          <h1 className="max-w-xl font-serif text-3xl font-light leading-relaxed text-swiss-ink">
            We are a family and independent organization known for our long-term mindset, responsible approach to business and entrepreneurial spirit.
          </h1>
          <figure className="relative aspect-[16/9] w-full overflow-hidden rounded-[6px] border border-swiss-slate/15 bg-swiss-ink/5">
            <Image
              src="https://assets.philamuseum.org/images/r7hgx2l2/production/d34e93fc5ded628fdb118370889a227b0e1e3448-3200x1800.jpg?w=3072&fit=max&auto=format"
              alt="Abstract painting from the Labish visual registry"
              fill
              priority
              sizes="(max-width: 1024px) 100vw, 58vw"
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