import { client } from "@/lib/api/client.gen";

export const SESSION_COOKIE = "labish_session";

export const API_BASE_URL =
  process.env.API_URL ?? "http://127.0.0.1:8000";

let configured = false;

/** Ensure the generated client targets the FastAPI backend. */
export function configureApiClient(): void {
  if (!configured) {
    client.setConfig({ baseUrl: API_BASE_URL });
    configured = true;
  }
}

/**
 * Lightweight structural check for the session JWT, safe for the Edge
 * runtime: confirms the token shape and that `exp` has not passed.
 * Cryptographic RS256 verification stays on the FastAPI backend.
 */
export function isSessionTokenUsable(token: string | undefined): boolean {
  if (!token) return false;
  const parts = token.split(".");
  if (parts.length !== 3) return false;
  try {
    const payload = JSON.parse(
      atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")),
    ) as { exp?: number };
    if (typeof payload.exp !== "number") return false;
    return payload.exp * 1000 > Date.now();
  } catch {
    return false;
  }
}
