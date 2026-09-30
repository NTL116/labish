import Image from "next/image";
import Breadcrumb from "@/components/breadcrumb";
import Footer from "@/components/footer";
import SideRail from "@/components/side-rail";

const levers = [
  {
    title: "Ethical Governance & Leadership",
    description:
      "Clear accountability and principled leadership inform durable decisions.",
  },
  {
    title: "Empowering Our People",
    description:
      "Respectful workplaces support the contribution and development of every person.",
  },
  {
    title: "Sustainable Operations",
    description:
      "Operational choices should use resources thoughtfully and reduce avoidable impact.",
  },
  {
    title: "A Responsible Supply Chain",
    description:
      "Long-term relationships are built on transparency, fairness, and shared standards.",
  },
  {
    title: "Innovation for Good",
    description:
      "Innovation can address meaningful needs while strengthening the communities it serves.",
  },
  {
    title: "Meaningful Community Investment",
    description:
      "Local understanding helps direct support toward lasting community priorities.",
  },
  {
    title: "Strategic Partnerships for Impact",
    description:
      "Partnerships bring complementary experience to complex, long-term challenges.",
  },
  {
    title: "Customer Empowerment & Transparency",
    description:
      "Useful information and clear communication help people make informed choices.",
  },
  {
    title: "Data-Driven Accountability",
    description:
      "Consistent measurement makes progress visible and helps guide improvement.",
  },
  {
    title: "Championing the Conversation",
    description:
      "Open dialogue helps responsible practices evolve across industries and communities.",
  },
];

export default function ResponsibleVisionPage() {
  return (
    <article className="stationery-sheet">
      <section className="canvas-left space-y-16">
        <Breadcrumb />

        <header className="space-y-8">
          <h1 className="font-serif text-4xl font-light">Responsible Vision</h1>
          <div className="grid grid-cols-1 items-start gap-8 sm:grid-cols-12">
            <div className="space-y-5 font-sans text-sm leading-6 text-swiss-slate sm:col-span-7">
              <p>
                The world is at a pivotal moment. The challenges we face—from
                social inequality to environmental degradation and economic
                volatility—demand a swift and decisive transition to a more
                sustainable and resilient global economy.
              </p>
              <p>
                At Labish, we believe this new era calls for a fundamental
                shift in focus. It requires moving beyond the extractive pursuit
                of short-term financial returns to embrace a broader, more
                durable definition of value. For us, success is measured by our
                positive impact on our people, our communities, the planet, and
                the long-term health of our business. This is our commitment to
                building a better future, together.
              </p>
            </div>
            <figure className="relative aspect-[4/5] overflow-hidden rounded-[6px] border border-swiss-slate/15 bg-swiss-ink/5 sm:col-span-5">
              <Image
                src="https://images.unsplash.com/photo-1470770841072-f978cf4d019e?auto=format&fit=crop&w=1000&q=85"
                alt="A forested mountain landscape reflected in clear water"
                fill
                priority
                sizes="(max-width: 640px) 100vw, 30vw"
                className="object-cover"
              />
            </figure>
          </div>
        </header>

        <section className="grid grid-cols-1 gap-6 border-t border-swiss-slate/10 pt-8 sm:grid-cols-12 sm:gap-8">
          <h2 className="text-xl font-normal normal-case tracking-normal text-swiss-ink sm:col-span-4">
            Ambitions
          </h2>
          <div className="space-y-5 font-sans text-sm leading-6 text-swiss-slate sm:col-span-8">
            <p>
              To meet this commitment, we must champion new models of operation
              and innovation. These models will be grounded in robust
              principles, guided by transparency, and built on innovative
              partnerships. Our aim is to embed sustainability and
              responsibility into our organization—from the products we create
              to the way we operate.
            </p>
            <p>
              It also means fostering a culture that prioritizes long-term
              resilience over short-term gains and actively directing our
              resources, talent, and influence toward creating a thriving system
              for future generations.
            </p>
          </div>
        </section>

        <figure className="relative aspect-[16/8] overflow-hidden rounded-[6px] border border-swiss-slate/15 bg-swiss-ink/5">
          <Image
            src="https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1800&q=85"
            alt="Aerial view across a forest and open landscape"
            fill
            sizes="(max-width: 1024px) 100vw, 58vw"
            className="object-cover"
          />
        </figure>

        <section className="space-y-8">
          <header className="grid grid-cols-1 gap-4 border-b border-swiss-slate/10 pb-5 sm:grid-cols-12 sm:items-end">
            <div className="sm:col-span-5">
              <p className="font-sans text-[10px] uppercase tracking-[0.16em] text-swiss-slate">
                Action framework
              </p>
              <h2 className="mt-3 text-2xl font-normal normal-case tracking-normal text-swiss-ink">
                10 levers of action
              </h2>
            </div>
            <p className="font-sans text-xs leading-5 text-swiss-slate sm:col-span-7">
              These principles describe the areas through which responsible
              intent can take practical form.
            </p>
          </header>
          <ol className="grid grid-cols-1 gap-x-7 sm:grid-cols-2">
            {levers.map((lever, index) => (
              <li
                key={lever.title}
                className="border-b border-swiss-slate/10 py-5"
              >
                <p className="font-serif text-base font-medium leading-snug text-swiss-ink">
                  {String(index + 1).padStart(2, "0")} / {lever.title}
                </p>
                <p className="mt-3 font-sans text-xs leading-5 text-swiss-slate">
                  {lever.description}
                </p>
              </li>
            ))}
          </ol>
        </section>

        <blockquote className="border-l border-swiss-slate/30 py-2 pl-6 font-serif text-xl italic leading-relaxed text-swiss-ink">
          “These 10 levers of action align us with our core purpose: to build an
          enduring and responsible business. We achieve this by creating shared
          value through meaningful partnerships with our employees, customers,
          suppliers, and the communities we serve.”
          <cite className="mt-4 block font-sans text-[9px] not-italic uppercase tracking-widest text-swiss-slate">
            Nathan Labish / Founder, Labish Corp.
          </cite>
        </blockquote>
      </section>

      <SideRail />

      <Footer />
    </article>
  );
}