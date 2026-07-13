// Stage 7 frontend Sentry init (D-A6). Env-gated on NEXT_PUBLIC_SENTRY_DSN: with no DSN
// (dev / test) nothing initializes and there are zero network calls. The Sentry package
// is loaded via a runtime dynamic import so the build/type-check never hard-depends on it
// (it is a declared dependency; activation needs `pnpm install` on a deploy box).

/** Pure gate: init only when a DSN exists and we are not in the test environment. */
export function shouldInitSentry(dsn: string | undefined, env: string | undefined): boolean {
  return Boolean(dsn) && env !== "test";
}

interface SentryLike {
  init(opts: Record<string, unknown>): void;
  captureException(err: unknown): void;
}

let initialized = false;
let client: SentryLike | null = null;

export async function initSentry(runtime: "client" | "server"): Promise<boolean> {
  const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
  const env = process.env.NEXT_PUBLIC_ENV ?? process.env.NODE_ENV;
  if (initialized || !shouldInitSentry(dsn, env)) return false;
  try {
    // Non-literal specifier → the type-checker treats this as `any`, so the build never
    // requires @sentry/nextjs to be present. It is resolved at runtime when installed.
    const pkg = "@sentry/nextjs";
    const mod = (await import(pkg)) as unknown as SentryLike;
    mod.init({
      dsn,
      environment: env,
      tracesSampleRate: 0.1, // conservative (D-A6)
      initialScope: { tags: { runtime } }, // client vs server, no PII
      // No PII: Sentry defaults send_default_pii to false; we attach only ids elsewhere.
    });
    client = mod;
    initialized = true;
    return true;
  } catch {
    // Package not installed / init failed → stay disabled, never crash the app.
    return false;
  }
}

/** Report a handled error if Sentry is active; otherwise a no-op. */
export function captureError(err: unknown): void {
  if (client) client.captureException(err);
}
