import { withPayload } from "@payloadcms/next/withPayload";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  async redirects() {
    return [
      {
          source: "/about/:slug",
          destination: "/people/:slug",
        permanent: true,
      },
    ];
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.unsplash.com",
        pathname: "/photo-**",
      },
      {
        protocol: "https",
        hostname: "assets.philamuseum.org",
        pathname: "/**",
      },
    ],
  },
};

export default withPayload(nextConfig);
