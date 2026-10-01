import type { CollectionConfig } from "payload";

import { DataBlock } from "@/blocks/DataBlock";
import { MetricsBlock } from "@/blocks/MetricsBlock";

/**
 * Headless portal pages. Each page is addressed by a unique slug under
 * /portal/[...slug] and composes a layout from the raw, unstyled data
 * blocks. No visual configuration lives in this schema.
 */
export const Pages: CollectionConfig = {
  slug: "pages",
  admin: {
    useAsTitle: "title",
    defaultColumns: ["title", "slug"],
  },
  fields: [
    {
      name: "title",
      type: "text",
      required: true,
    },
    {
      name: "slug",
      type: "text",
      required: true,
      unique: true,
      index: true,
      admin: {
        description:
          'URL path segment(s) under /portal, e.g. "dashboard" or "finance/receivables".',
      },
    },
    {
      name: "blocks",
      type: "blocks",
      blocks: [MetricsBlock, DataBlock],
    },
  ],
};
