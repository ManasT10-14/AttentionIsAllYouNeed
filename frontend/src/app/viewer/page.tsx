import { Suspense } from 'react';
import { DashboardShell } from '@/components/dashboard-shell';
import { ReferenceViewer } from '@/components/reference-viewer';
export default function ViewerPage() { return <DashboardShell><Suspense fallback={<p>Opening reference…</p>}><ReferenceViewer /></Suspense></DashboardShell>; }
