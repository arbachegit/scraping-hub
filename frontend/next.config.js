/** @type {import('next').NextConfig} */
const nextConfig = {
  // Configuracao para conectar com o backend Python
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
      {
        source: '/auth/:path*',
        destination: 'http://localhost:8000/auth/:path*',
      },
      {
        source: '/health',
        destination: 'http://localhost:8000/health',
      },
    ]
  },
}

module.exports = nextConfig
