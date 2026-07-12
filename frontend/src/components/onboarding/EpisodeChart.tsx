"use client";

import { useState } from "react";

import { swingLevels } from "@/lib/chart/swings";
import { getTerm, renderNow } from "@/lib/onboarding/concepts";
import { C, type Candle } from "@/lib/onboarding/types";

import { ConceptTooltip } from "./ConceptTooltip";

// CHART STANDARD v1 (Package B base component). In-app SVG from real klines, never
// external captures. Prominent symbol badge separated from price/range/resolution,
// EMA7/EMA200 + swing S/R + optional Blueprint levels with DECLUTTERED side labels,
// event annotations (each opens its Concept Tooltip), and candle-tap OHLC.

const W = 360;
const H = 210;
const PADL = 46;
const PADR = 62; // room for decluttered right-side labels
const PADT = 10;
const PADB = 16;
const MONO = "'IBM Plex Mono', ui-monospace, monospace";

export interface ChartAnnotation {
  index: number;
  label: string;
  tooltipId: string;
  ctx?: Record<string, unknown>;
}
export interface BlueprintLevels {
  trigger?: number | null;
  risk?: number | null;
  target?: number | null;
}

interface SideLabel {
  y: number;
  text: string;
  color: string;
}

function fmt(n: number): string {
  const abs = Math.abs(n);
  const d = abs >= 100 ? 0 : abs >= 1 ? 2 : 4;
  return n.toLocaleString(undefined, { maximumFractionDigits: d });
}
function isoDate(ms: number): string {
  return new Date(ms).toISOString().slice(0, 10);
}

// Push overlapping side labels apart so Trigger/Risk/Target/EMA never collide.
function declutter(labels: SideLabel[], minGap: number, top: number, bottom: number): SideLabel[] {
  const out = labels.map((l) => ({ ...l })).sort((a, b) => a.y - b.y);
  for (let i = 1; i < out.length; i++) {
    if (out[i].y - out[i - 1].y < minGap) out[i].y = out[i - 1].y + minGap;
  }
  const overflow = out.length ? out[out.length - 1].y - bottom : 0;
  if (overflow > 0) for (const l of out) l.y -= overflow;
  for (const l of out) l.y = Math.max(top, l.y);
  return out;
}

export function EpisodeChart({
  data,
  entryIndex,
  entryPrice,
  emaMode = "ema7",
  symbol,
  dateRange,
  annotations = [],
  blueprint,
  showSwingLevels = true,
}: {
  data: Candle[];
  entryIndex: number;
  entryPrice?: number | null;
  emaMode?: "none" | "ema7" | "ema200" | "both";
  symbol?: string;
  dateRange?: string;
  annotations?: ChartAnnotation[];
  blueprint?: BlueprintLevels;
  showSwingLevels?: boolean;
}) {
  const [tap, setTap] = useState<{ candle: Candle; x: number; y: number } | null>(null);
  if (data.length === 0) return null;

  const levels = showSwingLevels ? swingLevels(data) : { support: null, resistance: null };

  const showEma7 = emaMode === "ema7" || emaMode === "both";
  const showEma200 = emaMode === "ema200" || emaMode === "both";

  const lows = data.map((c) => c.l);
  const highs = data.map((c) => c.h);
  let min = Math.min(...lows);
  let max = Math.max(...highs);
  const consider: number[] = [];
  const ema7s = data.map((c) => c.ema7).filter((x): x is number => x != null);
  if (showEma7) consider.push(...ema7s);
  const ema200s = data.map((c) => c.ema200).filter((x): x is number => x != null);
  if (showEma200) consider.push(...ema200s);
  if (entryPrice != null) consider.push(entryPrice);
  for (const v of [levels.support, levels.resistance, blueprint?.trigger, blueprint?.risk, blueprint?.target]) {
    if (v != null) consider.push(v);
  }
  if (consider.length) {
    min = Math.min(min, ...consider);
    max = Math.max(max, ...consider);
  }
  const padY = (max - min) * 0.06 || 1;
  min -= padY;
  max += padY;

  const plotW = W - PADL - PADR;
  const plotH = H - PADT - PADB;
  const n = data.length;
  const step = plotW / n;
  const cw = Math.max(2, step * 0.62);
  const x = (i: number) => PADL + step * (i + 0.5);
  const y = (p: number) => PADT + plotH * (1 - (p - min) / (max - min));

  const emaPath = (key: "ema7" | "ema200") =>
    data
      .map((c, i) => (c[key] != null ? `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(c[key] as number).toFixed(1)}` : ""))
      .join(" ")
      .trim();

  // collect right-side labels, then declutter so they never overlap
  const rawLabels: SideLabel[] = [];
  if (showEma7 && ema7s.length) rawLabels.push({ y: y(ema7s[ema7s.length - 1]), text: "EMA7", color: C.green });
  if (showEma200 && ema200s.length) rawLabels.push({ y: y(ema200s[ema200s.length - 1]), text: "EMA200", color: C.amber });
  if (levels.resistance != null) rawLabels.push({ y: y(levels.resistance), text: "Resistance", color: C.muted });
  if (levels.support != null) rawLabels.push({ y: y(levels.support), text: "Support", color: C.muted });
  if (blueprint?.trigger != null) rawLabels.push({ y: y(blueprint.trigger), text: "Trigger", color: C.fg });
  if (blueprint?.risk != null) rawLabels.push({ y: y(blueprint.risk), text: "Risk", color: C.red });
  if (blueprint?.target != null) rawLabels.push({ y: y(blueprint.target), text: "Target", color: C.green });
  const sideLabels = declutter(rawLabels, 9, PADT + 4, H - PADB);

  const lastClose = data[data.length - 1].c;
  const range = dateRange ?? `${isoDate(data[0].t)} to ${isoDate(data[data.length - 1].t)}`;

  return (
    <div style={{ width: "100%", maxWidth: 460, margin: "0 auto" }}>
      {/* Context header: symbol prominent on its own line, separated from the rest */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "0 2px 5px" }}>
        <span
          style={{
            fontFamily: MONO,
            fontSize: 13,
            fontWeight: 700,
            color: C.fg,
            background: C.bg,
            border: `1px solid ${C.border}`,
            borderRadius: 5,
            padding: "2px 8px",
            letterSpacing: 1,
          }}
        >
          {symbol ?? `${data.length} candles`}
        </span>
        <span style={{ fontFamily: MONO, fontSize: 12, color: C.green, fontWeight: 600 }}>{fmt(lastClose)}</span>
        <span style={{ fontFamily: MONO, fontSize: 9.5, color: C.muted, marginLeft: "auto" }}>
          {range} · Daily
        </span>
      </div>

      <div style={{ position: "relative" }}>
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="auto" style={{ display: "block", background: C.bg, border: `1px solid ${C.border}`, borderRadius: 8 }} role="img" aria-label="Episode price chart, real historical candles">
          {/* y grid */}
          {[max - padY, (max + min) / 2, min + padY].map((p, i) => (
            <g key={i}>
              <line x1={PADL} y1={y(p)} x2={W - PADR} y2={y(p)} stroke={C.border} strokeWidth={0.5} />
              <text x={PADL - 4} y={y(p) + 3} textAnchor="end" fill={C.subtle} fontSize={8} fontFamily={MONO}>
                {fmt(p)}
              </text>
            </g>
          ))}

          {/* swing S/R + blueprint level LINES (labels drawn decluttered on the right) */}
          {levels.resistance != null && <line x1={PADL} y1={y(levels.resistance)} x2={W - PADR} y2={y(levels.resistance)} stroke={C.muted} strokeWidth={0.7} strokeDasharray="1 3" />}
          {levels.support != null && <line x1={PADL} y1={y(levels.support)} x2={W - PADR} y2={y(levels.support)} stroke={C.muted} strokeWidth={0.7} strokeDasharray="1 3" />}
          {blueprint?.trigger != null && <line x1={PADL} y1={y(blueprint.trigger)} x2={W - PADR} y2={y(blueprint.trigger)} stroke={C.fg} strokeWidth={0.7} strokeDasharray="4 2" />}
          {blueprint?.risk != null && <line x1={PADL} y1={y(blueprint.risk)} x2={W - PADR} y2={y(blueprint.risk)} stroke={C.red} strokeWidth={0.7} strokeDasharray="4 2" />}
          {blueprint?.target != null && <line x1={PADL} y1={y(blueprint.target)} x2={W - PADR} y2={y(blueprint.target)} stroke={C.green} strokeWidth={0.7} strokeDasharray="4 2" />}

          {/* candles */}
          {data.map((c, i) => {
            const up = c.c >= c.o;
            const col = up ? C.green : C.red;
            const bodyTop = y(Math.max(c.o, c.c));
            const bodyBot = y(Math.min(c.o, c.c));
            return (
              <g key={c.t}>
                <line x1={x(i)} y1={y(c.h)} x2={x(i)} y2={y(c.l)} stroke={col} strokeWidth={1} />
                <rect x={x(i) - cw / 2} y={bodyTop} width={cw} height={Math.max(1, bodyBot - bodyTop)} fill={col} opacity={i > entryIndex ? 1 : 0.85} />
              </g>
            );
          })}

          {/* EMA overlays */}
          {showEma200 && emaPath("ema200") && <path d={emaPath("ema200")} fill="none" stroke={C.amber} strokeWidth={1.2} strokeDasharray="4 3" opacity={0.9} />}
          {showEma7 && emaPath("ema7") && <path d={emaPath("ema7")} fill="none" stroke={C.green} strokeWidth={1.2} opacity={0.9} />}

          {/* entry marker */}
          {entryPrice != null && (
            <>
              <line x1={x(entryIndex)} y1={PADT} x2={x(entryIndex)} y2={H - PADB} stroke={C.muted} strokeWidth={0.8} strokeDasharray="2 2" />
              <line x1={PADL} y1={y(entryPrice)} x2={W - PADR} y2={y(entryPrice)} stroke={C.muted} strokeWidth={0.6} strokeDasharray="2 2" />
            </>
          )}

          {/* decluttered right-side labels with short leader ticks */}
          {sideLabels.map((l) => (
            <g key={l.text}>
              <line x1={W - PADR} y1={l.y} x2={W - PADR + 3} y2={l.y} stroke={l.color} strokeWidth={0.6} />
              <text x={W - PADR + 5} y={l.y + 2.5} fill={l.color} fontSize={7.5} fontFamily={MONO}>
                {l.text}
              </text>
            </g>
          ))}
        </svg>

        {/* interaction + annotation overlay (percentage coords over the scaled SVG) */}
        <div style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
          {data.map((c, i) => (
            <button
              key={c.t}
              type="button"
              aria-label={`Candle ${isoDate(c.t)}`}
              onClick={(e) => setTap({ candle: c, x: e.clientX, y: e.clientY })}
              style={{ position: "absolute", left: `${((x(i) - step / 2) / W) * 100}%`, top: 0, width: `${(step / W) * 100}%`, height: "100%", background: "transparent", border: "none", padding: 0, cursor: "pointer", pointerEvents: "auto" }}
            />
          ))}
          {annotations
            .filter((a) => a.index < data.length)
            .map((a) => (
              <span key={a.label} style={{ position: "absolute", left: `${(x(a.index) / W) * 100}%`, top: `${(y(data[a.index].h) / H) * 100}%`, transform: "translate(-50%, -120%)", pointerEvents: "auto" }}>
                <ConceptTooltip id={a.tooltipId} label={a.label} ctx={a.ctx} pill />
              </span>
            ))}
        </div>

        {/* OHLC popover on candle tap (ohlc term) */}
        {tap && (
          <>
            <span onClick={() => setTap(null)} style={{ position: "fixed", inset: 0, zIndex: 49 }} />
            <span
              style={{
                position: "fixed",
                left: Math.min(tap.x, (typeof window !== "undefined" ? window.innerWidth : 360) - 200),
                top: tap.y + 8,
                zIndex: 50,
                width: 190,
                background: C.panel,
                border: `1px solid ${C.green}`,
                borderRadius: 8,
                padding: 10,
                fontFamily: MONO,
                fontSize: 11,
                color: C.fg,
                boxShadow: "0 8px 24px rgba(0,0,0,0.55)",
              }}
            >
              <strong style={{ color: C.green }}>{getTerm("ohlc")?.term ?? "Candle"}</strong>
              <span style={{ display: "block", marginTop: 4 }}>
                {renderNow(getTerm("ohlc")?.now ?? "", {
                  date: isoDate(tap.candle.t),
                  open: fmt(tap.candle.o),
                  high: fmt(tap.candle.h),
                  low: fmt(tap.candle.l),
                  close: fmt(tap.candle.c),
                })}
              </span>
            </span>
          </>
        )}
      </div>
    </div>
  );
}
