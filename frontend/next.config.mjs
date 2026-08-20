/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Bundel server + dependency yang benar-benar dipakai ke `.next/standalone`,
  // supaya image production tidak perlu membawa seluruh node_modules.
  output: "standalone",
};

export default nextConfig;
