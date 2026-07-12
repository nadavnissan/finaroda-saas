"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";
import { anonId } from "@/lib/onboarding/anon";
import { onboardingApi } from "@/lib/onboarding/api";
import { vibrateScan } from "@/lib/onboarding/haptics";
import { C, XP_AMOUNTS, type Candle, type EpisodeReveal, type EpisodeSetup } from "@/lib/onboarding/types";
import { SCAN_STEPS, ScanningLog } from "@/components/scan/ScanningLog";

import { ConceptTooltip } from "./ConceptTooltip";
import { EpisodeChart } from "./EpisodeChart";
import { OnboardingShell } from "./OnboardingShell";

type Step =
  | "S0" | "S1" | "S1a" | "S2" | "S3" | "S4" | "S5"
  | "S6" | "S7" | "S8" | "S9" | "S10" | "S11";

// ── copy (kept as constants so JSX renders {expressions} — avoids escaping) ────
const COPY = {
  s0: "The first 60 seconds",
  s1: "The market is going wild. What do you do right now?",
  s1a:
    "That was a trap. This is how most beginners get caught — you're in good company. " +
    "The difference between a gambler and a risk manager is checking before acting. " +
    "Try again — this time with the engine.",
  s3empty: "No setups pass — the spike did not clear the threshold.",
  s3lesson:
    "Price is jumping — but it's deep below the 200-day average and the weekly structure is negative. " +
    "On our analysis, the vast majority of spikes in conditions like these faded before 10%. No confirmation. " +
    "(In the full bear regime: 7 of 7.)",
  s5xp:
    "Your XP is your professional capital — you earn it on discipline and learning. " +
    "It sets your rank and unlocks knowledge modules.",
  s6: "Welcome to the training arena. We've opened full access — 14 days of Pro activate when you choose, with no credit card.",
  s7: "Practicing on a realistic amount builds real discipline. The system uses this to illustrate risk management — not to make recommendations.",
  s8lesson:
    "The difference from the trap = market structure (EMA200 / weekly) + verified EMA7 timing — without exposing weights or formulas.",
  s10gate:
    "Had you scanned that day, the system would have logged it — and your next scan would reveal the outcome.",
  s10turning:
    "The whole market was turning. The same setup that died seven times in June completed when the structure aligned — context is everything.",
  s11title: "Yesterday's market is history. Tomorrow's waits for the prepared.",
};

const btn = (bg: string, fg = "#0b0d12"): React.CSSProperties => ({
  background: bg,
  color: fg,
  border: "none",
  borderRadius: 8,
  padding: "12px 18px",
  fontFamily: "monospace",
  fontSize: 14,
  cursor: "pointer",
});
const ghostBtn: React.CSSProperties = {
  background: "none",
  color: C.muted,
  border: `1px solid ${C.border}`,
  borderRadius: 8,
  padding: "10px 16px",
  fontFamily: "monospace",
  cursor: "pointer",
};

export function OnboardingFlow() {
  const router = useRouter();
  const anon = useRef<string>("ssr");
  const [step, setStep] = useState<Step>("S0");
  const [earned, setEarned] = useState<string[]>([]);
  const [signedIn, setSignedIn] = useState(false);
  const [scanUnlocked, setScanUnlocked] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanStep, setScanStep] = useState(0);
  const [revealCount, setRevealCount] = useState(0);

  const [e1, setE1] = useState<EpisodeSetup | null>(null);
  const [e1r, setE1r] = useState<EpisodeReveal | null>(null);
  const [e3, setE3] = useState<EpisodeSetup | null>(null);
  const [e3r, setE3r] = useState<EpisodeReveal | null>(null);
  const [e4, setE4] = useState<EpisodeSetup | null>(null);
  const [e4r, setE4r] = useState<EpisodeReveal | null>(null);

  const [callsign, setCallsign] = useState("");
  const [portfolio, setPortfolio] = useState(1000);

  const xp = earned.reduce((s, r) => s + (XP_AMOUNTS[r] ?? 0), 0);

  useEffect(() => {
    anon.current = anonId();
    // Prefetch the trap setup (outcome stays withheld server-side).
    void onboardingApi.getEpisode("E1").then((r) => r.data && setE1(r.data));
  }, []);

  const go = useCallback((next: Step) => {
    setStep(next);
    void onboardingApi.funnel("screen_view", { screen: next }, anon.current);
  }, []);

  const earn = useCallback(
    (ref: string) => {
      setEarned((prev) => (prev.includes(ref) ? prev : [...prev, ref]));
      if (signedIn) void onboardingApi.awardXp(ref); // idempotent, best-effort
    },
    [signedIn],
  );

  // staged candle reveal (playback of stored candles)
  const playReveal = useCallback((len: number) => {
    setRevealCount(0);
    let i = 0;
    const t = setInterval(() => {
      i += 1;
      setRevealCount(i);
      if (i >= len) clearInterval(t);
    }, 260);
  }, []);

  // scan animation (with haptic + silent iOS fallback), then onDone
  const runScan = useCallback((onDone: () => void) => {
    vibrateScan();
    setScanning(true);
    setScanStep(0);
    let s = 0;
    const t = setInterval(() => {
      s = Math.min(s + 1, SCAN_STEPS.length - 1);
      setScanStep(s);
      if (s >= SCAN_STEPS.length - 1) {
        clearInterval(t);
        window.setTimeout(() => {
          setScanning(false);
          onDone();
        }, 450);
      }
    }, 350);
  }, []);

  // S0 auto-advance
  useEffect(() => {
    if (step !== "S0") return;
    const t = window.setTimeout(() => go("S1"), 2600);
    return () => window.clearTimeout(t);
  }, [step, go]);

  // S2 is the scan illusion: run the animation, award +50, reveal the trap, go S3
  useEffect(() => {
    if (step !== "S2") return;
    runScan(() => {
      earn("s2_scan");
      void onboardingApi.revealEpisode("E1").then((r) => {
        if (r.data) {
          setE1r(r.data);
          playReveal(r.data.reveal_klines.length);
        }
      });
      go("S3");
    });
  }, [step, runScan, earn, go, playReveal]);

  // ── episode chart helpers ─────────────────────────────────────────────────
  function chartData(setup: EpisodeSetup | null, reveal: EpisodeReveal | null): Candle[] {
    if (!setup) return [];
    const revealed = reveal ? reveal.reveal_klines.slice(0, revealCount) : [];
    return [...setup.setup_klines, ...revealed];
  }

  // ── signup (S5) ───────────────────────────────────────────────────────────
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);

  const finishSignup = useCallback(() => {
    setSignedIn(true);
    // persist everything accumulated pre-signup (idempotent, server-priced)
    setEarned((prev) => {
      prev.forEach((ref) => void onboardingApi.awardXp(ref));
      return prev;
    });
    void onboardingApi.funnel("signup", undefined, anon.current);
    go("S6");
  }, [go]);

  async function submitEmail() {
    if (!email.includes("@")) return;
    const res = await api.requestMagicLink(email);
    const devLink = (res.data as { dev_magic_link?: string } | null)?.dev_magic_link;
    if (devLink) {
      // dev: complete the loop in-session so XP + completion actually persist
      const token = new URL(devLink).searchParams.get("token");
      if (token) await api.verify(token);
      finishSignup();
    } else {
      setSent(true); // prod: check your email; the experience still continues
    }
  }

  // ── S11 fork ──────────────────────────────────────────────────────────────
  function chooseFork(choice: "trial" | "free") {
    void onboardingApi.funnel("fork_choice", { choice }, anon.current);
    void onboardingApi.complete();
    router.push(choice === "trial" ? "/paywall" : "/scan");
  }

  // ── render ────────────────────────────────────────────────────────────────
  if (scanning) {
    return (
      <OnboardingShell xp={xp} contextLine="Scanning · same engine as the live product">
        <ScanningLog step={scanStep} />
      </OnboardingShell>
    );
  }

  const e1ctx = e1 ? `Educational simulation · real data · ${e1.coin} ${e1.date_range}` : undefined;

  switch (step) {
    case "S0":
      return (
        <OnboardingShell xp={xp} contextLine={e1ctx}>
          <h1 style={{ margin: 0, fontSize: 28 }}>{COPY.s0}</h1>
          <p style={{ color: C.muted, marginTop: 8 }}>A 60-second, data-true simulation.</p>
        </OnboardingShell>
      );

    case "S1":
      return (
        <OnboardingShell xp={xp} contextLine={e1ctx}>
          <h2 style={{ marginTop: 0 }}>{COPY.s1}</h2>
          {e1 && <EpisodeChart data={e1.setup_klines} entryIndex={e1.entry_index} entryPrice={e1.entry_price} emaMode="none" />}
          <div style={{ display: "flex", gap: 12, justifyContent: "center", marginTop: 16 }}>
            <button type="button" style={btn(C.green)} onClick={() => go("S1a")}>
              BUY
            </button>
            <button type="button" style={btn(C.amber)} onClick={() => go("S1a")}>
              SELL
            </button>
            {scanUnlocked && (
              <button
                type="button"
                onClick={() => {
                  void onboardingApi.funnel("branch_1a_to_s2", undefined, anon.current);
                  go("S2");
                }}
                style={{
                  ...btn(C.bg, C.green),
                  border: `2px solid ${C.green}`,
                  boxShadow: `0 0 18px ${C.green}`,
                }}
              >
                SCAN
              </button>
            )}
          </div>
          {scanUnlocked && <p style={{ color: C.green, marginTop: 10 }}>There was another option all along.</p>}
        </OnboardingShell>
      );

    case "S1a":
      return (
        <OnboardingShell xp={xp} contextLine={e1ctx}>
          <h2 style={{ marginTop: 0, color: C.red }}>Position eroding…</h2>
          {e1 && (
            <EpisodeChart
              data={chartData(e1, e1r)}
              entryIndex={e1.entry_index}
              entryPrice={e1.entry_price}
              emaMode="none"
            />
          )}
          <p style={{ color: C.fg, marginTop: 12 }}>{COPY.s1a}</p>
          <button
            type="button"
            style={btn(C.green)}
            onClick={() => {
              // reveal the erosion, then send the user back with SCAN unlocked
              void onboardingApi.revealEpisode("E1").then((r) => {
                if (r.data) {
                  setE1r(r.data);
                  playReveal(r.data.reveal_klines.length);
                }
              });
              setScanUnlocked(true);
              go("S1");
            }}
          >
            Try again — with the engine
          </button>
        </OnboardingShell>
      );

    case "S3":
      return (
        <OnboardingShell xp={xp} contextLine={e1ctx}>
          <h2 style={{ marginTop: 0, color: C.amber }}>{COPY.s3empty}</h2>
          {e1 && (
            <EpisodeChart data={chartData(e1, e1r)} entryIndex={e1.entry_index} entryPrice={e1.entry_price} emaMode="both" />
          )}
          <p style={{ color: C.fg, marginTop: 12, textAlign: "left", fontSize: 14 }}>
            Price is jumping — but it&apos;s deep below the{" "}
            <ConceptTooltip id="ema200" hereRightNow={e1 ? distanceCopy(e1) : undefined} /> and the{" "}
            <ConceptTooltip id="weekly-structure" /> is negative. The vast majority of spikes in conditions like these
            faded before 10%. No confirmation. (In the full bear regime: 7 of 7.)
          </p>
          <button type="button" style={btn(C.green)} onClick={() => go("S4")}>
            Continue
          </button>
        </OnboardingShell>
      );

    case "S4": {
      const drop = e1r ? Math.abs(e1r.outcome.pct ?? 0).toFixed(1) : null;
      return (
        <OnboardingShell xp={xp} contextLine={e1ctx}>
          <div style={{ fontSize: 40 }}>🛡️</div>
          <p style={{ color: C.fg, fontSize: 15 }}>
            {drop
              ? `Your discipline just prevented entry into a scenario that eroded ${drop}% (episode data).`
              : "Your discipline just prevented entry into a setup that failed within a full bear regime (episode data)."}
          </p>
          <p style={{ color: C.green, fontFamily: "monospace" }}>+100 XP — first strategic decision</p>
          <button
            type="button"
            style={btn(C.green)}
            onClick={() => {
              earn("s4_first_decision");
              go("S5");
            }}
          >
            Save your achievement
          </button>
        </OnboardingShell>
      );
    }

    case "S5":
      return (
        <OnboardingShell xp={xp}>
          <h2 style={{ marginTop: 0, color: C.green }}>{xp} XP earned</h2>
          <p style={{ color: C.muted, fontSize: 13 }}>{COPY.s5xp}</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 8 }}>
            <button type="button" style={btn(C.fg)} onClick={finishSignup}>
              Continue with Google
            </button>
            <button type="button" style={btn(C.fg)} onClick={finishSignup}>
              Continue with Apple
            </button>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@email.com"
                style={{ flex: 1, padding: 10, background: C.bg, border: `1px solid ${C.border}`, color: C.fg, borderRadius: 8 }}
              />
              <button type="button" style={ghostBtn} onClick={() => void submitEmail()}>
                Email me a link
              </button>
            </div>
            {sent && (
              <button type="button" style={btn(C.green)} onClick={finishSignup}>
                I&apos;ve confirmed — continue
              </button>
            )}
          </div>
          <p style={{ color: C.subtle, fontSize: 11, marginTop: 8 }}>No credit card. Personal details only.</p>
        </OnboardingShell>
      );

    case "S6":
      return (
        <OnboardingShell xp={xp}>
          <h2 style={{ marginTop: 0 }}>The training arena is open</h2>
          <p style={{ color: C.fg }}>{COPY.s6}</p>
          <button type="button" style={btn(C.green)} onClick={() => go("S7")}>
            Enter
          </button>
        </OnboardingShell>
      );

    case "S7":
      return (
        <OnboardingShell xp={xp}>
          <h2 style={{ marginTop: 0 }}>Set your practice capital</h2>
          <input
            type="number"
            value={portfolio}
            onChange={(e) => setPortfolio(Math.max(0, Number(e.target.value)))}
            style={{ padding: 12, fontSize: 20, width: 160, textAlign: "center", background: C.bg, border: `1px solid ${C.border}`, color: C.fg, borderRadius: 8, fontFamily: "monospace" }}
          />
          <p style={{ color: C.muted, fontSize: 13, marginTop: 10 }}>{COPY.s7}</p>
          <button
            type="button"
            style={btn(C.green)}
            onClick={() => {
              void onboardingApi.getEpisode("E3").then((r) => r.data && setE3(r.data));
              go("S8");
            }}
          >
            Continue
          </button>
        </OnboardingShell>
      );

    case "S8":
      return (
        <OnboardingShell xp={xp} contextLine={e3 ? `Real case: ${e3.coin} ${e3.date_range}` : undefined}>
          <h2 style={{ marginTop: 0 }}>This is what PASS looks like</h2>
          {!e3r ? (
            <>
              {e3 && <EpisodeChart data={e3.setup_klines} entryIndex={e3.entry_index} entryPrice={e3.entry_price} emaMode="ema7" />}
              <button
                type="button"
                style={{ ...btn(C.bg, C.green), border: `2px solid ${C.green}`, boxShadow: `0 0 18px ${C.green}`, marginTop: 14 }}
                onClick={() =>
                  runScan(() => {
                    earn("s8_scan");
                    void onboardingApi.revealEpisode("E3").then((r) => {
                      if (r.data) {
                        setE3r(r.data);
                        playReveal(r.data.reveal_klines.length);
                      }
                    });
                  })
                }
              >
                SCAN
              </button>
            </>
          ) : (
            <>
              <div style={{ color: C.green, fontFamily: "monospace", marginBottom: 8 }}>1 PASS · 10 SCANNED</div>
              {e3 && <EpisodeChart data={chartData(e3, e3r)} entryIndex={e3.entry_index} entryPrice={e3.entry_price} emaMode="ema7" />}
              <EpisodeBlueprint setup={e3} reveal={e3r} />
              <p style={{ color: C.fg, fontSize: 13, textAlign: "left", marginTop: 10 }}>{COPY.s8lesson}</p>
              <button
                type="button"
                style={btn(C.green)}
                onClick={() => {
                  earn("s8_lesson");
                  go("S9");
                }}
              >
                Continue
              </button>
            </>
          )}
        </OnboardingShell>
      );

    case "S9":
      return (
        <OnboardingShell xp={xp}>
          <h2 style={{ marginTop: 0 }}>What should the system call you?</h2>
          <input
            type="text"
            value={callsign}
            onChange={(e) => setCallsign(e.target.value)}
            placeholder="call-sign"
            style={{ padding: 12, fontSize: 16, textAlign: "center", background: C.bg, border: `1px solid ${C.border}`, color: C.fg, borderRadius: 8 }}
          />
          <div style={{ marginTop: 14, padding: 12, border: `1px solid ${C.green}`, borderRadius: 10, display: "inline-block" }}>
            <span style={{ color: C.green, fontFamily: "monospace" }}>◈ {callsign || "trader"} — Strategy Apprentice</span>
          </div>
          <div>
            <button
              type="button"
              style={btn(C.green)}
              onClick={() => {
                void onboardingApi.getEpisode("E4").then((r) => r.data && setE4(r.data));
                go("S10");
              }}
            >
              Continue
            </button>
          </div>
        </OnboardingShell>
      );

    case "S10":
      return (
        <OnboardingShell xp={xp} contextLine={e4 ? `Time machine · ${e4.coin} ${e4.date_range}` : undefined}>
          <h2 style={{ marginTop: 0 }}>The time machine</h2>
          {e4 && (
            <EpisodeChart
              data={chartData(e4, e4r)}
              entryIndex={e4.entry_index}
              entryPrice={e4.entry_price}
              emaMode="ema7"
            />
          )}
          {!e4r ? (
            <>
              <p style={{ color: C.muted, fontSize: 13 }}>{COPY.s10gate}</p>
              <button
                type="button"
                style={{ ...btn(C.bg, C.green), border: `2px solid ${C.green}`, boxShadow: `0 0 18px ${C.green}` }}
                onClick={() =>
                  runScan(() =>
                    void onboardingApi.revealEpisode("E4").then((r) => {
                      if (r.data) {
                        setE4r(r.data);
                        playReveal(r.data.reveal_klines.length);
                      }
                    }),
                  )
                }
              >
                SCAN
              </button>
            </>
          ) : (
            <>
              <p style={{ color: C.fg, fontSize: 14 }}>{COPY.s10turning}</p>
              <p style={{ color: C.green, fontFamily: "monospace" }}>
                Outcome revealed: {e4r.outcome.r_multiple != null ? `+${e4r.outcome.r_multiple}R` : "—"} (a loss avoided is
                as real as a gain captured)
              </p>
              <button type="button" style={btn(C.green)} onClick={() => go("S11")}>
                Continue
              </button>
            </>
          )}
        </OnboardingShell>
      );

    case "S11":
      return (
        <OnboardingShell xp={xp}>
          <h2 style={{ marginTop: 0 }}>{COPY.s11title}</h2>
          <button type="button" style={{ ...btn(C.green), width: "100%" }} onClick={() => chooseFork("trial")}>
            Start 14 days of Pro — no credit card
          </button>
          <ul style={{ listStyle: "none", padding: 0, color: C.muted, fontSize: 12, textAlign: "left", margin: "10px 0" }}>
            <li>🛡️ No card, no auto-charge — we&apos;ll remind you 3 days before</li>
            <li>🔓 You decide at the end</li>
            <li>📊 Every scan is checked against 4 years of empirical data</li>
          </ul>
          <ForkTable />
          <button type="button" style={{ ...ghostBtn, width: "100%", marginTop: 10 }} onClick={() => chooseFork("free")}>
            Continue on Free
          </button>
        </OnboardingShell>
      );

    default:
      return null;
  }
}

// price distance from EMA200 at entry (setup-time fact, not the withheld outcome)
function distanceCopy(setup: EpisodeSetup): string | undefined {
  const entryCandle = setup.setup_klines[setup.entry_index];
  if (!entryCandle?.ema200 || setup.entry_price == null) return undefined;
  const pct = ((setup.entry_price - entryCandle.ema200) / entryCandle.ema200) * 100;
  return `price is ${pct.toFixed(0)}% below the 200-day average`;
}

// Minimal Trading Blueprint card for the episode success screen (canonical terms).
function EpisodeBlueprint({ setup, reveal }: { setup: EpisodeSetup | null; reveal: EpisodeReveal | null }) {
  if (!setup) return null;
  const row = (label: React.ReactNode, value: string) => (
    <div style={{ display: "flex", justifyContent: "space-between", fontFamily: "monospace", padding: "6px 0", borderBottom: `1px solid ${C.border}` }}>
      <span style={{ color: C.muted }}>{label}</span>
      <span>{value}</span>
    </div>
  );
  return (
    <div style={{ textAlign: "left", marginTop: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontFamily: "monospace", marginBottom: 6 }}>
        <span>
          {setup.coin} <span style={{ color: C.amber }}>{setup.direction?.toUpperCase()}</span>
        </span>
        {setup.score != null && <span style={{ color: C.green }}>Score {setup.score} · PASS ≥85</span>}
      </div>
      {row(<ConceptTooltip id="mathematical-trigger-point" />, fmtNum(setup.entry_price))}
      {row(<ConceptTooltip id="calculated-target-level" />, fmtNum(reveal?.outcome.exit_price ?? null))}
      {row(
        <ConceptTooltip id="r-multiple" />,
        reveal?.outcome.r_multiple != null ? `+${reveal.outcome.r_multiple}R` : "—",
      )}
      <small style={{ color: C.subtle }}>Levels are calculated from market structure — no weights or formulas exposed.</small>
    </div>
  );
}

function ForkTable() {
  const cell: React.CSSProperties = { padding: "6px 8px", borderBottom: `1px solid ${C.border}`, fontSize: 11, fontFamily: "monospace" };
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", color: C.fg }}>
      <thead>
        <tr>
          <th style={{ ...cell, textAlign: "left", color: C.muted }} />
          <th style={{ ...cell, color: C.green }}>Free forever</th>
          <th style={cell}>Basic</th>
          <th style={cell}>Advanced</th>
          <th style={cell}>Pro</th>
        </tr>
      </thead>
      <tbody>
        {[
          ["Scans / day", "1", "∞", "∞", "∞"],
          ["Coins", "2", "2", "5", "10"],
          ["Trading Blueprint", "full", "full", "full", "full"],
          ["Journal (F3)", "7 days", "full", "full", "full"],
          ["Export", "—", "—", "✓", "✓"],
        ].map((r) => (
          <tr key={r[0]}>
            <td style={{ ...cell, textAlign: "left", color: C.muted }}>{r[0]}</td>
            <td style={cell}>{r[1]}</td>
            <td style={cell}>{r[2]}</td>
            <td style={cell}>{r[3]}</td>
            <td style={cell}>{r[4]}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function fmtNum(n: number | null): string {
  if (n == null) return "—";
  const abs = Math.abs(n);
  const d = abs >= 100 ? 0 : abs >= 1 ? 2 : 4;
  return n.toLocaleString(undefined, { maximumFractionDigits: d });
}
