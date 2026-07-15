"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";
import { C } from "@/lib/onboarding/types";
import { REFERRAL_KEY } from "@/lib/app/promotions";
import { routeAfterAuth } from "@/lib/app/session";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";

// btn() mirrors OnboardingFlow — filled terminal button, dark fg on bright bg.
const btn = (bg: string, fg: string = C.bg): React.CSSProperties => ({
  background: bg,
  color: fg,
  border: "none",
  borderRadius: 8,
  padding: "12px 18px",
  fontFamily: MONO,
  fontSize: 14,
  fontWeight: 600,
  cursor: "pointer",
  letterSpacing: 1,
});

type Status = "idle" | "sending" | "sent" | "error";

// (auth) — magic-link sign-in with terminal aesthetic (B6a). DEV SIGN-IN surfaces
// the backend dev_magic_link (staging/dev only, gated behind DEV_RETURN_MAGIC_LINK).
export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("");
  const [devToken, setDevToken] = useState<string | null>(null);
  const [devBusy, setDevBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.includes("@")) {
      setStatus("error");
      setMessage("Enter a valid email address.");
      return;
    }
    setStatus("sending");
    setDevToken(null);
    // A pending /r/<code> referral is bound once, server-side, when a NEW account signs up.
    let referralCode: string | null = null;
    if (typeof window !== "undefined") {
      try {
        referralCode = window.localStorage.getItem(REFERRAL_KEY);
      } catch {
        referralCode = null;
      }
    }
    const res = await api.requestMagicLink(email, referralCode);
    if (res.ok) {
      const devLink = (res.data as { dev_magic_link?: string } | null)?.dev_magic_link;
      if (devLink) {
        try {
          const token = new URL(devLink).searchParams.get("token");
          if (token) setDevToken(token);
        } catch {
          // Malformed dev link — fall through to the normal sent state.
        }
      }
      setStatus("sent");
      setMessage("Check your email for a sign-in link.");
    } else {
      setStatus("error");
      setMessage(res.error?.message ?? "Something went wrong. Try again.");
    }
  }

  async function devSignIn() {
    if (!devToken || devBusy) return;
    setDevBusy(true);
    const res = await api.verify(devToken);
    if (res.ok) {
      // FX1: a user who hasn't finished onboarding goes into it, not straight to /scan.
      router.push(await routeAfterAuth());
    } else {
      setDevBusy(false);
      setStatus("error");
      setMessage(res.error?.message ?? "Dev sign-in failed.");
    }
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        background: C.bg,
        color: C.fg,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 20,
        fontFamily: SANS,
      }}
    >
      <div style={{ width: "100%", maxWidth: 420, display: "flex", flexDirection: "column", alignItems: "center" }}>
        {/* Wordmark */}
        <span style={{ font: `700 15px ${SANS}`, letterSpacing: 5, color: C.fg, marginBottom: 6 }}>FINARODA</span>
        <span style={{ font: `400 10px ${MONO}`, letterSpacing: 2, color: C.green, marginBottom: 24 }}>
          <span style={{ display: "inline-block", width: 6, height: 6, background: C.green, borderRadius: 1, marginRight: 6, verticalAlign: "middle" }} />
          TERMINAL ACCESS
        </span>

        {/* Card */}
        <div
          style={{
            width: "100%",
            background: C.panel,
            border: `1px solid ${C.border}`,
            borderRadius: 12,
            padding: 24,
            display: "flex",
            flexDirection: "column",
            gap: 16,
          }}
        >
          <div>
            <h1 style={{ margin: 0, font: `700 20px ${SANS}`, letterSpacing: 0.5 }}>Sign in</h1>
            <p style={{ margin: "6px 0 0", font: `400 12px ${SANS}`, color: C.muted }}>
              No password. We email you a one-time sign-in link.
            </p>
          </div>

          {status === "sent" ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div
                style={{
                  border: `1px solid ${C.green}`,
                  borderRadius: 8,
                  padding: "14px 16px",
                  background: "rgba(31,178,134,.08)",
                }}
              >
                <div style={{ font: `600 11px ${MONO}`, letterSpacing: 1, color: C.green, marginBottom: 4 }}>
                  ✓ LINK SENT
                </div>
                <div style={{ font: `400 13px ${SANS}`, color: C.fg }}>{message}</div>
                <div style={{ font: `400 11px ${MONO}`, color: C.muted, marginTop: 6 }}>{email}</div>
              </div>

              {devToken && (
                <button type="button" onClick={devSignIn} disabled={devBusy} style={devBtnStyle(devBusy)}>
                  <span style={devTagStyle}>DEV</span>
                  {devBusy ? "SIGNING IN…" : "DEV SIGN-IN"}
                </button>
              )}

              <button
                type="button"
                onClick={() => {
                  setStatus("idle");
                  setMessage("");
                  setDevToken(null);
                }}
                style={{
                  background: "none",
                  color: C.muted,
                  border: `1px solid ${C.border}`,
                  borderRadius: 8,
                  padding: "10px 16px",
                  fontFamily: MONO,
                  fontSize: 12,
                  cursor: "pointer",
                }}
              >
                Use a different email
              </button>
            </div>
          ) : (
            <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <label style={{ font: `600 10px ${MONO}`, letterSpacing: 1.5, color: C.muted }}>EMAIL</label>
              <input
                type="email"
                required
                inputMode="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (status === "error") setStatus("idle");
                }}
                style={{
                  background: C.bg,
                  color: C.fg,
                  border: `1px solid ${C.border}`,
                  borderRadius: 8,
                  padding: "12px 14px",
                  fontFamily: MONO,
                  fontSize: 14,
                  outline: "none",
                  width: "100%",
                  boxSizing: "border-box",
                }}
              />

              {status === "error" && (
                <div style={{ font: `400 11px ${MONO}`, color: C.red }}>{message}</div>
              )}

              <button type="submit" disabled={status === "sending"} style={{ ...btn(C.green), opacity: status === "sending" ? 0.6 : 1 }}>
                {status === "sending" ? "SENDING…" : "Email me a sign-in link"}
              </button>
            </form>
          )}

          <div style={{ height: 1, background: C.border, opacity: 0.6 }} />

          <button
            type="button"
            disabled
            style={{
              background: "none",
              color: C.subtle,
              border: `1px dashed ${C.border}`,
              borderRadius: 8,
              padding: "11px 16px",
              fontFamily: MONO,
              fontSize: 12,
              cursor: "not-allowed",
            }}
          >
            Google sign-in, coming soon
          </button>
        </div>

        {/* Disclaimer */}
        <div style={{ font: `400 10px ${MONO}`, color: C.muted, marginTop: 22, textAlign: "center" }}>
          Analysis, not financial advice.
        </div>
      </div>
    </main>
  );
}

// DEV SIGN-IN — amber affordance, clearly non-production.
function devBtnStyle(busy: boolean): React.CSSProperties {
  return {
    ...btn(C.bg, C.amber),
    border: `1px solid ${C.amber}`,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    opacity: busy ? 0.6 : 1,
  };
}

const devTagStyle: React.CSSProperties = {
  font: `700 8px ${MONO}`,
  letterSpacing: 1,
  color: C.bg,
  background: C.amber,
  borderRadius: 3,
  padding: "2px 5px",
};
