"use client";

import { useState } from "react";

import { api } from "@/lib/api";

// (auth) — magic-link sign-in (+ Google planned). Beta-gated backend.
export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [message, setMessage] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("sending");
    const res = await api.requestMagicLink(email);
    if (res.ok) {
      setStatus("sent");
      setMessage("Check your email for a sign-in link.");
    } else {
      setStatus("error");
      setMessage(res.error?.message ?? "Something went wrong.");
    }
  }

  return (
    <main>
      <h1>Sign in</h1>
      {status === "sent" ? (
        <p>{message}</p>
      ) : (
        <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          <input
            type="email"
            required
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{ padding: "0.5rem", fontFamily: "monospace" }}
          />
          <button type="submit" disabled={status === "sending"}>
            {status === "sending" ? "Sending…" : "Send magic link"}
          </button>
          {status === "error" && <small>{message}</small>}
        </form>
      )}
      <small>Google sign-in — coming soon.</small>
    </main>
  );
}
