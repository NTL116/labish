import Image from "next/image";
import Breadcrumb from "@/components/breadcrumb";
import Footer from "@/components/footer";
import SideRail from "@/components/side-rail";

export default function CompaniesPage() {
  return (
    <article className="stationery-sheet">
      <section className="canvas-left flex flex-col justify-between gap-10">
        <Breadcrumb />

        <div className="space-y-8">
          <figure className="relative aspect-[16/9] w-full overflow-hidden rounded-[6px] border border-swiss-slate/15 bg-swiss-ink/5">
            <Image
              src="https://images.unsplash.com/photo-1487958449943-2429e8be8625?auto=format&fit=crop&w=1800&q=90"
              alt="Contemporary architecture in soft daylight"
              fill
              priority
              sizes="(max-width: 1024px) 100vw, 58vw"
              className="object-cover grayscale"
            />
          </figure>
          <p className="max-w-2xl font-serif text-xl leading-relaxed text-swiss-ink">
            Our portfolio comprises companies that demonstrate strong
            fundamentals and growth potential. Please contact us if you believe
            you have an investment opportunity that align with our thesis.
          </p>
        </div>
      </section>

      <SideRail />

      <Footer />
    </article>
  );
}