import { Suspense } from 'react';
import { WorkflowView } from '@/components/workflow-view';
export default function WorkflowPage() { return <Suspense fallback={<p>Loading workflow…</p>}><WorkflowView /></Suspense>; }
