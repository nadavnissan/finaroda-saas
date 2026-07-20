"use client";

import { useEffect } from "react";

/**
 * Registers the minimal service worker (/sw.js) in production only.
 *
 * The SW does ONE thing: serve a graceful offline page when a navigation fails
 * offline. It never caches app HTML/JS/CSS, so it can never serve a stale app
 * (a deliberate choice — no stale-version bugs). Dev is skipped so Next HMR is
 * untouched. Renders nothing.
 */
export function ServiceWorkerRegister() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production") return;
    if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return;
    const register = () => {
      navigator.serviceWorker.register("/sw.js").catch(() => {
        /* registration failure is non-fatal — the app works without offline fallback */
      });
    };
    if (document.readyState === "complete") register();
    else window.addEventListener("load", register, { once: true });
  }, []);

  return null;
}
