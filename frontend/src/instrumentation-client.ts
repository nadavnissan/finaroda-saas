// Next.js client instrumentation (runs in the browser). Env-gated Sentry init: with no
// NEXT_PUBLIC_SENTRY_DSN this is a no-op with zero network calls.
import { initSentry } from "@/lib/sentry";

void initSentry("client");
