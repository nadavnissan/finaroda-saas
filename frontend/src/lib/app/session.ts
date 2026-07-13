"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "@/lib/api";
import type { Me } from "./types";

type Guard = "any" | "admin";

// Shared auth guard for the post-auth app shell. Does not render protected content
// until /me resolves (avoids the mid-flow flash fixed in F13). Redirects unauthenticated
// users to /login and non-admins away from admin routes.
export function useMe(guard: Guard = "any"): { me: Me | null; loading: boolean } {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    void apiFetch<{ data: Me }>("/api/auth/me").then((r) => {
      if (!alive) return;
      if (!r.ok || !r.data?.data) {
        router.replace("/login");
        return;
      }
      const user = r.data.data;
      if (guard === "admin" && !user.is_admin) {
        router.replace("/dashboard");
        return;
      }
      setMe(user);
      setLoading(false);
    });
    return () => {
      alive = false;
    };
  }, [router, guard]);

  return { me, loading };
}
