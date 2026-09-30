import Image from "next/image";
import Link from "next/link";
import Breadcrumb from "@/components/breadcrumb";
import Footer from "@/components/footer";
import SideRail from "@/components/side-rail";

export interface CreativeGalleryItem {
  slug: string;
  title: string;
  creator: string;
  image: string;
  alt: string;
}

export default function CreativeGallery({
  title,
  collection,
  items,
}: {
  title: string;
  collection: "photography" | "art";
  items: CreativeGalleryItem[];
}) {
  return (
    <article className="stationery-sheet">
      <section className="canvas-left space-y-10">
        <Breadcrumb />
        <header className="space-y-4 border-b border-swiss-slate/10 pb-6">
          <h1 className="font-serif text-4xl font-light">{title}</h1>
        </header>
        <div className="grid grid-cols-1 gap-x-8 gap-y-10 sm:grid-cols-2">
          {items.map((item) => (
            <Link
              key={item.slug}
              href={`/creative/${collection}/${item.slug}`}
              className="group min-w-0"
            >
              <div className="relative aspect-[4/5] overflow-hidden rounded-[6px] border border-swiss-slate/15 bg-swiss-ink/5">
                <Image
                  src={item.image}
                  alt={item.alt}
                  fill
                  sizes="(max-width: 640px) 100vw, 28vw"
                  className="object-cover transition-opacity group-hover:opacity-85"
                />
              </div>
              <span className="mt-4 block font-serif text-lg leading-tight text-swiss-ink">
                {item.title}
              </span>
              <span className="mt-2 block font-sans text-[9px] uppercase tracking-[0.14em] text-swiss-slate">
                {item.creator}
              </span>
            </Link>
          ))}
        </div>
      </section>

      <SideRail />
      <Footer />
    </article>
  );
}