import Image from "next/image";
import Breadcrumb from "@/components/breadcrumb";
import Footer from "@/components/footer";
import SideRail from "@/components/side-rail";

export default function ResponsibilityPage() {
  return (
    <article className="stationery-sheet">
      <section className="canvas-left flex flex-col gap-10">
        <Breadcrumb />
        <div className="grid grid-cols-1 items-center gap-8 sm:grid-cols-12">
          <div className="space-y-6 sm:col-span-7">
            <p className="font-sans text-[10px] uppercase tracking-[0.16em] text-swiss-slate">
              Labish / Responsibility
            </p>
            <h1 className="font-serif text-4xl font-light">Responsibility</h1>
            <p className="max-w-lg font-sans text-sm leading-6 text-swiss-slate">
              Our approach to responsibility begins with thoughtful
              stewardship, sustainable operations, and long-term resilience.
            </p>
          </div>
          <figure className="relative aspect-[4/5] overflow-hidden rounded-[6px] border border-swiss-slate/15 bg-swiss-ink/5 sm:col-span-5">
            <Image
              src="https://images.unsplash.com/photo-1470770841072-f978cf4d019e?auto=format&fit=crop&w=1200&q=85"
              alt="Mountain landscape reflected in still water"
              fill
              priority
              sizes="(max-width: 640px) 100vw, 30vw"
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