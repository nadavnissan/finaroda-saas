"use client";

import { C, type Candle } from "@/lib/onboarding/types";

// In-app SVG candlestick renderer (the "v25.67 SVG engine" reference, Onboarding
// Spec §1.5). Real klines only — never external captures. Supports staged reveal
// (parent appends reveal candles over time) + EMA7 / EMA200 overlays + entry marker.

const W = 360;
const H = 200;
const PADL = 46;
const PADR = 8;
const PADT = 10;
const PADB = 18;

function fmt(n: number): string {
  const abs = Math.abs(n);
  const d = abs >= 100 ? 0 : abs >= 1 ? 2 : 4;
  return n.toLocaleString(undefined, { maximumFractionDigits: d });
}

export function EpisodeChart({
  data,
  entryIndex,
  entryPrice,
  emaMode = "ema7",
}: {
  data: Candle[]; // setup candles + any revealed reveal candles (in order)
  entryIndex: number; // index of the entry candle within `data`
  entryPrice?: number | null;
  emaMode?: "none" | "ema7" | "both";
}) {
  if (data.length === 0) return null;

  const lows = data.map((c) => c.l);
  const highs = data.map((c) => c.h);
  let min = Math.min(...lows);
  let max = Math.max(...highs);
  const ema7s = data.map((c) => c.ema7).filter((x): x is number => x != null);
  if (emaMode !== "none" && ema7s.length) {
    min = Math.min(min, ...ema7s);
    max = Math.max(max, ...ema7s);
  }
  const ema200s = data.map((c) => c.ema200).filter((x): x is number => x != null);
  if (emaMode === "both" && ema200s.length) {
    max = Math.max(max, ...ema200s); // intentionally shows the price-vs-EMA200 gap (S3 lesson)
  }
  if (entryPrice != null) {
    min = Math.min(min, entryPrice);
    max = Math.max(max, entryPrice);
  }
  const pad = (max - min) * 0.05 || 1;
  min -= pad;
  max += pad;

  const plotW = W - PADL - PADR;
  const plotH = H - PADT - PADB;
  const n = data.length;
  const step = plotW / n;
  const cw = Math.max(2, step * 0.62);
  const x = (i: number) => PADL + step * (i + 0.5);
  const y = (p: number) => PADT + plotH * (1 - (p - min) / (max - min));

  const ema7Path = data
    .map((c, i) => (c.ema7 != null ? `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(c.ema7).toFixed(1)}` : ""))
    .join(" ")
    .replace(/^ */, "");
  const ema200Path = data
    .map((c, i) => (c.ema200 != null ? `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(c.ema200).toFixed(1)}` : ""))
    .join(" ");

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      width="100%"
      style={{ maxWidth: 460, background: C.bg, border: `1px solid ${C.border}`, borderRadius: 8 }}
      role="img"
      aria-label="Episode price chart (real historical candles)"
    >
      {/* y grid + labels */}
      {[max - pad, (max + min) / 2, min + pad].map((p, i) => (
        <g key={i}>
          <line x1={PADL} y1={y(p)} x2={W - PADR} y2={y(p)} stroke={C.border} strokeWidth={0.5} />
          <text x={PADL - 4} y={y(p) + 3} textAnchor="end" fill={C.subtle} fontSize={8} fontFamily="monospace">
            {fmt(p)}
          </text>
        </g>
      ))}

      {/* candles */}
      {data.map((c, i) => {
        const up = c.c >= c.o;
        const col = up ? C.green : C.red;
        const bodyTop = y(Math.max(c.o, c.c));
        const bodyBot = y(Math.min(c.o, c.c));
        return (
          <g key={c.t}>
            <line x1={x(i)} y1={y(c.h)} x2={x(i)} y2={y(c.l)} stroke={col} strokeWidth={1} />
            <rect
              x={x(i) - cw / 2}
              y={bodyTop}
              width={cw}
              height={Math.max(1, bodyBot - bodyTop)}
              fill={col}
              opacity={i > entryIndex ? 1 : 0.85}
            />
          </g>
        );
      })}

      {/* EMA overlays */}
      {emaMode === "both" && ema200Path && (
        <path d={ema200Path} fill="none" stroke={C.amber} strokeWidth={1.2} strokeDasharray="4 3" opacity={0.9} />
      )}
      {emaMode !== "none" && ema7Path && <path d={ema7Path} fill="none" stroke={C.green} strokeWidth={1.2} opacity={0.9} />}

      {/* entry marker */}
      {entryPrice != null && (
        <>
          <line
            x1={x(entryIndex)}
            y1={PADT}
            x2={x(entryIndex)}
            y2={H - PADB}
            stroke={C.muted}
            strokeWidth={0.8}
            strokeDasharray="2 2"
          />
          <line x1={PADL} y1={y(entryPrice)} x2={W - PADR} y2={y(entryPrice)} stroke={C.muted} strokeWidth={0.6} strokeDasharray="2 2" />
        </>
      )}
    </svg>
  );
}
