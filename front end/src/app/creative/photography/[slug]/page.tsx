import Image from "next/image";
import { notFound } from "next/navigation";
import Breadcrumb from "@/components/breadcrumb";
import Footer from "@/components/footer";
import SideRail from "@/components/side-rail";
import { photographs } from "@/data/photographs";

export function generateStaticParams() {
  return photographs.map(({ slug }) => ({ slug }));
}

export default async function PhotographPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const photographIndex = photographs.findIndex((item) => item.slug === slug);
  const photograph = photographs[photographIndex];

  if (photographIndex === -1 || !photograph) notFound();

  return (
    <article className="stationery-sheet">
      <section className="canvas-left flex flex-col gap-8">
        <Breadcrumb />
        <figure className="mt-4 w-full">
          <div className="relative aspect-[16/10] overflow-hidden rounded-[6px] border border-swiss-slate/15 bg-swiss-ink/5">
            <Image
              src={photograph.image}
              alt={photograph.alt}
              fill
              priority
              sizes="(max-width: 1024px) 100vw, 58vw"
              className="object-cover"
            />
          </div>
        </figure>
      </section>

      <SideRail />

      <Footer />
    </article>
  );
}