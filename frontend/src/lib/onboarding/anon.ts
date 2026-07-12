// Anonymous session id for pre-signup funnel correlation (S0–S4). SSR-safe.
const KEY = "finaroda_onb_anon";

export function anonId(): string {
  if (typeof window === "undefined") return "ssr";
  try {
    let id = window.localStorage.getItem(KEY);
    if (!id) {
      const rand =
        typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : `a-${Math.abs(hashNow())}`;
      id = rand;
      window.localStorage.setItem(KEY, id);
    }
    return id;
  } catch {
    return "no-storage";
  }
}

// Fallback entropy when crypto.randomUUID is unavailable (older browsers).
function hashNow(): number {
  const s = `${performance.now()}-${Math.floor(performance.now() * 1000) % 997}`;
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return h;
}
