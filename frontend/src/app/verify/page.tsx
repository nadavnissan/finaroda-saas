"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";

// /verify?token=... — target of the magic-link email. Verifies then routes to /scan.
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
    api.verify(token).then((res) => {
      if (res.ok) {
        setState("ok");
        setMessage("Signed in. Redirecting…");
        setTimeout(() => {
          window.location.href = "/scan";
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
