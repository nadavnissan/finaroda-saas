"use client";

import { useState } from "react";

import { api } from "@/lib/api";

// coming-soon — pre-launch landing + waitlist capture (SPEC §3.1).
export default function ComingSoonPage() {
  const [email, setEmail] = useState("");
  const [joined, setJoined] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const res = await api.joinWaitlist(email);
    if (res.ok) {
      setJoined(true);
    } else {
      setError(res.error?.message ?? "Something went wrong.");
    }
  }

  return (
    <main>
      <h1>FINARODA — coming soon</h1>
      {joined ? (
        <p>You&apos;re on the waitlist. We&apos;ll be in touch.</p>
      ) : (
        <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          <p>Closed beta. Join the waitlist.</p>
          <input
            type="email"
            required
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{ padding: "0.5rem", fontFamily: "monospace" }}
          />
          <button type="submit">Join waitlist</button>
          {error && <small>{error}</small>}
        </form>
      )}
    </main>
  );
}
