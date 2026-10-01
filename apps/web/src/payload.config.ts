import path from "path";
import { fileURLToPath } from "url";

import { postgresAdapter } from "@payloadcms/db-postgres";
import { lexicalEditor } from "@payloadcms/richtext-lexical";
import { buildConfig } from "payload";

import { Pages } from "@/collections/Pages";

const filename = fileURLToPath(import.meta.url);
const dirname = path.dirname(filename);

/**
 * Base headless Payload engine. Intentionally minimal: no theming, no
 * custom admin components, no styling decisions. Data lives in the same
 * PostgreSQL instance as the FastAPI backend (separate tables).
 */
export default buildConfig({
  secret: process.env.PAYLOAD_SECRET || "",
  db: postgresAdapter({
    pool: {
      connectionString: process.env.DATABASE_URI || "",
    },
  }),
  editor: lexicalEditor(),
  collections: [Pages],
  typescript: {
    outputFile: path.resolve(dirname, "payload-types.ts"),
  },
});
