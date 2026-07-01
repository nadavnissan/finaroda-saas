/**
 * FINARODA — shared scoring engine (`scoring-engine.js`).
 *
 * ⚠️ PLACEHOLDER ONLY — NO IMPLEMENTATION.
 *
 * This is the single shared calculation brain (pure math, zero UI) that BOTH the
 * personal tool and the SaaS scan core import (SPEC §6.1, §12 decision 7).
 *
 * The real logic still lives woven inside the compiled React of the personal tool
 * (730KB). It has NOT been extracted yet. Every function below is a signature stub
 * that returns the {@link TODO} sentinel. Nadav supplies the real implementation
 * from the personal tool later — do NOT invent logic here, and do NOT wire this to
 * Bybit or any data source.
 *
 * Principles the real engine must honour when it lands:
 *   • Deterministic. Pure functions of their inputs. No LLM, no randomness, no I/O.
 *   • Only verified indicators are exposed: signed EMA7 slope + volume ratio (SPEC §1.4).
 *   • Same file, imported by both sides — a fix in the personal tool propagates here.
 *
 * Full contract (params, units, return shapes): see `scoring-engine.api.md`.
 * Signatures below are PROVISIONAL and may change when the real code is extracted.
 */

/**
 * Sentinel returned by every stub until the engine is extracted.
 * Truthy and obviously-not-a-number, so any premature use surfaces immediately
 * instead of silently flowing a bad value into a scan.
 * @type {{__todo: true, message: string}}
 */
export const TODO = Object.freeze({
  __todo: true,
  message:
    "scoring-engine not yet extracted from the personal tool — see scoring-engine.api.md (SPEC §6.1)",
});

/**
 * Signed EMA7 slope as a percentage. Positive = rising, negative = falling.
 * The one verified momentum indicator exposed to clients (SPEC §1.4).
 *
 * @param {number[]} closes - Ordered close prices (oldest → newest).
 * @returns {number} Signed slope percent. TODO — returns {@link TODO} sentinel.
 */
export function ema7Slope(closes) {
  void closes;
  return TODO;
}

/**
 * Deterministic score for one direction of one coin.
 *
 * @param {object} marketData - Candles + volume for the coin (shape TBD on extraction).
 * @param {"long"|"short"} direction - Trade direction to score.
 * @returns {number} Score (intended 0–100). TODO — returns {@link TODO} sentinel.
 */
export function scoreDirection(marketData, direction) {
  void marketData;
  void direction;
  return TODO;
}

/**
 * Reversal anchor used as the geometric basis for stop-loss placement (SPEC §6.1).
 *
 * @param {object} marketData - Candles for the coin (shape TBD on extraction).
 * @param {"long"|"short"} direction - Trade direction.
 * @returns {object} Anchor descriptor (e.g. { price, index }). TODO — returns {@link TODO} sentinel.
 */
export function computeReversalAnchor(marketData, direction) {
  void marketData;
  void direction;
  return TODO;
}

/**
 * Stop-loss price from entry + reversal anchor geometry.
 *
 * @param {number} entry - Entry price.
 * @param {object} anchor - Output of {@link computeReversalAnchor}.
 * @param {"long"|"short"} direction - Trade direction.
 * @returns {number} Stop-loss price. TODO — returns {@link TODO} sentinel.
 */
export function computeSL(entry, anchor, direction) {
  void entry;
  void anchor;
  void direction;
  return TODO;
}

/**
 * Take-profit price (and/or trailing basis) from entry + stop-loss geometry.
 *
 * @param {number} entry - Entry price.
 * @param {number} sl - Stop-loss price from {@link computeSL}.
 * @param {"long"|"short"} direction - Trade direction.
 * @returns {number} Take-profit price. TODO — returns {@link TODO} sentinel.
 */
export function computeTP(entry, sl, direction) {
  void entry;
  void sl;
  void direction;
  return TODO;
}
