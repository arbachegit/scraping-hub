import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      // Auth routes -> Python API (port 8000)
      {
        source: '/api/auth/:path*',
        destination: 'http://localhost:8000/auth/:path*',
      },
      // Other API routes -> Node.js backend (port 3001)
      {
        source: '/api/:path*',
        destination: 'http://localhost:3001/:path*',
      },
    ];
  },
};

export default nextConfig;
