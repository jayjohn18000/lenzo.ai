import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  outputFileTracingRoot: path.join(__dirname, '../'),
  
  // Increase timeout for API routes and proxied requests
  experimental: {
    proxyTimeout: 120000, // 2 minutes
  },
  
  // API route configuration
  api: {
    responseLimit: false,
    bodyParser: {
      sizeLimit: '10mb',
    },
    // Disable default timeout
    externalResolver: true,
  },

  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },

  webpack: (config) => {
    config.resolve.alias["@"] = path.resolve(__dirname);
    return config;
  },

  // Additional timeout settings
  serverRuntimeConfig: {
    // Will only be available on the server side
    requestTimeout: 120000, // 2 minutes
  },
};

export default nextConfig;