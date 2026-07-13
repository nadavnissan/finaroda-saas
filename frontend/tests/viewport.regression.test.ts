// Viewport regression harness (RESPONSIVE PASS).
// Run: node --test --experimental-strip-types tests/viewport.regression.test.ts
//
// WHY A STRUCTURAL LINT AND NOT A HEADLESS BROWSER:
// A true `scrollWidth <= clientWidth` assertion needs a real layout engine. jsdom
// computes no layout (both are always 0), and Playwright/a booted Next server does
// not run reliably in this local Windows dev loop (builds already time out), so a
// browser gate would fail for environment reasons and get ignored within a week.
// Nadav's manual phone validations ARE the real-pixel measurement. This lint instead
// encodes the SPECIFIC overflow-regression patterns we fix, as source-text checks
// that run everywhere with zero new deps.
//
// HOW TO EXTEND (do this every time a manual validation finds a new overflow bug):
//   - a fresh class of bug  -> add an object to PATTERNS
//   - a screen that must stay a centered max-width column -> add it to MAXWIDTH_ROUTES
//   - a wide table that must stay in a scroller -> add it to SCROLLER_FILES
// Keep each check precise (low false-positive) so the gate stays trusted.

import assert from "node:assert/strict";
import { test } from "node:test";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const SRC = join(HERE, "..", "src");

function walk(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) out.push(...walk(full));
    else out.push(full);
  }
  return out;
}
const ALL = walk(SRC);
const CODE = ALL.filter((f) => f.endsWith(".tsx") || f.endsWith(".ts"));
const read = (rel: string) => readFileSync(join(SRC, rel), "utf8");
const rel = (abs: string) => abs.slice(SRC.length + 1).replace(/\\/g, "/");

// ── PATTERNS: general overflow-regression rules, scanned across every component ──
interface Pattern {
  name: string;
  // Return a list of human-readable violations for one file (empty = clean).
  find: (src: string, file: string) => string[];
}

const PATTERNS: Pattern[] = [
  {
    // A raw fixed `width: N` (N >= 360px) on its own overflows a 360px phone. It is
    // only safe if the SAME inline-style line also bounds it — maxWidth, a vw unit,
    // "100%", or a `mobile` branch (desktop-only fixed widths are guarded by the
    // useIsMobile ternary). Charts use width:"100%" + viewBox, so they pass.
    // maxWidth:/minWidth:/strokeWidth:/borderLeftWidth: are excluded by the lookbehind.
    name: "no unbounded fixed width >= 360px on a container",
    find(src, file) {
      const bad: string[] = [];
      src.split("\n").forEach((line, i) => {
        const re = /(?<![A-Za-z])width:\s*(\d{3,})\b/g;
        let m: RegExpExecArray | null;
        while ((m = re.exec(line)) !== null) {
          const px = Number(m[1]);
          if (px < 360) continue;
          const guarded = /maxWidth|vw\b|"100%"|'100%'|mobile/.test(line);
          if (!guarded) bad.push(`${file}:${i + 1} width:${px} with no maxWidth/vw/100%/mobile guard`);
        }
      });
      return bad;
    },
  },
];

test("no component declares an unbounded fixed width that overflows a 360px phone", () => {
  const violations: string[] = [];
  for (const abs of CODE) {
    const src = readFileSync(abs, "utf8");
    for (const p of PATTERNS) violations.push(...p.find(src, rel(abs)));
  }
  assert.deepEqual(violations, [], `Overflow risks found:\n${violations.join("\n")}`);
});

// ── MAXWIDTH_ROUTES: product screens must center a bounded column (no edge-to-edge
// content that stretches on desktop / has nothing to constrain it on mobile). Admin
// is intentionally full-width and is checked separately (it uses useIsMobile). ──
const MAXWIDTH_ROUTES: string[] = [
  "app/(scan)/scan/page.tsx",
  "app/(scan)/history/page.tsx",
  "app/(dashboard)/dashboard/page.tsx",
  "app/(profile)/profile/page.tsx",
  "app/(profile)/settings/page.tsx",
  "app/(academy)/academy/page.tsx",
  "app/(academy)/academy/[moduleId]/page.tsx",
  "app/subscribe/page.tsx",
  "app/(auth)/login/page.tsx",
  "components/onboarding/OnboardingShell.tsx", // frames every onboarding screen
  "components/scan/TradingBlueprint.tsx", // full-screen scan modal
  "components/scan/NonPasser.tsx", // full-screen why-not modal
];

test("every product route constrains its content to a max-width column", () => {
  for (const route of MAXWIDTH_ROUTES) {
    assert.match(read(route), /maxWidth/, `${route} must bound its content with maxWidth (mobile-first centered column)`);
  }
});

// ── The admin console is full-width by design, so it must instead branch its layout
// on the viewport (rail -> top tabs, split panes -> master/detail swap). ──
test("admin console is responsive (branches on useIsMobile, no leaked centered main)", () => {
  const admin = read("app/(admin)/admin/page.tsx");
  assert.match(admin, /useIsMobile/, "admin must swap layout on mobile via useIsMobile");
  // The global `main` rule centers + pads; admin must override it to lay out edge-to-edge.
  assert.match(admin, /flexDirection:\s*mobile\s*\?\s*"column"\s*:\s*"row"/, "admin <main> must stack on mobile and use a rail on desktop");
});

// ── SCROLLER_FILES: files with a table too wide for a phone must keep it inside a
// horizontal scroller so it is never clipped (Nadav: "never cut off"). ──
const SCROLLER_FILES: string[] = [
  "components/onboarding/OnboardingFlow.tsx", // S11 comparison ForkTable
  "app/(admin)/admin/page.tsx", // notifications log + mobile tab strip
];

test("wide tables live inside a horizontal scroller", () => {
  for (const f of SCROLLER_FILES) {
    assert.match(read(f), /overflowX:\s*"auto"/, `${f} must wrap its wide table in an overflowX:"auto" scroller`);
  }
});

// ── Charts must scale to their container (viewBox + width:100%), never a fixed px SVG. ──
test("EpisodeChart scales to its container", () => {
  const chart = read("components/onboarding/EpisodeChart.tsx");
  assert.match(chart, /viewBox=/, "chart must use a viewBox to scale");
  assert.match(chart, /width="100%"/, "chart svg must be width:100% (fluid)");
});

// ── Global safety net: no horizontal page scrollbar, responsive gutter, media capped. ──
test("globals.css guards against horizontal overflow", () => {
  const css = read("app/globals.css");
  assert.match(css, /overflow-x:\s*hidden/, "body must never show a horizontal page scrollbar");
  assert.match(css, /padding:\s*clamp\(/, "main gutter must be a responsive clamp(), not a fixed 2rem");
  assert.match(css, /max-width:\s*100%/, "img/svg/table must be capped at 100% width");
});
