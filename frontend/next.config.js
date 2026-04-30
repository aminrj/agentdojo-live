/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  async rewrites() {
    // Proxy /api/* to the backend. The rewrite is performed by the Next.js
    // server (not the browser), so this URL must resolve from inside the
    // frontend container -- use the internal service name in docker/k8s.
    const backend =
      process.env.BACKEND_URL ||
      process.env.NEXT_PUBLIC_BACKEND_URL ||
      'http://localhost:8000';
    return [{ source: '/api/:path*', destination: `${backend}/api/:path*` }];
  },
};
module.exports = nextConfig;
