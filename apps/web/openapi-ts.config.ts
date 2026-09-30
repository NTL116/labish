import { defineConfig } from "@hey-api/openapi-ts";

// Pulls the OpenAPI schema from the running FastAPI development backend
// by default. Override with OPENAPI_INPUT (URL or local schema file) when
// generating without a live server.
export default defineConfig({
  input: process.env.OPENAPI_INPUT ?? "http://127.0.0.1:8000/openapi.json",
  output: {
    path: "src/lib/api",
  },
  plugins: ["@hey-api/client-next"],
});
