import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  webpack: (config) => {
    // point @ to the *current* folder (frontend root)
    config.resolve.alias["@"]= path.resolve(__dirname);
    return config;
  },
};

export default nextConfig;

