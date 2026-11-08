import "./lib/error-capture"; // Side-effect import: patches console.error for server-side error tracking

import { consumeLastCapturedError } from "./lib/error-capture";
import { renderErrorPage } from "./lib/error-page";

/** Shape of a dynamically-imported TanStack Start server entry module */
type ServerEntry = {
  fetch: (request: Request, env: unknown, ctx: unknown) => Promise<Response> | Response;
};

// Cache the server entry promise to avoid re-importing on every request
let serverEntryPromise: Promise<ServerEntry> | undefined;

/**
 * Lazily imports the TanStack Start server entry module and caches the result.
 * Using a dynamic import ensures the entry is not bundled into this module.
 */
async function getServerEntry(): Promise<ServerEntry> {
  if (!serverEntryPromise) {
    serverEntryPromise = import("@tanstack/react-start/server-entry").then(
      (m) => (m.default ?? m) as ServerEntry,
    );
  }
  return serverEntryPromise;
}

/**
 * Detects h3's silent error swallowing and replaces the response with an HTML error page.
 *
 * h3 converts unhandled throws into a JSON body like:
 *   {"unhandled": true, "message": "HTTPError"}
 *
 * We identify that pattern, retrieve the original error from error-capture.ts,
 * log it properly, and return a user-friendly HTML error page instead.
 */
async function normalizeCatastrophicSsrResponse(response: Response): Promise<Response> {
  if (response.status < 500) return response;
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) return response;

  const body = await response.clone().text();
  if (!isH3SwallowedErrorBody(body)) return response;

  console.error(consumeLastCapturedError() ?? new Error(`h3 swallowed SSR error: ${body}`));
  return new Response(renderErrorPage(), {
    status: 500,
    headers: { "content-type": "text/html; charset=utf-8" },
  });
}

/**
 * Checks if a response body matches h3's silent error format.
 * Returns true when the body is exactly {"unhandled":true,"message":"HTTPError"}.
 */
function isH3SwallowedErrorBody(body: string): boolean {
  try {
    const payload = JSON.parse(body) as { unhandled?: unknown; message?: unknown };
    return payload.unhandled === true && payload.message === "HTTPError";
  } catch {
    return false;
  }
}

/**
 * Main Cloudflare Worker / Nitro fetch handler.
 * Processes every incoming HTTP request through TanStack Start's server,
 * then normalizes catastrophic SSR failures into friendly HTML error pages.
 */
export default {
  async fetch(request: Request, env: unknown, ctx: unknown) {
    try {
      const handler = await getServerEntry();
      const response = await handler.fetch(request, env, ctx);
      return await normalizeCatastrophicSsrResponse(response);
    } catch (error) {
      console.error(error);
      return new Response(renderErrorPage(), {
        status: 500,
        headers: { "content-type": "text/html; charset=utf-8" },
      });
    }
  },
};
