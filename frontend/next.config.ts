import type { NextConfig } from 'next';
import { PHASE_DEVELOPMENT_SERVER } from 'next/constants';
export default function config(phase: string): NextConfig {
 const development = phase === PHASE_DEVELOPMENT_SERVER;
 const localServer = process.env.ODIN_LOCAL_SERVER === '1';
 const proxy = development || localServer;
 const target = (process.env.API_PROXY_TARGET || 'http://localhost:8000').replace(/\/$/,'');
 return {
  output: proxy ? undefined : 'export',
  distDir: process.env.ODIN_BUILD_DIR || (localServer ? '.next-local' : '.next'),
  trailingSlash: true,
  poweredByHeader: false,
  // Dev proxy must not gzip: compression buffers the /api/stream SSE so the live feed never connects.
  compress: false,
  images: { unoptimized: true },
  env: { NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? (proxy ? '/' : '') },
  ...(proxy ? {
   skipTrailingSlashRedirect: true,
   async rewrites() {
    return { beforeFiles: [
     { source: '/api/:path*', destination: target + '/api/:path*' },
     { source: '/auth/google/callback', destination: target + '/auth/google/callback' },
     { source: '/openapi.json', destination: target + '/openapi.json' }
    ] };
   }
  } : {})
 };
}
