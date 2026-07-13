"use client";

// Records a route_change breadcrumb on every App Router navigation (Stage 7, D-A7).
// Renders nothing; mounted once in the root layout.
import { useEffect } from "react";
import { usePathname } from "next/navigation";

import { addBreadcrumb } from "@/lib/breadcrumbs";

export function RouteBreadcrumbs() {
  const pathname = usePathname();
  useEffect(() => {
    addBreadcrumb("route_change", { path: pathname });
  }, [pathname]);
  return null;
}
