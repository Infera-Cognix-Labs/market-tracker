import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
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
