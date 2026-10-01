import Image from "next/image";
import Link from "next/link";
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

export default function NewsPage() {
  return (
    <article className="stationery-sheet">
      <section className="canvas-left space-y-10">
        <Breadcrumb />
        <header className="space-y-4 border-b border-swiss-slate/10 pb-8">
          <h1 className="font-serif text-4xl font-light">News &amp; Announcements</h1>
          <p className="max-w-xl font-sans text-sm leading-6 text-swiss-slate">
            Company news, portfolio notes, and perspectives from Labish.
          </p>
        </header>

        <ol className="divide-y divide-swiss-slate/10">
          {latestArticles.map((article) => (
            <li key={article.id} className="py-7 first:pt-0">
              <Link
                href={`/news/${article.slug}`}
                className="group grid grid-cols-1 gap-5 sm:grid-cols-[10rem_minmax(0,1fr)]"
              >
                <div className="relative aspect-[16/10] overflow-hidden rounded-[6px] border border-swiss-slate/15 bg-swiss-ink/5 sm:aspect-[4/3]">
                  <Image
                    src={article.image}
                    alt={article.imageAlt}
                    fill
                    sizes="(max-width: 640px) 100vw, 160px"
                    className="object-cover transition-opacity group-hover:opacity-85"
                  />
                </div>
                <div className="min-w-0 space-y-3">
                  <p className="font-sans text-[9px] uppercase tracking-[0.14em] text-swiss-slate">
                    {article.category} <span aria-hidden="true">/</span> {formatDate(article.date)}
                  </p>
                  <h2 className="font-serif text-xl leading-tight text-swiss-ink transition-colors group-hover:text-swiss-slate">
                    {article.title}
                  </h2>
                  <p className="font-sans text-xs leading-5 text-swiss-slate">
                    {article.summary}
                  </p>
                  <p className="font-sans text-[9px] uppercase tracking-[0.13em] text-swiss-slate">
                    By {article.author}
                  </p>
                </div>
              </Link>
            </li>
          ))}
        </ol>
      </section>

      <SideRail />

      <Footer />
    </article>
  );
}