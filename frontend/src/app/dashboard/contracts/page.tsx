import { Suspense } from 'react';
import { ContractsView } from '@/components/contracts-view';
export default function ContractsPage() { return <Suspense fallback={<p>Loading contracts…</p>}><ContractsView /></Suspense>; }
