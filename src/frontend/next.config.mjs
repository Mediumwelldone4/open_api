/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  eslint: {
    dirs: ["app"],
  },
  experimental: {
    typedRoutes: true,
  },
};

export default nextConfig;
