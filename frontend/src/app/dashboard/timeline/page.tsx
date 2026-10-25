import { Suspense } from 'react';
import { TimelineView } from '@/components/timeline-view';
export default function TimelinePage() { return <Suspense fallback={<p>Loading timeline…</p>}><TimelineView /></Suspense>; }
