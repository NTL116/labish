import Image from "next/image";
import Link from "next/link";
import Breadcrumb from "@/components/breadcrumb";
import Footer from "@/components/footer";
import SideRail from "@/components/side-rail";
import { people } from "@/data/people";

export default function PeoplePage() {
  return (
    <article className="stationery-sheet">
      <section className="canvas-left space-y-12">
        <Breadcrumb />
        <div className="grid w-full grid-cols-2 gap-5 sm:w-11/12 sm:gap-8">
          {people.map((person) => (
            <Link
              key={person.slug}
              href={`/people/${person.slug}`}
              className="group min-w-0 space-y-4"
            >
              <div className="relative aspect-[4/5] overflow-hidden rounded-[6px] border border-swiss-slate/15 bg-swiss-ink/5">
                <Image
                  src={person.image}
                  alt={person.imageAlt}
                  fill
                  sizes="(max-width: 640px) 42vw, (max-width: 1024px) 36vw, 24vw"
                  className="object-cover grayscale transition-opacity group-hover:opacity-80"
                />
              </div>
              <span className="block font-serif text-base leading-tight text-swiss-ink sm:text-lg">
                {person.name}
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