"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const segmentLabels: Record<string, string> = {
  about: "About",
  companies: "Companies",
  contact: "Contact",
  creative: "Creative",
  art: "Fine Art",
  news: "News",
  people: "People",
  photography: "Photography",
  privacy: "Privacy Policy",
  responsibility: "Responsibility",
  "responsible-vision": "Responsible Vision",
  terms: "Terms of Use",
};

function formatSegment(segment: string) {
  return (
    segmentLabels[segment] ??
    segment
      .split(/[-_]/)
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ")
  );
}

export default function Breadcrumb() {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);
  const items = [
    { label: "Labish", href: segments.length > 0 ? "/" : undefined },
    ...segments.map((segment, index) => ({
      label: formatSegment(segment),
      href:
        index < segments.length - 1
          ? `/${segments.slice(0, index + 1).join("/")}`
          : undefined,
    })),
  ];

  return (
    <nav aria-label="Breadcrumb">
      <ol className="flex flex-wrap items-center gap-x-2 gap-y-1 font-sans text-[9px] uppercase tracking-[0.14em] text-swiss-slate">
        {items.map((item, index) => {
          const isCurrent = index === items.length - 1;

          return (
            <li key={`${item.label}-${index}`} className="flex items-center gap-2">
              {index > 0 && <span aria-hidden="true">/</span>}
              {item.href ? (
                <Link
                  href={item.href}
                  aria-current={isCurrent ? "page" : undefined}
                  className="text-swiss-slate transition-colors hover:text-swiss-ink"
                >
                  {item.label}
                </Link>
              ) : (
                <span
                  aria-current={isCurrent ? "page" : undefined}
                  className={isCurrent ? "text-swiss-ink" : "text-swiss-slate"}
                >
                  {item.label}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}