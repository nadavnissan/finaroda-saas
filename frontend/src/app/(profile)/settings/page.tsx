"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { C } from "@/lib/onboarding/types";

// Settings live inside the Profile screen (B5). This route keeps the nav item working.
export default function SettingsPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/profile");
  }, [router]);
  return <main style={{ minHeight: "100vh", background: C.bg }} />;
}
