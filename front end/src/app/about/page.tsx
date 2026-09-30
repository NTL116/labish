import Image from "next/image";
import Breadcrumb from "@/components/breadcrumb";
import Footer from "@/components/footer";
import SideRail from "@/components/side-rail";

export default function AboutPage() {
  return (
    <article className="stationery-sheet">
      <section className="canvas-left flex flex-col gap-10">
        <Breadcrumb />
        <div className="grid grid-cols-1 items-center gap-10 sm:grid-cols-12">
          <div className="space-y-6 sm:col-span-7">
            <p className="font-sans text-[10px] uppercase tracking-[0.16em] text-swiss-slate">
              Labish / About
            </p>
            <h1 className="font-serif text-4xl font-light">About Labish</h1>
            <p className="max-w-xl font-sans text-sm leading-6 text-swiss-slate">
              Labish is an independent company focused on long-term ownership,
              thoughtful stewardship, and the development of enduring
              enterprises.
            </p>
          </div>
          <figure className="relative aspect-[4/5] overflow-hidden rounded-[6px] border border-swiss-slate/15 bg-swiss-ink/5 sm:col-span-5">
            <Image
              src="https://images.unsplash.com/photo-1487958449943-2429e8be8625?auto=format&fit=crop&w=1200&q=85"
              alt="Contemporary architecture in soft daylight"
              fill
              priority
              sizes="(max-width: 640px) 100vw, 30vw"
              className="object-cover grayscale"
            />
          </figure>
        </div>
      </section>

      <SideRail />

      <Footer />
    </article>
  );
}