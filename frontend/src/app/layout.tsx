import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FINARODA",
  description: "Decision-support for crypto swing trading. Analysis, not advice.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
