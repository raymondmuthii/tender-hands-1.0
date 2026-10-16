/**
 * TanStack Start application entry point
 *
 * Configures global server middleware for the application:
 * - errorMiddleware: catches unhandled server function errors and returns a
 *   proper HTML error page instead of crashing with a raw exception
 * - csrfMiddleware: protects server functions from cross-site request forgery
 *
 * Note: TanStack Start would normally auto-install csrfMiddleware when this
 * file is absent. Defining the file opts out of that, so we re-add it manually.
 */
import { createStart, createCsrfMiddleware, createMiddleware } from "@tanstack/react-start";

import { renderErrorPage } from "./lib/error-page";

/**
 * Middleware that wraps server function execution in a try/catch.
 * Re-throws errors with a status code (e.g. 404, 401) so they propagate
 * correctly; converts all other unhandled throws into a 500 HTML response.
 */
const errorMiddleware = createMiddleware().server(async ({ next }) => {
  try {
    return await next();
  } catch (error) {
    // Re-throw HTTP-status errors (TanStack Start uses statusCode to signal expected errors)
    if (error != null && typeof error === "object" && "statusCode" in error) {
      throw error;
    }
    // Log and convert unexpected errors to a user-friendly error page
    console.error(error);
    return new Response(renderErrorPage(), {
      status: 500,
      headers: { "content-type": "text/html; charset=utf-8" },
    });
  }
});

/**
 * CSRF protection middleware — restricts server function calls to same-origin requests.
 * Applied only to server function handler types (not regular GET/POST routes).
 */
const csrfMiddleware = createCsrfMiddleware({
  filter: (ctx) => ctx.handlerType === "serverFn",
});

export const startInstance = createStart(() => ({
  requestMiddleware: [errorMiddleware, csrfMiddleware],
}));
