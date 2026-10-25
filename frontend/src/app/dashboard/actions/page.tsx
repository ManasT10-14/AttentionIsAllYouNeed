import { Suspense } from 'react';
import { ActionsView } from '@/components/actions-view';
export default function ActionsPage() { return <Suspense fallback={<p>Loading action queue…</p>}><ActionsView /></Suspense>; }
