// scorer.js — FINARODA score engine (scoreDirection + deps), VERBATIM from v25.80.
// Byte-faithful; same code as the personal tool → same scores. Default profile: momentum.
import { calcEMA, calcRSI, calcATR, calcADX } from './scoring-engine.js';

// ---- priceDecimals (verbatim v25.80, 358-366) ----
function priceDecimals(n) {
  const a = Math.abs(Number(n) || 0);
  if (a >= 1000) return 1;
  if (a >= 100) return 2;
  if (a >= 1) return 3;
  if (a >= 0.1) return 4;
  if (a >= 0.01) return 5;
  return 6;
}

// ---- roundPrice (verbatim v25.80, 367-369) ----
function roundPrice(n) {
  return Number(Number(n).toFixed(priceDecimals(n)));
}

// ---- fmtPrice (verbatim v25.80, 370-375) ----
function fmtPrice(n) {
  return Number(n).toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: priceDecimals(n)
  });
}

// ---- computeAnchoredVwap (verbatim v25.80, 466-487) ----
function computeAnchoredVwap(h, l, c, v, lookbackDays) {
  if (!h || !l || !c || !v || c.length < 30) return null;
  var lb = Math.min(lookbackDays || 365, c.length);
  var start = c.length - lb;
  // מצא את אינדקס התחתית הגדולה בחלון
  var loIdx = start;
  for (var j = start; j < c.length; j++) { if (l[j] < l[loIdx]) loIdx = j; }
  // VWAP צובר מהתחתית עד היום (typical price = (h+l+c)/3)
  var pv = 0, vol = 0;
  for (var k = loIdx; k < c.length; k++) {
    var tp = (h[k] + l[k] + c[k]) / 3;
    pv += tp * (v[k] || 0); vol += (v[k] || 0);
  }
  if (vol <= 0) return null;
  var vwap = pv / vol;
  var price = c[c.length - 1];
  var gapPct = Math.round((price - vwap) / vwap * 1000) / 10;
  // טריגר (כמו בבקטסט): הנר נגע ב-VWAP (≤1.5%) וסגר מעליו
  var touched = l[c.length - 1] <= vwap * 1.015 && l[c.length - 1] >= vwap * 0.985;
  var closedAbove = price > vwap;
  return { vwap: Math.round(vwap * 100) / 100, gapPct: gapPct, anchorLowIdx: loIdx, triggerLong: touched && closedAbove };
}

// ---- computeADL (verbatim v25.80, 490-506) ----
function computeADL(h, l, c, v, lookback) {
  if (!h || !l || !c || !v || h.length < 2) return null;
  var n = h.length;
  var adlSeries = [];
  var adl = 0;
  for (var i = 0; i < n; i++) {
    var rng = h[i] - l[i];
    var mfm = rng > 0 ? ((c[i] - l[i]) - (h[i] - c[i])) / rng : 0;
    adl += mfm * (v[i] || 0);
    adlSeries.push(adl);
  }
  var lb = Math.min(lookback || 20, n - 1);
  var prev = adlSeries[n - 1 - lb];
  var curr = adlSeries[n - 1];
  var trend = curr > prev ? 'up' : curr < prev ? 'down' : 'flat';
  return { value: Math.round(curr), trendLb: lb, trend: trend, changePct: prev !== 0 ? Math.round((curr - prev) / Math.abs(prev) * 1000) / 10 : null };
}

// ---- detectSweep (verbatim v25.80, 509-522) ----
function detectSweep(h, l, c, level, dir, lookback) {
  if (!h || !l || !c || level == null || h.length < 3) return null;
  var n = h.length;
  var lb = Math.min(lookback || 10, n - 1);
  for (var i = n - 1; i >= n - lb; i--) {
    if (dir === 'long') {
      // sweep של רצפה: ה-low ירד מתחת ל-level אך ה-close חזר מעל
      if (l[i] < level && c[i] > level) return { swept: true, candlesAgo: n - 1 - i, low: l[i] };
    } else {
      if (h[i] > level && c[i] < level) return { swept: true, candlesAgo: n - 1 - i, high: h[i] };
    }
  }
  return { swept: false, candlesAgo: null };
}

// ---- computeSlTp (verbatim v25.80, 634-665) ----
function computeSlTp(dir, price, ema14, ema28, atr, opt) {
  opt = opt || {};
  const slAtrMult = opt.slAtrMult ?? 1.5;
  const tp1Mult = opt.tp1Mult ?? 1.5;
  const tp2Mult = opt.tp2Mult ?? 3.0;
  const slMaxPct = opt.slMaxPct ?? 2.0;
  const slMinPct = opt.slMinPct ?? 0.5;
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  let sl, slPct;
  if (dir === 'long') {
    const slRaw = Math.min(ema14, ema28) - atr * slAtrMult; // מבני, אמור להיות מתחת למחיר
    slPct = clamp((price - slRaw) / price * 100, slMinPct, slMaxPct);
    sl = price * (1 - slPct / 100); // תמיד מתחת למחיר
  } else {
    const slRaw = Math.max(ema14, ema28) + atr * slAtrMult; // מבני, אמור להיות מעל המחיר
    slPct = clamp((slRaw - price) / price * 100, slMinPct, slMaxPct);
    sl = price * (1 + slPct / 100); // תמיד מעל המחיר
  }
  const risk = Math.abs(price - sl);
  const tp1 = dir === 'long' ? price + risk * tp1Mult : price - risk * tp1Mult;
  const tp2 = dir === 'long' ? price + risk * tp2Mult : price - risk * tp2Mult;
  const tp1Pct = Math.abs(tp1 - price) / price * 100;
  const tp2Pct = Math.abs(tp2 - price) / price * 100;
  return {
    sl,
    tp1,
    tp2,
    slPct,
    tp1Pct,
    tp2Pct
  };
}

// ---- DEFAULT_RISK (verbatim v25.80, 842-855) ----
const DEFAULT_RISK = {
  accountBalance: 10000,
  riskTolerance: 1.5,
  slAtrMult: 1.5,
  tp1Mult: 1.5,
  tp2Mult: 3.0,
  slMaxPct: 2.0,
  // תקרת SL באחוז — אם ATR×mult רחב מזה, ה-SL מוגבל לתקרה (R הדוק → TP מושג)
  slMinPct: 0.5,
  // רצפת SL באחוז — מבטיח SL בצד הנכון של המחיר ולא הדוק/אפס
  defaultLeverage: 10,
  // ברירת מחדל למנוף — ניתן לשינוי לכל פוזיציה
  beThreshold: 50 // אחוז ההתקדמות ל-TP1 שמפעיל המלצת BE move (30/50/70 = אגרסיבי/סטנדרטי/שמרני)
};

// ---- TREND_MGMT_RISK (verbatim v25.80, 858-864) ----
const TREND_MGMT_RISK = {
  defaultLeverage: 3,
  slMaxPct: 15,
  slAtrMult: 4,
  trailActivationPct: 3,
  trailCallbackPct: 5
};

// ---- DEFAULT_CALIBRATION (verbatim v25.80, 865-998) ----
const DEFAULT_CALIBRATION = {
  // Basic
  rsiLongMin: 55,
  rsiShortMax: 45,
  rsiExtremePenalty: true,
  rsiOversoldLimit: 20,
  rsiOverboughtLimit: 80,
  extremePenaltyAmount: 15,
  distThresholdPct: 2.0,
  executeCutoff: 90,
  waitCutoff: 50,
  // Filter A: HTF Bias (weekly)
  htfBiasEnabled: true,
  htfBiasWeight: 10,
  // Filter B: Liquidity (swing high/low)
  liquidityEnabled: true,
  liquidityWeight: 10,
  liquidityNearPct: 3.0,
  // אזהרת רדיפה — אם המהלך כבר התקדם מעל X% מטווח ה-swing → כניסה מאוחרת
  chaseWarnPct: 60,
  moveDoneLookback: 30,
  // חלון נרות יומיים למדידת moveDone (טווח דומיננטי high/low)
  // ===== כניסת המשך מגמה (entryMode='continuation') =====
  // 'pullback' (ברירת מחדל) = הטכניקה הקיימת (קרבה ל-EMA7, מעניש מתוח).
  // 'continuation' = כניסה למהלך שכבר רץ עם מומנטום; לא דורש קרבה ל-EMA7,
  // אבל חוסם EXECUTE מחוץ לחלון moveDone, וחוסם RSI קיצוני (מהלך מותש).
  entryMode: 'pullback',
  contMoveDoneMin: 20,
  // מתחת לזה = מוקדם מדי (ייתכן פולס)
  contMoveDoneMax: 60,
  // מעל זה = מותש (רדיפה)
  momMoveDoneMin: 60,
  // מומנטום: מינ' מהלך שנחשב "רץ" (entryMode='momentum')
  // ===== Trailing Stop (רק מומנטום) — הנחיה להזנה ידנית ב-Bybit =====
  trailActivationPct: 1.5,
  // אחוז רווח שמפעיל את ה-trailing
  trailCallbackPct: 0.8,
  // מרווח ה-trailing (callback) באחוזים
  // ===== v25.23: שכבת הגנה (פרופיל "מומנטום מוגן") — קונפיגורבילי בהגדרות =====
  // שומר אחרי הציון: EXECUTE רק אם ER≥סף וגם התרחבות תנודתיות. אינו משנה את הציון.
  defenseGate: false,
  // כבוי כברירת מחדל (רק הפרופיל המוגן מדליק)
  defenseErThreshold: 0.4,
  // סף Efficiency Ratio (תכליתיות כיוונית)
  defenseErPeriod: 10,
  // חלון ER
  defenseRequireExpansion: true,
  // דורש התרחבות תנודתיות (BB מחוץ לקלטנר)
  // Filter C: Volume on Wick
  volumeOnWickEnabled: true,
  volumeOnWickMultiplier: 1.5,
  volumeOnWickBonus: 5,
  // Filter D: Funding Bias
  fundingBiasEnabled: true,
  fundingBiasThreshold: 0.02,
  fundingBiasWeight: 10,
  // Filter E: Market Isolation
  isolationEnabled: true,
  isolationStdThreshold: 1.5,
  isolationWeight: 5,
  // ===== Quality Checklist (חלק A — בדיקות אוטומטיות) — ספים מכויילים =====
  qaEma200MaxPct: 3.0,
  // A2: מרחק מקסימלי מ-EMA200 שנחשב "הגיוני"
  qaRsiMin: 25,
  qaRsiMax: 75,
  // A3: טווח RSI לא-קיצוני
  qaSwingNearPct: 3.0,
  // A5: מרחק מקסימלי מ-swing level בכיוון הכניסה (R:R טוב)
  qaVolumeMinRatio: 1.0,
  // A6: יחס וולום מינימלי על הפתיל
  qaConsensusMin: 2,
  // A7: מינימום פרופילים ב-EXECUTE
  qaWarnMaxFails: 3,
  // סף כשלים בחלק A שמפעיל תג אזהרה בכרטיס (שילוב רך)
  // ===== מנגנון ציון מאוחד — בדיקות SMC עם משקל + דגל חובה (ניתן לכיול) =====
  // משקל שווה לכולן כברירת מחדל. required=true → בדיקת חובה (נכשלה = פסול, NO TRADE).
  // הציון = אחוז משוקלל של הבדיקות שעברו. הניהול והשאלון האישי אינם חלק מהמנגנון הזה.
  checkConfig: {
    macro: {
      weight: 10,
      required: true
    },
    // מאקרו (EMA200) — כיוון
    htf: {
      weight: 10,
      required: true
    },
    // HTF bias שבועי — כיוון
    ema7: {
      weight: 10,
      required: false
    },
    // קרבה ל-EMA7 (תזמון כניסה)
    fvg: {
      weight: 10,
      required: false
    },
    // FVG בכיוון
    wick: {
      weight: 10,
      required: false
    },
    // דחיית פתיל
    rsiMom: {
      weight: 10,
      required: false
    },
    // RSI momentum
    ltf: {
      weight: 10,
      required: false
    },
    // LTF cross
    liquidity: {
      weight: 10,
      required: false
    },
    // קרבה ל-swing
    volume: {
      weight: 10,
      required: false
    },
    // Volume על הפתיל
    funding: {
      weight: 10,
      required: false
    },
    // Funding bias
    isolation: {
      weight: 10,
      required: false
    } // Market isolation
  }
};

// ---- classifyRegime (verbatim v25.80, 1496-1518) ----
const classifyRegime = adxObj => {
  if (!adxObj || adxObj.adx == null) return {
    regime: 'unknown',
    label: 'משטר?',
    color: 'slate'
  };
  const a = adxObj.adx;
  if (a < 20) return {
    regime: 'range',
    label: `דשדוש · ADX ${a}`,
    color: 'amber'
  };
  if (a < 25) return {
    regime: 'transition',
    label: `מעבר · ADX ${a}`,
    color: 'sky'
  };
  return {
    regime: 'trend',
    label: `טרנד · ADX ${a}`,
    color: 'emerald'
  };
};

// ---- detectSMC (verbatim v25.80, 1519-1527) ----
const detectSMC = (highs, lows, dir) => {
  const len = highs.length;
  if (len < 4) return false;
  for (let i = Math.max(2, len - 10); i < len; i++) {
    if (dir === 'long' && lows[i] > highs[i - 2]) return true;
    if (dir === 'short' && highs[i] < lows[i - 2]) return true;
  }
  return false;
};

// ---- detectWickRejection (verbatim v25.80, 1528-1557) ----
const detectWickRejection = (highs, lows, closes, opens, volumes, dir) => {
  const len = highs.length;
  let maxRatio = 0,
    maxIdx = -1;
  for (let i = Math.max(0, len - 3); i < len; i++) {
    const range = highs[i] - lows[i];
    if (range === 0) continue;
    const wickLen = dir === 'long' ? Math.min(opens[i], closes[i]) - lows[i] : highs[i] - Math.max(opens[i], closes[i]);
    const ratio = wickLen / range * 100;
    if (ratio > maxRatio) {
      maxRatio = ratio;
      maxIdx = i;
    }
  }
  const hasWick = maxRatio >= 65;
  // Volume on wick check
  let volumeRatio = 0;
  if (hasWick && volumes && maxIdx >= 0) {
    const lookback = 14;
    const start = Math.max(0, len - lookback - 1);
    const recent = volumes.slice(start, len - 1);
    const avg = recent.reduce((a, b) => a + b, 0) / (recent.length || 1);
    volumeRatio = avg > 0 ? volumes[maxIdx] / avg : 0;
  }
  return {
    hasWick,
    maxRatio,
    volumeRatio
  };
};

// ---- findRecentSwingLevels (verbatim v25.80, 1560-1586) ----
const findRecentSwingLevels = (highs, lows, lookback = 3, scanRange = 30) => {
  let swingHigh = null,
    swingLow = null;
  const start = Math.max(lookback, highs.length - scanRange);
  const end = highs.length - lookback;
  for (let i = end - 1; i >= start; i--) {
    let isHigh = true,
      isLow = true;
    for (let j = 1; j <= lookback && (isHigh || isLow); j++) {
      if (highs[i] <= highs[i - j] || highs[i] <= highs[i + j]) isHigh = false;
      if (lows[i] >= lows[i - j] || lows[i] >= lows[i + j]) isLow = false;
    }
    if (isHigh && swingHigh === null) swingHigh = {
      idx: i,
      value: highs[i]
    };
    if (isLow && swingLow === null) swingLow = {
      idx: i,
      value: lows[i]
    };
    if (swingHigh && swingLow) break;
  }
  return {
    swingHigh,
    swingLow
  };
};

// ---- getWeeklyBias (verbatim v25.80, 1589-1596) ----
const getWeeklyBias = (weeklyCloses, currentPrice) => {
  if (!weeklyCloses || weeklyCloses.length < 50) return 'neutral';
  const wEma20 = calcEMA(weeklyCloses, 20);
  const wEma50 = calcEMA(weeklyCloses, 50);
  if (currentPrice > wEma20 && currentPrice > wEma50 && wEma20 > wEma50) return 'bullish';
  if (currentPrice < wEma20 && currentPrice < wEma50 && wEma20 < wEma50) return 'bearish';
  return 'neutral';
};

// ---- calcEfficiencyRatio (verbatim v25.80, 2397-2405) ----
const calcEfficiencyRatio = (closes, period = 10) => {
  if (!closes || closes.length < period + 1) return null;
  const s = closes.slice(-(period + 1));
  const change = Math.abs(s[s.length - 1] - s[0]);
  let vol = 0;
  for (let i = 1; i < s.length; i++) vol += Math.abs(s[i] - s[i - 1]);
  if (vol === 0) return null;
  return change / vol; // 0..1
};

// ---- calcVolExpansion (verbatim v25.80, 2406-2426) ----
const calcVolExpansion = (highs, lows, closes, period = 20, bbMult = 2, kcMult = 1.5) => {
  if (!closes || closes.length < period + 1) return null;
  const cl = closes.slice(-period);
  const mean = cl.reduce((a, b) => a + b, 0) / period;
  const sd = Math.sqrt(cl.reduce((acc, x) => acc + (x - mean) ** 2, 0) / period);
  const bbUpper = mean + bbMult * sd,
    bbLower = mean - bbMult * sd;
  const ema = calcEMA(closes, period);
  const atr = calcATR(highs, lows, closes, period);
  if (atr == null) return null;
  const kcUpper = ema + kcMult * atr,
    kcLower = ema - kcMult * atr;
  const expanded = bbUpper > kcUpper || bbLower < kcLower; // BB מחוץ לקלטנר = התרחבות
  return {
    expanded,
    bbUpper,
    bbLower,
    kcUpper,
    kcLower
  };
};

// ---- scoreDirection (verbatim v25.80, 2429-2940) ----
const scoreDirection = (raw, dir, riskParams, cal, marketContext, coin) => {
  const {
    c: cRaw,
    h: hRaw,
    l: lRaw,
    o: oRaw,
    v: vRaw
  } = raw.daily;
  // ===== v25.38: ניקוד על נר יומי סגור בלבד =====
  // הנר היומי האחרון מ-Bybit הוא הנר *החי* (לא נסגר עד 00:00 UTC). שימוש בו
  // גרם לציון לרצד מסריקה לסריקה — אנטי-תזה לסווינג. מעתה כל ה-checks (EMA/RSI/
  // trend/dist/slope/moveDone/swing/weekly) מחושבים על נרות סגורים בלבד, כך
  // שהציון קבוע לאורך כל היום ומשתנה רק כשנר יומי חדש נסגר. המחיר החי (raw.price)
  // נשמר אך ורק ל-Entry/SL/TP/positionSize — ההחלטה יציבה, הכניסה עדכנית.
  const closedTrim = cRaw.length > 30 ? 1 : 0; // הגנה: אל תזרוק אם מעט נתונים
  const c = cRaw.slice(0, cRaw.length - closedTrim);
  const h = hRaw.slice(0, hRaw.length - closedTrim);
  const l = lRaw.slice(0, lRaw.length - closedTrim);
  const o = oRaw ? oRaw.slice(0, oRaw.length - closedTrim) : [];
  const v = vRaw.slice(0, vRaw.length - closedTrim);
  const closedClose = c[c.length - 1]; // מחיר הסגירה האחרון (לבדיקות trend/dist)
  const {
    c: hc,
    h: hh,
    l: hl,
    o: ho,
    v: hv
  } = raw.hourly;
  const price = raw.price,
    funding = raw.funding;
  const ema7 = calcEMA(c, 7),
    ema14 = calcEMA(c, 14),
    ema28 = calcEMA(c, 28),
    ema200 = calcEMA(c, 200);
  const ema7Slope = (() => {
    if (!c || c.length < 12) return null;
    const e7now = calcEMA(c, 7);
    const e7prev = calcEMA(c.slice(0, c.length - 5), 7);
    if (!e7prev) return null;
    // v25.77: שיפוע *עם סימן* (חיובי=עולה, שלילי=יורד) — תואם להגדרת המחקר ש-fam_mtf השתמש בה.
    // צרכני-עוצמה (computeSlopeFlag/computeEmaPanel) מפעילים Math.abs() בעצמם.
    return (e7now - e7prev) / e7prev * 100;
  })();
  // v25.39: שיפועי EMA14/28 (לפאנל EMA — תצוגה בלבד). על נר סגור כמו ema7Slope.
  const ema14Slope = (() => {
    if (!c || c.length < 19) return null;
    const now = calcEMA(c, 14);
    const prev = calcEMA(c.slice(0, c.length - 5), 14);
    if (!prev) return null;
    return (now - prev) / prev * 100;
  })();
  const ema28Slope = (() => {
    if (!c || c.length < 33) return null;
    const now = calcEMA(c, 28);
    const prev = calcEMA(c.slice(0, c.length - 5), 28);
    if (!prev) return null;
    return (now - prev) / prev * 100;
  })();
  const rsi = calcRSI(c, 6),
    atr = calcATR(h, l, c, 14);
  const adxObj = calcADX(h, l, c, 14);
  const regimeInfo = classifyRegime(adxObj);
  // v25.23: שכבת הגנה — מחושב תמיד, משמש רק אם cal.defenseGate
  const effRatio = calcEfficiencyRatio(c, cal.defenseErPeriod ?? 10);
  const volExp = calcVolExpansion(h, l, c, 20, 2, 1.5);
  // v25.41 FIX: wick + ltf חושבו על הנר השעתי החי → התהפכו כל דקה (256 קפיצות בלוגר).
  // מעבר לנר היומי הסגור (כמו כל שאר הצ'קים מ-v25.38) → יציב לאורך היום.
  // ltf עכשיו = הצטלבות EMA7/EMA14 יומית (במקום שעתית), על נרות סגורים.
  const dem7 = calcEMA(c, 7),
    dem14 = calcEMA(c, 14);
  const ltfCross = dem7 > dem14 ? 'bullish' : dem7 < dem14 ? 'bearish' : 'none';
  const hasFvg = detectSMC(h, l, dir);
  // wick עכשיו = דחיית פתיל על הנר היומי הסגור (במקום שעתי חי)
  const rejH = detectWickRejection(h, l, c, o, v, dir);
  const swing = findRecentSwingLevels(h, l, 3, 30);
  // v25.38: weeklyBias על מחיר הסגירה היומי הסגור (לא המחיר החי)
  const weeklyBias = raw.weekly ? getWeeklyBias(raw.weekly.c, closedClose) : 'neutral';
  // v25.50: מדדים שבועיים מלאים (RSI, swing, EMA20/50) — מאותם נרות שבועיים שכבר נמשכים
  const weeklyRsi = raw.weekly && raw.weekly.c && raw.weekly.c.length >= 15 ? calcRSI(raw.weekly.c, 14) : null;
  const weeklyEma20 = raw.weekly && raw.weekly.c && raw.weekly.c.length >= 20 ? calcEMA(raw.weekly.c, 20) : null;
  const weeklyEma50 = raw.weekly && raw.weekly.c && raw.weekly.c.length >= 50 ? calcEMA(raw.weekly.c, 50) : null;
  const weeklySwing = raw.weekly && raw.weekly.h && raw.weekly.l ? findRecentSwingLevels(raw.weekly.h, raw.weekly.l, 3, 30) : null;
  // v25.51: ADL (אקומולציה/חלוקה) ו-sweep — מ-OHLCV יומי
  const adl = raw.daily ? computeADL(raw.daily.h, raw.daily.l, raw.daily.c, raw.daily.v, 20) : null;
  const vwapAnchored = raw.daily ? computeAnchoredVwap(raw.daily.h, raw.daily.l, raw.daily.c, raw.daily.v, 365) : null;
  const sweepFloor = swing.swingLow ? swing.swingLow.value : null;
  const sweepCeil = swing.swingHigh ? swing.swingHigh.value : null;
  const sweepDn = raw.daily && sweepFloor != null ? detectSweep(raw.daily.h, raw.daily.l, raw.daily.c, sweepFloor, 'long', 10) : null;
  const sweepUp = raw.daily && sweepCeil != null ? detectSweep(raw.daily.h, raw.daily.l, raw.daily.c, sweepCeil, 'short', 10) : null;

  // ===== מנגנון ציון מאוחד — בדיקות SMC עם משקל + דגל חובה =====
  const cfg = cal.checkConfig || {};
  const cc = (k, def) => cfg[k] || def || {
    weight: 10,
    required: false
  };
  // v25.38: trend/dist על מחיר הסגירה הסגור — ציון יציב לאורך היום
  const trend = closedClose > ema200 ? 'bullish' : 'bearish';
  const dist = Math.abs(closedClose - ema7) / ema7;
  const distThresh = cal.distThresholdPct / 100;

  // חישוב pass לכל בדיקה
  const macroPass = dir === 'long' && trend === 'bullish' || dir === 'short' && trend === 'bearish';
  const htfPass = weeklyBias !== 'neutral' && (dir === 'long' && weeklyBias === 'bullish' || dir === 'short' && weeklyBias === 'bearish');
  const ema7Pass = dist < distThresh;
  const fvgPass = hasFvg === true;
  const wickPass = rejH.hasWick === true;
  const rsiMomPass = dir === 'long' && rsi > cal.rsiLongMin || dir === 'short' && rsi < cal.rsiShortMax;
  const ltfPass = dir === 'long' && ltfCross === 'bullish' || dir === 'short' && ltfCross === 'bearish';
  let liqPass = false;
  if (dir === 'long' && swing.swingLow) {
    const d = (closedClose - swing.swingLow.value) / swing.swingLow.value * 100;
    liqPass = d >= 0 && d < cal.liquidityNearPct;
  }
  if (dir === 'short' && swing.swingHigh) {
    const d = (swing.swingHigh.value - closedClose) / closedClose * 100;
    liqPass = d >= 0 && d < cal.liquidityNearPct;
  }

  // ===== אזהרת רדיפה — כמה מהמהלך כבר קרה (origin → target) =====
  // 0% = המהלך רק מתחיל (כניסה מוקדמת/טובה), 100% = המהלך הושלם (כניסה מאוחרת/רדיפה).
  // FIX moveDone: נמדד מול הגבוה/הנמוך הקיצוני בחלון (origin/target אמיתי של המהלך),
  //   ולא מול ה-swing הפרקטלי הקרוב — שגרם לקריאת 0% שגויה על דשדוש בתחתית/בפסגה
  //   אחרי מהלך גמור (תועד פעמיים על BNB). ה-swing הפרקטלי נשאר ל-Liquidity בלבד.
  let moveDonePct = null,
    chaseWarning = false,
    moveDoneHigh = null,
    moveDoneLow = null;
  {
    const mdLook = Math.max(5, Math.round(cal.moveDoneLookback ?? 30));
    const hSlice = h.slice(-mdLook),
      lSlice = l.slice(-mdLook);
    if (hSlice.length && lSlice.length) {
      const rangeHigh = Math.max(...hSlice),
        rangeLow = Math.min(...lSlice);
      moveDoneHigh = rangeHigh;
      moveDoneLow = rangeLow;
      const range = rangeHigh - rangeLow;
      if (range > 0) {
        moveDonePct = dir === 'short' ? (rangeHigh - closedClose) / range * 100 // short: origin=הגבוה הקיצוני, target=הנמוך
        : (closedClose - rangeLow) / range * 100; // long: origin=הנמוך הקיצוני, target=הגבוה
        moveDonePct = Math.max(0, Math.min(100, moveDonePct));
        chaseWarning = moveDonePct >= (cal.chaseWarnPct ?? 60);
      }
    }
  }
  const volPass = rejH.hasWick && rejH.volumeRatio >= cal.volumeOnWickMultiplier;
  let fundPass = false;
  {
    const t = cal.fundingBiasThreshold;
    fundPass = dir === 'short' && funding > t || dir === 'long' && funding < -t;
  }
  let isolationZ = 0,
    isoPass = false;
  if (marketContext && marketContext.coinChanges[coin] !== undefined && marketContext.stdChange > 0) {
    isolationZ = (marketContext.coinChanges[coin] - marketContext.meanChange) / marketContext.stdChange;
    if (Math.abs(isolationZ) >= cal.isolationStdThreshold) {
      isoPass = dir === 'short' && isolationZ < 0 || dir === 'long' && isolationZ > 0;
    }
  }

  // רשימת הבדיקות עם משקל + חובה (מהכיול)
  const checkList = [{
    key: 'macro',
    label: 'מאקרו (EMA200)',
    pass: macroPass,
    ...cc('macro')
  }, {
    key: 'htf',
    label: 'HTF bias שבועי',
    pass: htfPass,
    ...cc('htf')
  }, {
    key: 'ema7',
    label: 'קרבה ל-EMA7',
    pass: ema7Pass,
    ...cc('ema7')
  }, {
    key: 'fvg',
    label: 'FVG בכיוון',
    pass: fvgPass,
    ...cc('fvg')
  }, {
    key: 'wick',
    label: 'דחיית פתיל (Wick)',
    pass: wickPass,
    ...cc('wick')
  }, {
    key: 'rsiMom',
    label: 'RSI momentum',
    pass: rsiMomPass,
    ...cc('rsiMom')
  }, {
    key: 'ltf',
    label: 'LTF cross',
    pass: ltfPass,
    ...cc('ltf')
  }, {
    key: 'liquidity',
    label: 'Liquidity (swing)',
    pass: liqPass,
    ...cc('liquidity')
  }, {
    key: 'volume',
    label: 'Volume על הפתיל',
    pass: volPass,
    ...cc('volume')
  }, {
    key: 'funding',
    label: 'Funding bias',
    pass: fundPass,
    ...cc('funding')
  }, {
    key: 'isolation',
    label: 'Market isolation',
    pass: isoPass,
    ...cc('isolation')
  }];

  // ציון = אחוז משוקלל של הבדיקות שעברו
  const totalWeight = checkList.reduce((s, c) => s + c.weight, 0) || 1;
  const earnedWeight = checkList.reduce((s, c) => s + (c.pass ? c.weight : 0), 0);
  let score = Math.round(earnedWeight / totalWeight * 100);

  // בדיקות חובה שנכשלו → פסול
  const failedRequired = checkList.filter(c => c.required && !c.pass);
  const blocked = failedRequired.length > 0;

  // קנס RSI קיצוני (נשאר — מוריד מהציון)
  let penalized = false;
  if (cal.rsiExtremePenalty) {
    if (dir === 'short' && rsi < cal.rsiOversoldLimit || dir === 'long' && rsi > cal.rsiOverboughtLimit) {
      penalized = true;
    }
  }

  // breakdown טקסטואלי (לתאימות)
  const breakdown = checkList.filter(c => c.pass).map(c => `${c.label}: +${c.weight}${c.required ? ' (חובה)' : ''}`);

  // מבנה רכיבים לתצוגה (נוכחי/מקסימלי + חובה)
  const scoreComponents = checkList.map(c => ({
    label: c.label,
    got: c.pass ? c.weight : 0,
    max: c.weight,
    required: c.required,
    pass: c.pass
  }));
  const scoreMaxPossible = totalWeight;
  const penaltyGot = 0;
  const {
    slAtrMult,
    tp1Mult,
    tp2Mult,
    accountBalance,
    riskTolerance
  } = riskParams;
  const slMaxPct = riskParams.slMaxPct || 2.0; // תקרת SL באחוז
  const slMinPct = riskParams.slMinPct || 0.5; // רצפת SL — צד נכון, לא הדוק/אפס
  const entryMode = cal.entryMode || 'pullback';
  // עיגון: פולבק = Limit מודע באזור EMA7 שאליו המחיר יחזור (לא רודפים את המחיר הנוכחי).
  //        מומנטום/המשך = Market במחיר הנוכחי (נכנסים עכשיו על המהלך).
  const anchorPrice = entryMode === 'pullback' ? ema7 : price;
  const _stp = computeSlTp(dir, anchorPrice, ema14, ema28, atr, {
    slAtrMult,
    tp1Mult,
    tp2Mult,
    slMaxPct,
    slMinPct
  });
  const sl = _stp.sl,
    tp1 = _stp.tp1,
    tp2 = _stp.tp2;
  const slPct = _stp.slPct,
    tp1Pct = _stp.tp1Pct,
    tp2Pct = _stp.tp2Pct;
  const positionSize = slPct > 0 ? accountBalance * (riskTolerance / 100) / (slPct / 100) : 0;

  // v25.43: תצוגת ניהול-מגמה חלופית (display בלבד — לא משנה ניקוד/קונסנזוס/סיגנל).
  // אותו סטאפ, אותו עיגון — אך SL/TP/גודל לפי פרמטרי רכיבת-מגמה (מנוף 3, SL רחב).
  const _tm = computeSlTp(dir, anchorPrice, ema14, ema28, atr, {
    slAtrMult: TREND_MGMT_RISK.slAtrMult,
    tp1Mult: 1.5,
    tp2Mult: 3,
    slMaxPct: TREND_MGMT_RISK.slMaxPct,
    slMinPct: slMinPct
  });
  const tmPosSize = _tm.slPct > 0 ? accountBalance * (riskTolerance / 100) / (_tm.slPct / 100) : 0;
  // ניהול מגמה = טריילינג (לא TP): סטופ רחב מגן עד הפעלה, ואז callback רחב רוכב על המהלך.
  const tmAct = TREND_MGMT_RISK.trailActivationPct;
  const tmCb = TREND_MGMT_RISK.trailCallbackPct;
  const tmActPrice = dir === 'short' ? anchorPrice * (1 - tmAct / 100) : anchorPrice * (1 + tmAct / 100);
  const trendMgmt = entryMode === 'momentum' ? {
    sl: roundPrice(_tm.sl),
    slPct: Number(_tm.slPct.toFixed(2)),
    positionSize: Math.round(tmPosSize),
    leverage: TREND_MGMT_RISK.defaultLeverage,
    marginUsed: Math.round(tmPosSize / TREND_MGMT_RISK.defaultLeverage),
    trailActivationPct: tmAct,
    trailCallbackPct: tmCb,
    activationPrice: roundPrice(tmActPrice)
  } : null;

  // ===== SIGNAL CLASSIFICATION + הסבר מנומק אחיד =====
  // כל סיגנל שאינו EXECUTE מקבל הסבר *מנומק* (למה לא נכנסים),
  // ומחיר יעד מספרי רק כשהחסם הוא מרחק מחיר (מקרה הפולבק).
  const trendWord = dir === 'long' ? 'שורית' : 'דובית';
  const actionWord = dir === 'long' ? 'לונג' : 'שורט';
  const entryLow = Math.min(ema7, ema14);
  const entryHigh = Math.max(ema7, ema14);
  const distPct = (dist * 100).toFixed(1);
  const pullbackThreshPct = (distThresh * 1.25 * 100).toFixed(1);
  const fmt = n => n >= 1000 ? Math.round(n).toLocaleString('en-US') : n.toFixed(2);

  // ===== שערי כניסה לפי entryMode (לא משנים ציון — חוסמים/מתירים EXECUTE) =====
  // pullback   = אין שער מיוחד (הטכניקה הקלאסית).
  // continuation = חלון moveDone 20–60%, חוסם RSI קיצוני (מהלך מותש).
  // momentum   = דורש מהלך רץ (move ≥ momMoveDoneMin); מתיר RSI קיצוני במכוון (רוכבים).
  const rsiExtremeNow = dir === 'short' && rsi < cal.rsiOversoldLimit || dir === 'long' && rsi > cal.rsiOverboughtLimit;
  let gateBlock = false,
    gateHard = false,
    gateReason = '';
  if (entryMode === 'continuation') {
    const cMin = cal.contMoveDoneMin ?? 20,
      cMax = cal.contMoveDoneMax ?? 60;
    if (rsiExtremeNow) {
      gateBlock = true;
      gateHard = true;
      gateReason = `RSI ${rsi.toFixed(0)} קיצוני — מהלך מותש, אין כניסת המשך.`;
    } else if (moveDonePct === null) {
      gateBlock = true;
      gateReason = 'אין טווח swing לחישוב התקדמות המהלך — אין כניסת המשך.';
    } else if (moveDonePct > cMax) {
      gateBlock = true;
      gateHard = true;
      gateReason = `המהלך התקדם ${Math.round(moveDonePct)}% (מעל ${cMax}%) — מותש. רדיפה, לא כניסת המשך.`;
    } else if (moveDonePct < cMin) {
      gateBlock = true;
      gateReason = `המהלך רק ${Math.round(moveDonePct)}% (מתחת ל-${cMin}%) — מוקדם מדי, ייתכן פולס. המתן לאישור מבני.`;
    }
  } else if (entryMode === 'momentum') {
    const mMin = cal.momMoveDoneMin ?? 60;
    if (moveDonePct === null) {
      gateBlock = true;
      gateReason = 'אין טווח swing לחישוב התקדמות המהלך — אין כניסת מומנטום.';
    } else if (moveDonePct < mMin) {
      gateBlock = true;
      gateReason = `המהלך רק ${Math.round(moveDonePct)}% (מתחת ל-${mMin}%) — לא רץ מספיק לכניסת מומנטום. זו לא רדיפה, פשוט עדיין לא מומנטום.`;
    }
    // move ≥ mMin → מותר. RSI קיצוני מותר במכוון — זה כל הרעיון של מומנטום.
  }
  let signal, desc;
  if (blocked) {
    // בדיקת חובה נכשלה → פסול, ללא תלות בציון
    signal = 'NO TRADE';
    const names = failedRequired.map(c => c.label).join(', ');
    desc = `פסול — בדיקת חובה נכשלה: ${names}. אין כניסה ${actionWord} גם אם הציון גבוה.`;
  } else if ((entryMode === 'continuation' || entryMode === 'momentum') && gateBlock) {
    // שער ההמשך/מומנטום נכשל — מותש/קיצוני = NO TRADE, מוקדם/לא-רץ = WAIT
    signal = gateHard ? 'NO TRADE' : 'WAIT';
    desc = gateReason;
  } else if (score >= cal.executeCutoff) {
    // v25.23: שער הגנה (מומנטום מוגן) — דורש ER+התרחבות לפני EXECUTE. אינו משנה את הציון.
    const _erTh = cal.defenseErThreshold ?? 0.4;
    const _erOk = effRatio != null && effRatio >= _erTh;
    const _expOk = cal.defenseRequireExpansion ? !!(volExp && volExp.expanded) : true;
    if (cal.defenseGate && !(_erOk && _expOk)) {
      signal = 'WAIT';
      const _erTxt = effRatio == null ? 'ER לא זמין' : _erOk ? `ER ${effRatio.toFixed(2)}✓` : `ER ${effRatio.toFixed(2)}<${_erTh}`;
      const _expTxt = volExp && volExp.expanded ? 'התרחבות ✓' : 'אין התרחבות תנודתית';
      desc = `🛡️ שער הגנה: הציון ${score} מספיק (≥${cal.executeCutoff}), אבל תנאי התנועה לא מאושרים — ${_erTxt} · ${_expTxt}. ממתין למהלך תכליתי שמתפרץ לפני כניסה.`;
    } else {
      signal = 'EXECUTE';
      if (entryMode === 'momentum') {
        const mdTxt = moveDonePct != null ? Math.round(moveDonePct) + '%' : '?';
        const rsiTxt = rsiExtremeNow ? ` RSI ${rsi.toFixed(0)} קיצוני — מומנטום מאוחר, סיכון היפוך גבוה.` : '';
        const defTxt = cal.defenseGate ? ` 🛡️ שער הגנה עבר (ER ${effRatio != null ? effRatio.toFixed(2) : '?'}, התרחבות פעילה).` : '';
        desc = `מומנטום ${dir === 'long' ? 'לונג' : 'שורט'} חי — מהלך רץ (${mdTxt}).${rsiTxt}${defTxt} ⚠ כניסה מאוחרת: חובה Trailing Stop ב-Bybit. אל תחזיק SL סטטי — צא ברגע שהמומנטום נשבר.`;
      } else {
        desc = dir === 'long' ? 'תנאים מסונכרנים לכניסת לונג.' : 'תנאים מסונכרנים לכניסת שורט.';
      }
    }
  } else if (score >= cal.waitCutoff && dist > distThresh * 1.25) {
    // חסם = מרחק מחיר → יש מחיר יעד אמיתי (אזור הכניסה)
    signal = 'WAIT';
    const moveWord = price > ema7 ? 'ירד' : 'יעלה';
    desc = `מגמה ${trendWord} תקפה, אבל המחיר רחוק מ-EMA7 ב-${distPct}% (סף ${pullbackThreshPct}%). המתן ש${moveWord} חזרה לאזור הכניסה $${fmt(entryLow)}–$${fmt(entryHigh)} לפני ${actionWord}.`;
  } else if (score >= cal.waitCutoff) {
    signal = 'WAIT';
    if (penalized) {
      // חסם = RSI בקיצון → אין מחיר יעד, ממתינים להתייצבות RSI
      const rsiZone = rsi < cal.rsiOversoldLimit ? 'oversold' : 'overbought';
      desc = `מגמה ${trendWord} תומכת, אבל RSI ${rsi.toFixed(0)} ב-${rsiZone} — סיכון להיפוך טווח קצר. המתן שה-RSI יתייצב.`;
    } else {
      // חסם = תנאים חסרים → מציגים *מה חסר*, לא מחיר
      const missing = [];
      if (!hasFvg) missing.push('FVG');
      if (!rejH.hasWick) missing.push('דחיית פתיל');
      const ltfOk = dir === 'long' && ltfCross === 'bullish' || dir === 'short' && ltfCross === 'bearish';
      if (!ltfOk) missing.push('אישור LTF');
      if (dist >= distThresh) missing.push('קרבה ל-EMA7');
      const missingStr = missing.length ? missing.join(', ') : 'אישור נוסף';
      desc = `מגמה ${trendWord} תומכת, אבל חסרים אישורים: ${missingStr}. ממתין לקונפלואנס.`;
    }
  } else {
    signal = 'NO TRADE';
    if (penalized) {
      desc = `RSI ${rsi.toFixed(0)} קיצוני בכיוון הנגדי — אין כניסה.`;
    } else {
      desc = `הפילטרים סותרים (ציון ${Math.round(score)}). אין מגמה ברורה לכיוון ${actionWord}.`;
    }
  }

  // ===== קריאת קצה — נטיית היפוך/המשך ב-moveDone גבוה (נשמר לדאטה) =====
  let edgeVerdict = null;
  // כיוון התנועה האחרון (3 נרות יומיים) — קלט לזיהוי מעבר משטר (מודיעין בלבד).
  // מתקן את "באג קריאת הקצה העיוורת לכיוון": אם המחיר זז חזק *נגד* כיוון ה-thesis,
  // אסור לקרוא לזה "המשך" — ייתכן מעבר משטר.
  let recentMovePct = null;
  const recentN = 3;
  if (c.length > recentN + 1) {
    const past = c[c.length - 1 - recentN];
    if (past) recentMovePct = (closedClose - past) / past * 100;
  }
  const recentAgainst = recentMovePct != null && (dir === 'short' && recentMovePct >= 3 || dir === 'long' && recentMovePct <= -3);
  {
    const md = moveDonePct !== null ? Math.round(moveDonePct) : null;
    if (md !== null && md >= 75) {
      const rsiExt = dir === 'short' && rsi < (cal.rsiOversoldLimit ?? 20) || dir === 'long' && rsi > (cal.rsiOverboughtLimit ?? 80);
      const htfAl = dir === 'short' && weeklyBias === 'bearish' || dir === 'long' && weeklyBias === 'bullish';
      const exh = md >= 90;
      const rev = (rsiExt ? 2 : 0) + (exh ? 1 : 0) + (!htfAl ? 1 : 0);
      const cont = (htfAl ? 2 : 0) + (!rsiExt ? 1 : 0);
      // מעבר משטר גובר: תנועה אחרונה חזקה נגד הכיוון = לא "המשך", התראה.
      if (recentAgainst) edgeVerdict = 'regime_shift';else edgeVerdict = rev >= 3 && rev > cont ? 'reversal' : cont >= 2 && cont >= rev ? 'continuation' : 'mixed';
    }
  }
  return {
    direction: dir,
    score,
    signal,
    desc,
    price,
    breakdown,
    penalized,
    ema7,
    ema7Slope,
    ema14Slope,
    ema28Slope,
    ema14,
    ema28,
    ema200,
    rsi,
    atr,
    funding,
    ltfCross,
    weeklyBias,
    weeklyRsi: weeklyRsi != null ? Math.round(weeklyRsi * 10) / 10 : null,
    weeklyEma20: weeklyEma20 != null ? weeklyEma20 : null,
    weeklyEma50: weeklyEma50 != null ? weeklyEma50 : null,
    weeklySwingHigh: weeklySwing && weeklySwing.swingHigh ? weeklySwing.swingHigh.value : null,
    weeklySwingLow: weeklySwing && weeklySwing.swingLow ? weeklySwing.swingLow.value : null,
    adlValue: adl ? adl.value : null,
    adlTrend: adl ? adl.trend : null,
    adlChangePct: adl ? adl.changePct : null,
    sweepBelow: sweepDn && sweepDn.swept ? sweepDn.candlesAgo : null,
    sweepAbove: sweepUp && sweepUp.swept ? sweepUp.candlesAgo : null,
    hasFvg,
    hasWick: rejH.hasWick,
    wickRatio: rejH.maxRatio,
    wickVolumeRatio: rejH.volumeRatio,
    swingHigh: swing.swingHigh?.value,
    swingLow: swing.swingLow?.value,
    moveDonePct: moveDonePct !== null ? Math.round(moveDonePct) : null,
    chaseWarning,
    adx: adxObj ? adxObj.adx : null,
    adxPlusDI: adxObj ? adxObj.plusDI : null,
    adxMinusDI: adxObj ? adxObj.minusDI : null,
    regime: regimeInfo.regime,
    regimeLabel: regimeInfo.label,
    regimeColor: regimeInfo.color,
    moveDoneHigh,
    moveDoneLow,
    edgeVerdict,
    recentMovePct: recentMovePct != null ? Math.round(recentMovePct * 10) / 10 : null,
    oi: raw.oi ?? null,
    vwapAnchored: vwapAnchored ? vwapAnchored.vwap : null,
    vwapGapPct: vwapAnchored ? vwapAnchored.gapPct : null,
    vwapTriggerLong: vwapAnchored ? vwapAnchored.triggerLong : false,
    oiChangePct: raw.oiChangePct != null ? Math.round(raw.oiChangePct * 100) / 100 : null,
    priceChange1d: c.length >= 2 && c[c.length - 2] > 0 ? Math.round((c[c.length - 1] - c[c.length - 2]) / c[c.length - 2] * 1000) / 10 : null,
    isolationZ,
    blocked,
    failedRequired: failedRequired.map(c => c.label),
    scoreComponents,
    scoreMaxPossible,
    penaltyGot,
    // FIX אחיד: Entry = המחיר הנוכחי לכל הפרופילים. ב-EXECUTE נכנסים עכשיו (Market),
    // וה-SL/TP מעוגנים למחיר — כך אין פער בין Entry ל-SL באף פרופיל (כולל פולבק כש-EMA7
    // נכשל אבל הציון עבר, וכולל פרופילי בקטסט). אזור הפולבק מופיע בטקסט ה-WAIT בלבד.
    // פולבק = Limit מודע: מציג את אזור EMA7 שאליו המחיר יחזור (ה-SL/TP מעוגנים אליו).
    // מומנטום/המשך = Market: המחיר הנוכחי.
    entry: entryMode === 'pullback' ? `${fmtPrice(entryLow)} - ${fmtPrice(entryHigh)}` : fmtPrice(price),
    sl: roundPrice(sl),
    tp1: roundPrice(tp1),
    tp2: roundPrice(tp2),
    slPct: Number(slPct.toFixed(2)),
    tp1Pct: Number(tp1Pct.toFixed(2)),
    tp2Pct: Number(tp2Pct.toFixed(2)),
    positionSize: Math.round(positionSize),
    trendMgmt
  };
};


export const MOMENTUM_CAL = {
  ...DEFAULT_CALIBRATION,
  entryMode:'momentum', executeCutoff:70, momMoveDoneMin:60, rsiExtremePenalty:false,
  checkConfig:{ macro:{weight:25,required:true}, htf:{weight:20,required:true},
    rsiMom:{weight:20,required:false}, ltf:{weight:20,required:false}, ema7:{weight:0,required:false},
    fvg:{weight:5,required:false}, wick:{weight:5,required:false}, liquidity:{weight:5,required:false},
    funding:{weight:5,required:false}, volume:{weight:3,required:false}, isolation:{weight:2,required:false} },
};
export { scoreDirection, computeSlTp, computeAnchoredVwap, computeADL, detectSweep, classifyRegime,
  detectSMC, detectWickRejection, findRecentSwingLevels, getWeeklyBias, calcEfficiencyRatio,
  calcVolExpansion, roundPrice, fmtPrice, priceDecimals, DEFAULT_RISK, DEFAULT_CALIBRATION, TREND_MGMT_RISK };
