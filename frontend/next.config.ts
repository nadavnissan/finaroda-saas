import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // The shared scoring engine is a linked ESM package — transpile it for the client bundle.
  transpilePackages: ["@finaroda/scoring-engine"],
};

export default nextConfig;
