// Next.js server instrumentation hook. Env-gated Sentry init (no-op without a DSN).
import { initSentry } from "@/lib/sentry";

export async function register(): Promise<void> {
  await initSentry("server");
}
