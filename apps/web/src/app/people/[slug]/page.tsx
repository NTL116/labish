import Image from "next/image";
import { notFound } from "next/navigation";
import Breadcrumb from "@/components/breadcrumb";
import Footer from "@/components/footer";
import SideRail from "@/components/side-rail";
import { people } from "@/data/people";

export function generateStaticParams() {
  return people.map(({ slug }) => ({ slug }));
}

export default async function PersonPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const person = people.find((entry) => entry.slug === slug);

  if (!person) notFound();

  return (
    <article className="stationery-sheet">
      <section className="canvas-left flex flex-col gap-8">
        <Breadcrumb />
        <h1 className="font-serif text-4xl font-light">{person.name}</h1>
        <figure className="w-full">
          <div className="relative aspect-[4/5] max-h-[34rem] overflow-hidden rounded-[6px] border border-swiss-slate/15 bg-swiss-ink/5 sm:aspect-[16/10]">
            <Image
              src={person.image}
              alt={person.imageAlt}
              fill
              priority
              sizes="(max-width: 1024px) 100vw, 58vw"
              className="object-cover grayscale"
            />
          </div>
          <blockquote className="mt-8 max-w-2xl font-serif text-xl leading-relaxed text-swiss-ink">
            “{person.quote}”
          </blockquote>
          {"quoteAttribution" in person && person.quoteAttribution && (
            <figcaption className="mt-3 font-sans text-[9px] uppercase tracking-widest text-swiss-slate">
              {person.quoteAttribution}
            </figcaption>
          )}
        </figure>
      </section>

      <SideRail />

      <Footer />
    </article>
  );
}