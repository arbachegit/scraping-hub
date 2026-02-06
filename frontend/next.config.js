/** @type {import('next').NextConfig} */
const nextConfig = {
  // Configuracao para conectar com o backend Python
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ]
  },
}

module.exports = nextConfig
