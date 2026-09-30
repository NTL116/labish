import Image from "next/image";
import Link from "next/link";
import Breadcrumb from "@/components/breadcrumb";
import Footer from "@/components/footer";
import SideRail from "@/components/side-rail";

export default function PortalPage() {
  return (
    <article className="stationery-sheet">
      <section className="canvas-left flex flex-col gap-10">
        <Breadcrumb />
        <div className="grid grid-cols-1 items-center gap-8 sm:grid-cols-12">
          <div className="space-y-6 sm:col-span-7">
            <h1 className="font-serif text-4xl font-light">Portal Access</h1>
            <p className="max-w-lg font-sans text-sm leading-6 text-swiss-slate">
            The Labish portal is reserved for authorized individuals.
            For access information, please contact our office.
            </p>
            <div className="flex flex-wrap gap-x-6 gap-y-3">
              <Link
                href="/contact"
                className="font-sans text-[10px] font-normal uppercase tracking-[0.13em] text-swiss-slate transition-colors hover:text-swiss-ink"
              >
                Contact
              </Link>
              <Link
                href="/login"
                className="font-sans text-[10px] font-normal uppercase tracking-[0.13em] text-swiss-slate transition-colors hover:text-swiss-ink"
              >
                Login
              </Link>
            </div>
          </div>
          <figure className="relative aspect-[4/5] overflow-hidden rounded-[6px] border border-swiss-slate/15 bg-swiss-ink/5 sm:col-span-5">
            <Image
              src="https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1200&q=85"
              alt="Modern office architecture rising toward the sky"
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