import Image from "next/image";
import { notFound } from "next/navigation";
import Breadcrumb from "@/components/breadcrumb";
import Footer from "@/components/footer";
import SideRail from "@/components/side-rail";
import { companies } from "@/data/companies";

export default async function CompanyPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const company = companies.find((entry) => entry.slug === slug);

  if (!company) notFound();

  return (
    <article className="stationery-sheet">
      <section className="canvas-left flex flex-col gap-8">
        <Breadcrumb />
        <div className="space-y-6">
          <h1 className="font-serif text-4xl font-light capitalize">
            {company.name}
          </h1>
        </div>

        <div className="relative mt-12 aspect-[16/10] w-full overflow-hidden rounded-[6px] border border-swiss-slate/15 bg-swiss-ink/5">
          <Image
            src={company.image}
            alt={company.imageAlt}
            fill
            priority
            sizes="(max-width: 1024px) 100vw, 58vw"
            className="object-cover grayscale contrast-[1.02]"
          />
        </div>
      </section>

      <SideRail />

      <Footer />
    </article>
  );
}