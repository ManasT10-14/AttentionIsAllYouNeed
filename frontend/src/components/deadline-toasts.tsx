'use client';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { BellRing, X } from 'lucide-react';
import { useWorkspace } from './providers';
import { Button, IconButton } from './ui';
export function DeadlineToasts({ onOpen }: { onOpen: () => void }) {
 const { notices } = useWorkspace(); const [hidden, setHidden] = useState<number[]>([]);
 const fresh = notices.filter(n => n.category === 'deadline' && n.toast && !hidden.includes(n.id));
 const batch = fresh.map(n => n.id).join(',');
 useEffect(() => {
  if (!batch) return;
  const ids = batch.split(',').map(Number);
  const timer = setTimeout(() => setHidden(previous => [...previous, ...ids]), 15000);
  return () => clearTimeout(timer);
 }, [batch]);
 if (!fresh.length) return null;
 const notice = fresh[0];
 return <aside className="deadline-toast" role="status" aria-live="polite" aria-label="Upcoming deadline reminder"><span className="deadline-toast-icon"><BellRing size={20} /></span><div><strong>{notice.title}</strong><p>{notice.detail}</p>{fresh.length > 1 && <small>{fresh.length - 1} more upcoming deadline{fresh.length > 2 ? 's' : ''}</small>}<div className="button-row"><Link className="text-link" href={notice.href}>Open timeline</Link><Button variant="ghost" onClick={onOpen}>All notifications</Button></div></div><IconButton icon={X} label="Dismiss deadline popup" onClick={() => setHidden(previous => [...previous, ...fresh.map(n => n.id)])} /></aside>;
}
