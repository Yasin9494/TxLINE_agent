import type { NextConfig } from "next";

// Static export — FastAPI serves the built `out/` folder at / and the API at /api.
// Flag images come from flagcdn.com so image optimisation is disabled.
const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
  trailingSlash: true,
};

export default nextConfig;
