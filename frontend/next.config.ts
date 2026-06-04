import type { NextConfig } from "next";

const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "/market-tracker";

const nextConfig: NextConfig = {
  output: "standalone",

  basePath: BASE_PATH,
  assetPrefix: `${BASE_PATH}/`,
};

export default nextConfig;