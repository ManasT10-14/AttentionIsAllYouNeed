import type { NextConfig } from 'next';
import { PHASE_DEVELOPMENT_SERVER } from 'next/constants';
export default function config(phase: string): NextConfig {
 const development = phase === PHASE_DEVELOPMENT_SERVER;
 const target = (process.env.API_PROXY_TARGET || 'http://localhost:8000').replace(/\/$/,'');
 return {
  output: development ? undefined : 'export',
  trailingSlash: true,
  poweredByHeader: false,
  images: { unoptimized: true },
  env: { NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? (development ? '/' : '') },
  ...(development ? {
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
