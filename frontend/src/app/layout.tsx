import type { Metadata, Viewport } from "next";
import "./globals.css";
import { RouteBreadcrumbs } from "@/components/app/RouteBreadcrumbs";
import { ServiceWorkerRegister } from "@/components/app/ServiceWorkerRegister";

export const metadata: Metadata = {
  title: "FINARODA",
  description: "Decision-support for crypto swing trading. Analysis, not advice.",
  applicationName: "FINARODA",
  manifest: "/manifest.webmanifest",
  appleWebApp: { capable: true, statusBarStyle: "black-translucent", title: "FINARODA" },
  icons: {
    icon: [
      { url: "/icons/icon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
};

export const viewport: Viewport = {
  themeColor: "#0b0d12",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <ServiceWorkerRegister />
        <RouteBreadcrumbs />
        {children}
      </body>
    </html>
  );
}
