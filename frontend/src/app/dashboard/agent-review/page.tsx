import { Suspense } from 'react';
import { AgentReviewView } from '@/components/agent-review-view';
export default function AgentReviewPage() { return <Suspense fallback={<p>Loading debate…</p>}><AgentReviewView /></Suspense>; }
