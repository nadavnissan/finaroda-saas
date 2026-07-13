"use client";

import { useEffect, useState } from "react";

// Responsive breakpoint hook (RESPONSIVE PASS). Inline-styled components can't use
// CSS media queries, so screens that need to swap layout (e.g. the admin console,
// which is desktop-first row layout but must stack on a phone) branch on this.
//
// SSR/hydration safety: it returns `false` (desktop) until the component mounts on
// the client, then updates — this matches the server render (which has no viewport)
// and avoids a hydration mismatch. Callers that render nothing until data loads
// (admin gates behind useMe) never even show the desktop frame first.
export function useIsMobile(maxWidth = 768): boolean {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${maxWidth}px)`);
    const update = () => setIsMobile(mql.matches);
    update();
    // addEventListener("change") is supported in all evergreen browsers; the
    // deprecated addListener fallback keeps older Safari happy.
    if (mql.addEventListener) mql.addEventListener("change", update);
    else mql.addListener(update);
    return () => {
      if (mql.removeEventListener) mql.removeEventListener("change", update);
      else mql.removeListener(update);
    };
  }, [maxWidth]);

  return isMobile;
}
