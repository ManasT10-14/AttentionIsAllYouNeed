import { Suspense } from 'react';
import { ReportsView } from '@/components/reports-view';
export default function ReportsPage() { return <Suspense fallback={<p>Loading reports…</p>}><ReportsView /></Suspense>; }
