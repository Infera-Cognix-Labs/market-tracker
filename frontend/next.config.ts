import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",

  basePath: "/market-tracker",
  assetPrefix: "/market-tracker/",

  async redirects() {
    return [
      {
        source: "/",
        destination: "/market-tracker",
        permanent: false,
        basePath: false,
      },
    ];
  },

  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://217.216.34.228:8000/:path*",
      },
    ];
  },
};

export default nextConfig;