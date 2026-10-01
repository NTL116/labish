import type { Block } from "payload";

/**
 * Raw metric data slot. Carries zero visual design decisions — the design
 * team styles the rendered output later. Payload automatically assigns a
 * unique `id` to every block instance in a layout.
 */
export const MetricsBlock: Block = {
  slug: "metricsBlock",
  interfaceName: "MetricsBlock",
  labels: {
    singular: "Metrics Block",
    plural: "Metrics Blocks",
  },
  fields: [
    {
      name: "label",
      type: "text",
      required: true,
      admin: {
        description: "Plain string label for the metric slot.",
      },
    },
    {
      name: "sapField",
      type: "text",
      required: true,
      admin: {
        description:
          'Dot path into the ingested SAP dictionary, e.g. "OCRD.Balance". ' +
          "Validate names against apps/api/app/shared/sap_dictionary/.",
      },
    },
  ],
};
