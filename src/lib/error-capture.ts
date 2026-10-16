/**
 * Server-side error capture utility
 *
 * Addresses a critical limitation: h3 (the HTTP framework used by TanStack Start)
 * serializes thrown Errors into a bare string, losing stack traces and cause chains.
 * Even worse, HTTPError throws get swallowed into the generic JSON body:
 *   {"status":500,"unhandled":true,"message":"HTTPError"}
 *
 * This module patches console.error to intercept, record, and expand Error objects
 * before they reach h3's serialization layer. It also listens for global error events.
 *
 * Functions exported:
 * - describeError(error): converts an Error into a formatted string with full cause chain
 * - consumeLastCapturedError(): retrieves the most recent error captured (TTL: 5 seconds)
 */

let lastCapturedError: { error: unknown; at: number } | undefined;
const TTL_MS = 5_000; // Captured errors expire after 5 seconds

/** Records an error with the current timestamp */
function record(error: unknown) {
  lastCapturedError = { error, at: Date.now() };
}
// Configuration for error serialization
const CAUSE_DEPTH_LIMIT = 5;           // Maximum depth for traversing error cause chains
const DESCRIPTION_LENGTH_LIMIT = 8_000; // Maximum character length for error descriptions

/**
 * Converts an error into a detailed string representation.
 *
 * Handles:
 * - Error instances: includes stack trace and traverses cause chain up to 5 levels deep
 * - Plain strings: returned as-is
 * - Objects with a message property: extracts and returns the message
 * - Other values: JSON.stringify or String() fallback
 *
 * For errors with a .status or .statusCode property, appends " (status <code>)".
 */
export function describeError(error: unknown): string {
  const parts: string[] = [];
  let current: unknown = error;
  for (let depth = 0; depth < CAUSE_DEPTH_LIMIT && current != null; depth++) {
    if (!(current instanceof Error)) {
      parts.push(typeof current === "string" ? current : safeStringify(current));
      break;
    }
    const label = depth === 0 ? "" : "caused by: ";
    const status = describeStatus(current);
    parts.push(`${label}${current.stack ?? `${current.name}: ${current.message}`}${status}`);
    current = current.cause;
  }
  return parts.join("\n").slice(0, DESCRIPTION_LENGTH_LIMIT);
}

/** Extracts and formats HTTP status code from an Error if present */
function describeStatus(error: Error): string {
  const { status, statusCode } = error as { status?: unknown; statusCode?: unknown };
  const value = status ?? statusCode;
  return typeof value === "number" ? ` (status ${value})` : "";
}

/** Safely converts any value to a string representation */
function safeStringify(value: unknown): string {
  try {
    return JSON.stringify(value) ?? String(value);
  } catch {
    return String(value);
  }
}

/** Type guard to check if a value is an Error instance */
function isErrorLike(value: unknown): value is Error {
  return value instanceof Error;
}

/**
 * Patch console.error to intercept and expand Error objects before serialization.
 *
 * This ensures that errors logged by any part of the application (including h3's
 * internal unhandled-error logging) are:
 * 1. Recorded for later retrieval via consumeLastCapturedError()
 * 2. Expanded into a full description with stack trace and cause chain
 *
 * Without this patch, h3 would serialize Errors to bare strings, losing critical
 * debugging information.
 */
const originalConsoleError = console.error.bind(console);
console.error = (...args: unknown[]) => {
  const expanded = args.map((arg) => {
    if (!isErrorLike(arg)) return arg;
    record(arg);               // Record for consumeLastCapturedError()
    return describeError(arg); // Expand to full description with stack and causes
  });
  originalConsoleError(...expanded);
};

/**
 * Register global error event listeners (Node.js/Worker environment).
 * Records uncaught errors and unhandled promise rejections.
 */
if (typeof globalThis.addEventListener === "function") {
  globalThis.addEventListener("error", (event) => record((event as ErrorEvent).error ?? event));
  globalThis.addEventListener("unhandledrejection", (event) =>
    record((event as PromiseRejectionEvent).reason),
  );
}

/**
 * Retrieves the most recently captured error (if within TTL).
 * Automatically clears the cached error after consumption or expiration.
 *
 * Used by server.ts to recover the original Error when h3 has swallowed
 * it into a generic 500 JSON response.
 */
export function consumeLastCapturedError(): unknown {
  if (!lastCapturedError) return undefined;
  if (Date.now() - lastCapturedError.at > TTL_MS) {
    lastCapturedError = undefined;
    return undefined;
  }
  const { error } = lastCapturedError;
  lastCapturedError = undefined;
  return error;
}
