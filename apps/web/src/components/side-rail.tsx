"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { artworks } from "@/data/artworks";
import { companies } from "@/data/companies";
import { newsArticles } from "@/data/news";
import { people, personalAddress } from "@/data/people";
import { photographs } from "@/data/photographs";

interface MenuLink {
  label: string;
  href: string;
}

const homeSections: { label: string; href: string; links: MenuLink[] }[] = [
  {
    label: "Companies",
    href: "/companies",
    links: [
      { label: "Slate Micro", href: "/companies/slate-micro" },
      { label: "Blue Hat Cleaning", href: "/companies/blue-hat-cleaning" },
      { label: "May Birch", href: "/companies/may-birch" },
    ],
  },
  {
    label: "About",
    href: "/about",
    links: [
      { label: "People", href: "/people" },
      { label: "Contact", href: "/contact" },
    ],
  },
  {
    label: "Creative",
    href: "/creative",
    links: [
      { label: "Photography", href: "/creative/photography" },
      { label: "Fine Art", href: "/creative/art" },
    ],
  },
  {
    label: "Newsroom",
    href: "/news",
    links: [{ label: "News & Announcements", href: "/news" }],
  },
  {
    label: "Responsibility",
    href: "/responsibility",
    links: [
      {
        label: "Responsible Vision",
        href: "/responsibility/responsible-vision",
      },
    ],
  },
];

const railClass =
  "canvas-right-axis font-sans text-[10px] font-medium uppercase tracking-[0.13em] text-swiss-slate";
const headingClass =
  "mb-3 block text-[9px] font-semibold tracking-widest text-swiss-ink transition-colors hover:text-swiss-slate";
const itemClass =
  "block font-normal transition-colors hover:text-swiss-ink";

function formatDate(date: string) {
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${date}T00:00:00Z`));
}

function CompanyDetailRail({ slug }: { slug: string }) {
  const company = companies.find((entry) => entry.slug === slug);
  if (!company) return null;

  return (
    <aside className="canvas-right-axis space-y-4 font-sans text-[11px] leading-relaxed text-swiss-slate">
      <p className="mb-3 text-[10px] font-medium uppercase tracking-widest text-swiss-ink">
        Specifications
      </p>
      <div className="border-t border-swiss-slate/10 pt-3">
        <p className="text-[9px] uppercase tracking-widest">Registry</p>
        <p className="mt-1 text-swiss-ink">Labish portfolio</p>
      </div>
      <div className="border-t border-swiss-slate/10 pt-3">
        <p className="text-[9px] uppercase tracking-widest">Classification</p>
        <p className="mt-1 text-swiss-ink">Operating company</p>
      </div>
      <div className="border-t border-swiss-slate/10 pt-3">
        <p className="text-[9px] uppercase tracking-widest">Website</p>
        <a
          className="mt-1 block break-all text-swiss-ink transition-colors hover:text-swiss-slate"
          href={company.website}
          target="_blank"
          rel="noreferrer"
        >
          {company.website.replace("https://", "")}
        </a>
      </div>
    </aside>
  );
}

function ArtworkRail({
  kind,
  slug,
}: {
  kind: "photography" | "art";
  slug: string;
}) {
  const items = kind === "photography" ? photographs : artworks;
  const currentIndex = items.findIndex((item) => item.slug === slug);
  const item = items[currentIndex];
  if (!item) return null;

  const previous = items[currentIndex - 1];
  const next = items[currentIndex + 1];
  const basePath = `/creative/${kind}`;
  const noun = kind === "photography" ? "photograph" : "artwork";

  return (
    <aside className="canvas-right-axis flex flex-col justify-end gap-6 font-sans text-[10px] uppercase tracking-[0.13em] text-swiss-slate">
      <nav
        aria-label={`${kind} navigation`}
        className="flex min-h-10 items-center justify-between border-b border-swiss-slate/10 pb-3"
      >
        {previous ? (
          <Link
            href={`${basePath}/${previous.slug}`}
            aria-label={`Previous ${noun}: ${previous.title}`}
            title={`Previous: ${previous.title}`}
            className="text-xl leading-none transition-colors hover:text-swiss-ink"
          >
            ←
          </Link>
        ) : null}
        {next ? (
          <Link
            href={`${basePath}/${next.slug}`}
            aria-label={`Next ${noun}: ${next.title}`}
            title={`Next: ${next.title}`}
            className={`text-xl leading-none transition-colors hover:text-swiss-ink ${previous ? "" : "ml-auto"}`}
          >
            →
          </Link>
        ) : null}
      </nav>
      <h1 className="font-serif text-2xl font-normal normal-case tracking-normal text-swiss-ink">
          <Link className={headingClass} href="/portal">Portal</Link>
      </h1>
      <div className="space-y-4">
        <div className="border-t border-swiss-slate/10 pt-3">
          <p className="text-[9px] tracking-widest">Reference</p>
          <p className="mt-1 text-swiss-ink">{item.reference}</p>
        </div>
        <div className="border-t border-swiss-slate/10 pt-3">
          <p className="text-[9px] tracking-widest">Artist</p>
          <p className="mt-1 text-swiss-ink">{item.artist}</p>
        </div>
      </div>
    </aside>
  );
}

function NewsArticleRail({ slug }: { slug: string }) {
  const articles = [...newsArticles].sort(
    (first, second) => Date.parse(second.date) - Date.parse(first.date),
  );
  const currentIndex = articles.findIndex((article) => article.slug === slug);
  const article = articles[currentIndex];
  if (!article) return null;

  const newer = articles[currentIndex - 1];
  const older = articles[currentIndex + 1];
  const canonicalUrl = `${process.env.NEXT_PUBLIC_SITE_URL ?? "https://labish.com"}/news/${article.slug}`;
  const encodedUrl = encodeURIComponent(canonicalUrl);
  const encodedTitle = encodeURIComponent(article.title);

  return (
    <aside className="canvas-right-axis flex flex-col justify-between gap-8 font-sans text-[10px] uppercase tracking-[0.13em] text-swiss-slate">
      <div>
        <nav
          aria-label="Article navigation"
          className="mb-8 flex min-h-10 items-center justify-between border-b border-swiss-slate/10 pb-3"
        >
          {newer ? <Link href={`/news/${newer.slug}`} aria-label={`Newer article: ${newer.title}`} title={`Newer: ${newer.title}`} className="text-xl leading-none transition-colors hover:text-swiss-ink">←</Link> : null}
          {older ? <Link href={`/news/${older.slug}`} aria-label={`Older article: ${older.title}`} title={`Older: ${older.title}`} className={`text-xl leading-none transition-colors hover:text-swiss-ink ${newer ? "" : "ml-auto"}`}>→</Link> : null}
        </nav>
        <h1 className="font-serif text-2xl font-normal normal-case leading-tight tracking-normal text-swiss-ink">
          {article.title}
        </h1>
        <div className="mt-6 space-y-4">
          <div className="border-t border-swiss-slate/10 pt-3">
            <p className="text-[9px] tracking-widest">Author</p>
            <p className="mt-1 text-swiss-ink">{article.author}</p>
          </div>
          <div className="border-t border-swiss-slate/10 pt-3">
            <p className="text-[9px] tracking-widest">Published</p>
            <time className="mt-1 block text-swiss-ink" dateTime={article.date}>
              {formatDate(article.date)}
            </time>
          </div>
        </div>
      </div>
      <div>
        <p className="mb-3 text-[9px] tracking-widest text-swiss-ink">Share</p>
        <ul className="space-y-3 border-t border-swiss-slate/10 pt-4">
          <li><a href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodedUrl}`} target="_blank" rel="noreferrer" className="transition-colors hover:text-swiss-ink">LinkedIn</a></li>
          <li><a href={`https://twitter.com/intent/tweet?url=${encodedUrl}&text=${encodedTitle}`} target="_blank" rel="noreferrer" className="transition-colors hover:text-swiss-ink">X</a></li>
          <li><a href={`mailto:?subject=${encodedTitle}&body=${encodedUrl}`} className="transition-colors hover:text-swiss-ink">Email</a></li>
        </ul>
      </div>
    </aside>
  );
}

function NewsIndexRail() {
  const articles = [...newsArticles].sort(
    (first, second) => Date.parse(second.date) - Date.parse(first.date),
  );

  return (
    <aside className="canvas-right-axis font-sans text-[10px] uppercase tracking-[0.13em] text-swiss-slate">
      <p className="mb-4 text-[10px] font-medium tracking-widest text-swiss-ink">
        Latest Posts
      </p>
      <ol className="divide-y divide-swiss-slate/10 border-t border-swiss-slate/10">
        {articles.map((article) => (
          <li key={article.id}>
            <Link href={`/news/${article.slug}`} className="block py-4 transition-colors hover:text-swiss-ink">
              {article.title}
            </Link>
          </li>
        ))}
      </ol>
    </aside>
  );
}

function PersonDetailRail({ slug }: { slug: string }) {
  const person = people.find((entry) => entry.slug === slug);
  if (!person) return null;

  return (
    <aside className="canvas-right-axis flex flex-col gap-8 font-sans text-[11px] leading-relaxed text-swiss-slate">
      <section>
        <h2 className="mb-3 text-[10px] font-medium uppercase tracking-widest text-swiss-ink">Biography</h2>
        <p className="border-t border-swiss-slate/10 pt-4">{person.bio}</p>
      </section>
      <section>
        <h2 className="mb-3 text-[10px] font-medium uppercase tracking-widest text-swiss-ink">Contact</h2>
        <address className="space-y-1 border-t border-swiss-slate/10 pt-4 not-italic">
          {personalAddress.map((line) => <p key={line}>{line}</p>)}
        </address>
        <div className="mt-4 space-y-2">
          <p><a href={`tel:${person.phone.replace(/[^+\d]/g, "")}`}>{person.phone}</a></p>
          <p><a href={`mailto:${person.email}`}>{person.email}</a></p>
        </div>
      </section>
      <section>
        <h2 className="mb-3 text-[10px] font-medium uppercase tracking-widest text-swiss-ink">Social</h2>
        <ul className="space-y-2 border-t border-swiss-slate/10 pt-4">
          {person.socialLinks.map((social) => <li key={social.href}><Link href={social.href} target="_blank" rel="noreferrer">{social.label}</Link></li>)}
        </ul>
      </section>
      {person.education.length > 0 && (
        <section>
          <h2 className="mb-3 text-[10px] font-medium uppercase tracking-widest text-swiss-ink">Education &amp; Credentials</h2>
          <ul className="space-y-2 border-t border-swiss-slate/10 pt-4">
            {person.education.map((credential) => <li key={credential}>{credential}</li>)}
          </ul>
        </section>
      )}
    </aside>
  );
}

function HomeRail() {
  return (
    <aside className={`${railClass} flex flex-col justify-between`}>
      <div className="space-y-9">
        {homeSections.map((section, index) => (
          <div className={index === 0 ? "" : "pt-3"} key={section.label}>
            <Link className={headingClass} href={section.href}>{section.label}</Link>
            <ul className="space-y-3 border-t border-swiss-slate/10 pt-3">
              {section.links.map((item) => <li key={item.href}><Link className={itemClass} href={item.href}>{item.label}</Link></li>)}
            </ul>
          </div>
        ))}
        <div className="pt-3">
          <Link className={headingClass} href="/portal">Portal</Link>
          <ul className="space-y-3 border-t border-swiss-slate/10 pt-3">
            <li><Link className={itemClass} href="/login">Login</Link></li>
          </ul>
        </div>
      </div>
    </aside>
  );
}

function ResponsibilityRail({ isDetail }: { isDetail: boolean }) {
  return (
    <aside className={railClass}>
      <Link className={headingClass} href="/responsibility">Responsibility</Link>
      <ul className="space-y-3 border-t border-swiss-slate/10 pt-3">
        <li>
          {isDetail ? (
            <span className="block font-normal text-swiss-ink">Responsible Vision</span>
          ) : (
            <Link className={itemClass} href="/responsibility/responsible-vision">Responsible Vision</Link>
          )}
        </li>
      </ul>
    </aside>
  );
}

export default function SideRail() {
  const pathname = usePathname() || "/";
  const segments = pathname.split("/").filter(Boolean);

  if (segments.length === 0) return <HomeRail />;

  if (segments[0] === "companies") {
    if (segments.length === 1) {
      return (
        <aside className={railClass}>
          <Link className={headingClass} href="/companies">Companies</Link>
          <ul className="space-y-3 border-t border-swiss-slate/10 pt-3">
            {companies.map((company) => <li key={company.slug}><Link className={itemClass} href={`/companies/${company.slug}`}>{company.name}</Link></li>)}
          </ul>
        </aside>
      );
    }
    return <CompanyDetailRail slug={segments[1]} />;
  }

  if (segments[0] === "about" || segments[0] === "people" || segments[0] === "contact") {
    if (segments[0] === "people" && segments.length > 1) {
      return <PersonDetailRail slug={segments[1]} />;
    }
    return (
      <aside className={railClass}>
        <Link className={headingClass} href="/about">About</Link>
        <ul className="space-y-3 border-t border-swiss-slate/10 pt-3">
          <li><Link className={itemClass} href="/people">People</Link></li>
          <li><Link className={itemClass} href="/contact">Contact</Link></li>
        </ul>
      </aside>
    );
  }

  if (segments[0] === "creative") {
    if (segments.length === 3 && segments[1] === "photography") {
      return <ArtworkRail kind="photography" slug={segments[2]} />;
    }
    if (segments.length === 3 && segments[1] === "art") {
      return <ArtworkRail kind="art" slug={segments[2]} />;
    }

    return (
      <aside className={railClass}>
        <Link className={headingClass} href="/creative">Creative</Link>
        <ul className="space-y-3 border-t border-swiss-slate/10 pt-3">
          <li><Link className={itemClass} href="/creative/photography">Photography</Link></li>
          <li><Link className={itemClass} href="/creative/art">Fine Art</Link></li>
        </ul>
      </aside>
    );
  }

  if (segments[0] === "news") {
    if (segments.length > 1) return <NewsArticleRail slug={segments[1]} />;
    return <NewsIndexRail />;
  }

  if (segments[0] === "responsibility") {
    return <ResponsibilityRail isDetail={segments.length > 1} />;
  }
  if (segments[0] === "portal" || segments[0] === "login") {
    return (
      <aside className={railClass}>
        <Link className={headingClass} href="/portal">Portal</Link>
        <ul className="space-y-3 border-t border-swiss-slate/10 pt-3">
          <li>
            {segments[0] === "login" ? (
              <span className="block font-normal text-swiss-ink">Login</span>
            ) : (
              <Link className={itemClass} href="/login">Login</Link>
            )}
          </li>
        </ul>
      </aside>
    );
  }
  if (segments[0] === "privacy" || segments[0] === "terms") {
    return <HomeRail />;
  }

  return <aside className="canvas-right-axis" aria-hidden="true" />;
}