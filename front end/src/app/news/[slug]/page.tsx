import Image from "next/image";
import { notFound } from "next/navigation";
import Breadcrumb from "@/components/breadcrumb";
import Footer from "@/components/footer";
import SideRail from "@/components/side-rail";
import { newsArticles } from "@/data/news";

const latestArticles = [...newsArticles].sort(
  (first, second) => Date.parse(second.date) - Date.parse(first.date),
);

function formatDate(date: string) {
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${date}T00:00:00Z`));
}

export function generateStaticParams() {
  return latestArticles.map(({ slug }) => ({ slug }));
}

export default async function NewsArticlePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const articleIndex = latestArticles.findIndex((entry) => entry.slug === slug);
  const article = latestArticles[articleIndex];

  if (articleIndex === -1 || !article) notFound();

  return (
    <article className="stationery-sheet">
      <section className="canvas-left space-y-8">
        <Breadcrumb />
        <figure>
          <div className="relative aspect-[16/9] overflow-hidden rounded-[6px] border border-swiss-slate/15 bg-swiss-ink/5">
            <Image
              src={article.image}
              alt={article.imageAlt}
              fill
              priority
              sizes="(max-width: 1024px) 100vw, 58vw"
              className="object-cover"
            />
          </div>
          <figcaption className="mt-3 font-sans text-[9px] uppercase tracking-widest text-swiss-slate">
            {article.category} / {formatDate(article.date)}
          </figcaption>
        </figure>

        <div className="max-w-2xl space-y-7">
          {article.content.map((block, index) => {
            if (block.type === "heading") {
              return (
                <h2 key={`${block.type}-${index}`} className="font-serif text-2xl text-swiss-ink">
                  {block.text}
                </h2>
              );
            }

            if (block.type === "quote") {
              return (
                <blockquote
                  key={`${block.type}-${index}`}
                  className="border-l border-swiss-slate/30 py-2 pl-5 font-serif text-xl leading-relaxed text-swiss-ink"
                >
                  “{block.text}”
                  {block.attribution && (
                    <cite className="mt-3 block font-sans text-[9px] not-italic uppercase tracking-widest text-swiss-slate">
                      {block.attribution}
                    </cite>
                  )}
                </blockquote>
              );
            }

            if (block.type === "image") {
              return (
                <figure key={`${block.type}-${index}`}>
                  <div className="relative aspect-[16/9] overflow-hidden rounded-[6px] border border-swiss-slate/15 bg-swiss-ink/5">
                    <Image
                      src={block.src}
                      alt={block.alt}
                      fill
                      sizes="(max-width: 1024px) 100vw, 58vw"
                      className="object-cover"
                    />
                  </div>
                  {block.caption && (
                    <figcaption className="mt-3 font-sans text-[9px] uppercase tracking-widest text-swiss-slate">
                      {block.caption}
                    </figcaption>
                  )}
                </figure>
              );
            }

            return (
              <p
                key={`${block.type}-${index}`}
                className="font-sans text-sm leading-7 text-swiss-slate"
              >
                {block.text}
              </p>
            );
          })}
        </div>
      </section>

      <SideRail />

      <Footer />
    </article>
  );
}