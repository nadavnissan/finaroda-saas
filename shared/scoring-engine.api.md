# `scoring-engine.js` — API contract (PLACEHOLDER)

> ⚠️ **Status: awaiting extraction from the personal tool.** The functions below are
> signature stubs only; each returns the `TODO` sentinel. The real, verified logic
> lives inside the compiled React of the personal tool and will be supplied by Nadav.
> **Do not invent logic. Do not wire to Bybit or any data source.** (SPEC §6.1)

## Purpose

The single shared calculation brain — pure math, zero UI — imported by **both** the
personal tool (browser, `<script type="module">`) and the SaaS scan core (Next.js,
client-side). A fix in the personal tool propagates here, then to the SaaS
(eventually as a shared npm package). SPEC §6.1, §12 decision 7.

## Invariants the real engine must honour

| # | Invariant |
|---|-----------|
| 1 | **Deterministic.** Pure functions of inputs. No LLM, no randomness, no I/O, no time. |
| 2 | **Verified indicators only** are exposed to clients: signed EMA7 slope + volume ratio (SPEC §1.4). No funding/OI. |
| 3 | **Shared, single source.** Same file both sides — never fork the math. |
| 4 | **Analysis, not advice.** Outputs a score + levels; it does not decide entry. |

## Functions

> Signatures are **provisional** — final params/return shapes are fixed when the real
> code is extracted. `TODO` = `{ __todo: true, message }` (frozen), returned by every stub.

### `ema7Slope(closes: number[]): number`
Signed EMA7 slope, in percent. Positive = rising, negative = falling.
- **params** — `closes`: ordered close prices (oldest → newest).
- **returns** — signed slope %. *(stub → `TODO`)*

### `scoreDirection(marketData: object, direction: "long"|"short"): number`
Deterministic score for one direction of one coin.
- **params** — `marketData`: candles + volume (shape TBD); `direction`: `"long"|"short"`.
- **returns** — score, intended range 0–100. *(stub → `TODO`)*

### `computeReversalAnchor(marketData: object, direction: "long"|"short"): object`
Reversal anchor used as the geometric basis for the stop-loss (SPEC §6.1).
- **returns** — anchor descriptor, e.g. `{ price, index }`. *(stub → `TODO`)*

### `computeSL(entry: number, anchor: object, direction: "long"|"short"): number`
Stop-loss price from entry + reversal-anchor geometry.
- **returns** — stop-loss price. *(stub → `TODO`)*

### `computeTP(entry: number, sl: number, direction: "long"|"short"): number`
Take-profit price (and/or trailing basis) from entry + stop-loss geometry.
- **returns** — take-profit price. *(stub → `TODO`)*

## Consumers (future)

- **Personal tool** — extraction source; keeps running locally as the research lab.
- **SaaS scan core (P2)** — imports this module client-side; every scan press pulls
  fresh Bybit data *in the SaaS*, not here, and passes it into these pure functions.

## Extraction checklist (when Nadav provides the real code)

1. Replace each stub body with the extracted pure function; drop the `TODO` returns.
2. Lock the exact param/return shapes here and in the JSDoc.
3. Add unit tests with known-good vectors from the personal tool.
4. Bump the version in `shared/package.json`.
