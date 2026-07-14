"use client";

// Stage 4 admin sections: Coupons (Stripe-native mirror) + Referrals (bindings + rewards).
// Admin-only endpoints (403 otherwise); every mutation is audited server-side.
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import { C } from "@/lib/onboarding/types";
import {
  couponIsRedeemable,
  formatCouponDiscount,
  type CouponMirror,
} from "@/lib/app/promotions";
import { formatAgorotIls } from "@/lib/app/billing";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";

/* eslint-disable @typescript-eslint/no-explicit-any */

function H({ title, note }: { title: string; note?: string }) {
  return <div style={{ font: `700 17px ${SANS}`, color: C.fg }}>{title} {note && <span style={{ font: `400 10px ${MONO}`, color: C.muted }}>· {note}</span>}</div>;
}
function Label({ text }: { text: string }) {
  return <span style={{ font: `600 8px ${MONO}`, letterSpacing: 1, color: C.muted }}>{text}</span>;
}
const ctl: React.CSSProperties = { background: C.bg, color: C.fg, border: `1px solid ${C.border}`, borderRadius: 6, padding: "8px 10px", font: `400 10px ${MONO}` };

export function CouponsAdmin() {
  const [rows, setRows] = useState<CouponMirror[]>([]);
  const [discountType, setDiscountType] = useState<"percent" | "fixed">("percent");
  const [code, setCode] = useState("");
  const [percentOff, setPercentOff] = useState("20");
  const [amountOff, setAmountOff] = useState("1000");
  const [maxRedemptions, setMaxRedemptions] = useState("");
  const [planRestriction, setPlanRestriction] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    const r = await api.adminListCoupons();
    if (r.ok && r.data) setRows((r.data as { coupons: CouponMirror[] }).coupons);
  }, []);
  useEffect(() => { void load(); }, [load]);

  async function create() {
    setErr(null);
    if (!code.trim()) { setErr("A code is required."); return; }
    const body: any = {
      code: code.trim(),
      discount_type: discountType,
      percent_off: discountType === "percent" ? Number(percentOff) : null,
      amount_off_agorot: discountType === "fixed" ? Number(amountOff) : null,
      max_redemptions: maxRedemptions ? Number(maxRedemptions) : null,
      plan_restriction: planRestriction || null,
      expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
    };
    const r = await api.adminCreateCoupon(body);
    if (!r.ok) { setErr(r.error?.message ?? "Create failed."); return; }
    setCode(""); setMaxRedemptions(""); setPlanRestriction(""); setExpiresAt("");
    await load();
  }

  async function deactivate(id: number) {
    await api.adminDeactivateCoupon(id);
    await load();
  }

  return (
    <div style={{ flex: 1, padding: "20px clamp(16px,4vw,24px)", display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
      <H title="Coupons" note="Stripe-native · first charge only" />

      {/* Create form */}
      <div style={{ background: C.panel, border: `1px solid rgba(233,238,243,.08)`, borderRadius: 10, padding: 16, display: "flex", flexDirection: "column", gap: 10 }}>
        <Label text="CREATE COUPON" />
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
          <input placeholder="CODE" value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} style={{ ...ctl, minWidth: 120 }} />
          <select value={discountType} onChange={(e) => setDiscountType(e.target.value as any)} style={ctl}>
            <option value="percent">PERCENT</option>
            <option value="fixed">FIXED (ILS)</option>
          </select>
          {discountType === "percent" ? (
            <label style={{ font: `400 8px ${MONO}`, color: C.muted }}>% OFF<input type="number" min={1} max={100} value={percentOff} onChange={(e) => setPercentOff(e.target.value)} style={{ ...ctl, width: 80, marginLeft: 4 }} /></label>
          ) : (
            <label style={{ font: `400 8px ${MONO}`, color: C.muted }}>AGOROT OFF<input type="number" min={1} value={amountOff} onChange={(e) => setAmountOff(e.target.value)} style={{ ...ctl, width: 100, marginLeft: 4 }} /></label>
          )}
          <label style={{ font: `400 8px ${MONO}`, color: C.muted }}>MAX USES<input type="number" min={1} placeholder="∞" value={maxRedemptions} onChange={(e) => setMaxRedemptions(e.target.value)} style={{ ...ctl, width: 80, marginLeft: 4 }} /></label>
          <select value={planRestriction} onChange={(e) => setPlanRestriction(e.target.value)} style={ctl}>
            <option value="">ANY PLAN</option>
            <option value="basic">BASIC ONLY</option>
            <option value="pro">PRO ONLY</option>
          </select>
          <label style={{ font: `400 8px ${MONO}`, color: C.muted }}>EXPIRES<input type="date" value={expiresAt} onChange={(e) => setExpiresAt(e.target.value)} style={{ ...ctl, marginLeft: 4 }} /></label>
          <button type="button" onClick={create} style={{ ...ctl, background: C.green, color: C.bg, border: "none", cursor: "pointer", fontWeight: 600 }}>CREATE</button>
        </div>
        {err && <span style={{ font: `400 9px ${MONO}`, color: C.red }}>{err}</span>}
        <span style={{ font: `400 8.5px/1.5 ${MONO}`, color: C.muted }}>Coupons apply to the first charge only (Stripe duration once). Deactivating stops new redemptions.</span>
      </div>

      {/* List */}
      <div style={{ overflowX: "auto", background: C.panel, border: `1px solid rgba(233,238,243,.08)`, borderRadius: 10 }}>
        <div style={{ minWidth: 720, font: `400 10px ${MONO}` }}>
          <div style={{ display: "grid", gridTemplateColumns: "1.1fr .9fr .7fr .8fr .8fr .8fr .7fr", padding: "10px 14px", borderBottom: `1px solid rgba(233,238,243,.08)`, fontWeight: 600, fontSize: 8, letterSpacing: 1, color: C.muted }}>
            <span>CODE</span><span>DISCOUNT</span><span>PLAN</span><span>USED</span><span>EXPIRES</span><span>STATE</span><span></span>
          </div>
          {rows.length === 0 && <div style={{ padding: 16, color: C.muted }}>No coupons yet.</div>}
          {rows.map((c) => (
            <div key={c.id} style={{ display: "grid", gridTemplateColumns: "1.1fr .9fr .7fr .8fr .8fr .8fr .7fr", padding: "11px 14px", borderBottom: `1px solid rgba(233,238,243,.05)`, alignItems: "center" }}>
              <span style={{ color: C.fg, fontWeight: 600 }}>{c.code}</span>
              <span style={{ color: C.green }}>{formatCouponDiscount(c.discount_type, c.percent_off, c.amount_off_agorot)}</span>
              <span style={{ color: C.muted }}>{c.plan_restriction ? c.plan_restriction.toUpperCase() : "ANY"}</span>
              <span style={{ color: C.fg }}>{c.redeemed_count}{c.max_redemptions != null ? ` / ${c.max_redemptions}` : ""}</span>
              <span style={{ color: C.muted }}>{c.expires_at ? String(c.expires_at).slice(0, 10) : "none"}</span>
              <span style={{ color: couponIsRedeemable(c) ? C.green : C.muted, fontWeight: 600 }}>{c.active ? (couponIsRedeemable(c) ? "ACTIVE" : "SPENT") : "OFF"}</span>
              <span>{c.active && <button type="button" onClick={() => deactivate(c.id)} style={{ background: "none", border: `1px solid rgba(224,88,79,.25)`, color: C.red, borderRadius: 6, padding: "5px 9px", font: `600 8px ${MONO}`, cursor: "pointer" }}>DEACTIVATE</button>}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function ReferralsAdmin() {
  const [rows, setRows] = useState<any[]>([]);
  const [counts, setCounts] = useState<any>({});
  const [banked, setBanked] = useState(0);
  const [note, setNote] = useState("");

  const load = useCallback(async () => {
    const r = await api.adminListReferrals();
    if (r.ok && r.data) {
      const d = r.data as any;
      setRows(d.referrals); setCounts(d.counts); setBanked(d.credits_banked);
    }
  }, []);
  useEffect(() => { void load(); }, [load]);

  async function voidReferral(id: number) {
    if (!note.trim()) { alert("An audit note is required to void a referral."); return; }
    await api.adminVoidReferral(id, note.trim());
    setNote("");
    await load();
  }

  return (
    <div style={{ flex: 1, padding: "20px clamp(16px,4vw,24px)", display: "flex", flexDirection: "column", gap: 12, minWidth: 0 }}>
      <H title="Referrals" note={`${counts.rewarded ?? 0} rewarded · ${banked} credits banked`} />
      <input placeholder="audit note (required to void)" value={note} onChange={(e) => setNote(e.target.value)} style={{ ...ctl, maxWidth: 320 }} />
      <div style={{ overflowX: "auto", background: C.panel, border: `1px solid rgba(233,238,243,.08)`, borderRadius: 10 }}>
        <div style={{ minWidth: 760, font: `400 10px ${MONO}` }}>
          <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1.3fr .8fr 1fr .9fr .7fr", padding: "10px 14px", borderBottom: `1px solid rgba(233,238,243,.08)`, fontWeight: 600, fontSize: 8, letterSpacing: 1, color: C.muted }}>
            <span>REFERRER</span><span>REFERRED</span><span>STATUS</span><span>REWARD</span><span>WHEN</span><span></span>
          </div>
          {rows.length === 0 && <div style={{ padding: 16, color: C.muted }}>No referrals yet.</div>}
          {rows.map((r) => (
            <div key={r.id} style={{ display: "grid", gridTemplateColumns: "1.3fr 1.3fr .8fr 1fr .9fr .7fr", padding: "11px 14px", borderBottom: `1px solid rgba(233,238,243,.05)`, alignItems: "center" }}>
              <span style={{ color: C.fg, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.referrer_email}</span>
              <span style={{ color: C.muted, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.referred_email}</span>
              <span style={{ color: r.status === "rewarded" ? C.green : r.status === "void" ? C.red : C.muted, fontWeight: 600 }}>{String(r.status).toUpperCase()}</span>
              <span style={{ color: C.fg }}>{r.reward_type ? (r.reward_type === "banked" ? "BANKED" : formatAgorotIls(r.reward_amount_agorot ?? 0)) : "none"}</span>
              <span style={{ color: C.muted }}>{r.reward_granted_at ? String(r.reward_granted_at).slice(0, 10) : String(r.created_at).slice(0, 10)}</span>
              <span>{r.status !== "void" && <button type="button" onClick={() => voidReferral(r.id)} style={{ background: "none", border: `1px solid rgba(224,88,79,.25)`, color: C.red, borderRadius: 6, padding: "5px 9px", font: `600 8px ${MONO}`, cursor: "pointer" }}>VOID</button>}</span>
            </div>
          ))}
        </div>
      </div>
      <span style={{ font: `400 8.5px/1.5 ${MONO}`, color: C.muted }}>Voiding removes a not-yet-applied banked credit, or posts a compensating balance transaction for an applied one. Every void is audited.</span>
    </div>
  );
}
