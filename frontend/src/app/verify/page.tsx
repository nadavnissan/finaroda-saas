"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { routeAfterAuth } from "@/lib/app/session";

// /verify?token=... — target of the magic-link email. Verifies then routes the user:
// into onboarding if they have not completed it (FX1), otherwise to /scan.
export default function VerifyPage() {
  const [state, setState] = useState<"verifying" | "ok" | "error">("verifying");
  const [message, setMessage] = useState("Verifying your link…");

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("token");
    if (!token) {
      setState("error");
      setMessage("Missing token.");
      return;
    }
    api.verify(token).then(async (res) => {
      if (res.ok) {
        setState("ok");
        setMessage("Signed in. Redirecting…");
        const dest = await routeAfterAuth();
        setTimeout(() => {
          window.location.href = dest;
        }, 800);
      } else {
        setState("error");
        setMessage(res.error?.message ?? "Invalid or expired link.");
      }
    });
  }, []);

  return (
    <main>
      <h1>{state === "ok" ? "Welcome" : "Sign in"}</h1>
      <p>{message}</p>
      {state === "error" && <a href="/login">Back to sign in</a>}
    </main>
  );
}
