// Build image production (frontend/Dockerfile) set SKIP_BUILD_CHECKS=1: lint & typecheck
// sudah dijalankan CI, jadi tidak diulang di VPS. Build lokal tetap memeriksa keduanya.
const skipBuildChecks = process.env.SKIP_BUILD_CHECKS === "1";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Bundel server + dependency yang benar-benar dipakai ke `.next/standalone`,
  // supaya image production tidak perlu membawa seluruh node_modules.
  output: "standalone",
  eslint: { ignoreDuringBuilds: skipBuildChecks },
  typescript: { ignoreBuildErrors: skipBuildChecks },
};

export default nextConfig;
