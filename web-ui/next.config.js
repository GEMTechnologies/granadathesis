/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Determine backend URL based on environment
    // In Docker: use backend service name for server-side, localhost for client
    // Outside Docker: use localhost
    const backendUrl = process.env.BACKEND_URL ||
      (process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000');

    return [
      {
        source: '/api/:path*',
        // Use backend service name when in Docker (server-side)
        // Client-side will use NEXT_PUBLIC_BACKEND_URL
        destination: `${backendUrl}/api/:path*`,
      },
    ]
  },
}

module.exports = nextConfig






