import { notFound } from "next/navigation";
import { getPayload } from "payload";

import config from "@payload-config";
import type { Page } from "@/payload-types";

export const dynamic = "force-dynamic";

type PortalPageProps = {
  params: Promise<{ slug: string[] }>;
};

async function queryPageBySlug(slug: string): Promise<Page | null> {
  const payload = await getPayload({ config });
  const result = await payload.find({
    collection: "pages",
    where: {
      slug: {
        equals: slug,
      },
    },
    limit: 1,
    pagination: false,
  });
  return result.docs[0] ?? null;
}

/**
 * Dynamic catch-all wrapper for CMS-driven portal pages. It resolves the
 * Payload `pages` document matching the URL slug and passes the raw,
 * unstyled block payload straight through. No design decisions are made
 * here — the design team owns 100% of the visual layer.
 */
export default async function PortalCmsPage({ params }: PortalPageProps) {
  const { slug } = await params;
  const page = await queryPageBySlug(slug.join("/"));

  if (!page) {
    notFound();
  }

  return (
    <article data-page-id={page.id} data-page-slug={page.slug}>
      <h1>{page.title}</h1>
      {(page.blocks ?? []).map((block) => {
        switch (block.blockType) {
          case "metricsBlock":
            return (
              <section
                key={block.id}
                data-block-id={block.id}
                data-block-type={block.blockType}
                data-sap-field={block.sapField}
              >
                <span>{block.label}</span>
                <output>{block.sapField}</output>
              </section>
            );
          case "dataBlock":
            return (
              <section
                key={block.id}
                data-block-id={block.id}
                data-block-type={block.blockType}
              >
                <ul>
                  {(block.sapFields ?? []).map((row) => (
                    <li key={row.id} data-sap-field={row.sapField}>
                      {row.sapField}
                    </li>
                  ))}
                </ul>
              </section>
            );
          default:
            return null;
        }
      })}
    </article>
  );
}
