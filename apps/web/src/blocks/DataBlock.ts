import type { Block } from "payload";

/**
 * Raw tabular data slot. Maps a list of SAP dictionary field paths with no
 * styling or presentation metadata. Payload automatically assigns a unique
 * `id` to every block instance (and to each `sapFields` row).
 */
export const DataBlock: Block = {
  slug: "dataBlock",
  interfaceName: "DataBlock",
  labels: {
    singular: "Data Block",
    plural: "Data Blocks",
  },
  fields: [
    {
      name: "sapFields",
      type: "array",
      required: true,
      minRows: 1,
      admin: {
        description:
          "Ordered list of SAP dictionary field paths this block exposes.",
      },
      fields: [
        {
          name: "sapField",
          type: "text",
          required: true,
          admin: {
            description:
              'Dot path into the ingested SAP dictionary, e.g. "OINV.DocTotal". ' +
              "Validate names against apps/api/app/shared/sap_dictionary/.",
          },
        },
      ],
    },
  ],
};
