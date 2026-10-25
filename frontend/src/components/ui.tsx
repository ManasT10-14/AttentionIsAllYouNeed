'use client';

import * as Dialog from '@radix-ui/react-dialog';
import { ArrowRight, X, type LucideIcon } from 'lucide-react';
import { useRef, type ButtonHTMLAttributes, type PointerEvent, type ReactNode } from 'react';
import { motion, useMotionValue, useReducedMotion, useSpring } from 'motion/react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

export function Logo({ compact = false }: { compact?: boolean }) {
  return <Link href="/" className="brand" aria-label="Odin home"><span className="brand-mark">O</span>{!compact && 'odin'}</Link>;
}
export function Button({ children, className, variant = 'primary', ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost' }) {
  return <button className={cn('button', `button-${variant}`, className)} {...props}>{children}</button>;
}
export function LinkButton({ href, children, secondary = false, className }: { href: string; children: ReactNode; secondary?: boolean; className?: string }) {
  return <Link href={href} className={cn('button', secondary ? 'button-secondary' : 'button-primary', className)}>{children}</Link>;
}
export function Panel({ children, className }: { children: ReactNode; className?: string }) {
  const reducedMotion = useReducedMotion();
  const bounds = useRef<DOMRect | null>(null);
  const interactive = className?.split(' ').includes('stat-card');
  const pitch = useMotionValue(0);
  const yaw = useMotionValue(0);
  const rotateX = useSpring(pitch, { stiffness: 220, damping: 24 });
  const rotateY = useSpring(yaw, { stiffness: 220, damping: 24 });
  function movePointer(event: PointerEvent<HTMLElement>) {
    if (!interactive || reducedMotion || event.pointerType !== 'mouse') return;
    const rect = bounds.current ?? event.currentTarget.getBoundingClientRect();
    const horizontal = (event.clientX - rect.left) / rect.width;
    const vertical = (event.clientY - rect.top) / rect.height;
    pitch.set((.5 - vertical) * 5);
    yaw.set((horizontal - .5) * 5);
    event.currentTarget.style.setProperty('--surface-x', `${horizontal * 100}%`);
    event.currentTarget.style.setProperty('--surface-y', `${vertical * 100}%`);
  }
  return <motion.section className={cn('panel', className)} whileHover={interactive && !reducedMotion ? { y: -6 } : undefined} transition={{ type: 'spring', stiffness: 260, damping: 24 }} style={interactive && !reducedMotion ? { rotateX, rotateY, transformPerspective: 1000 } : undefined} onPointerEnter={event => { bounds.current = event.currentTarget.getBoundingClientRect(); }} onPointerMove={movePointer} onPointerLeave={() => { bounds.current = null; pitch.set(0); yaw.set(0); }}>{children}</motion.section>;
}
export function PageTitle({ eyebrow, title, description, children }: { eyebrow: string; title: string; description: string; children?: ReactNode }) {
  return <div className="page-title"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="page-description">{description}</p></div>{children && <div className="page-title-actions">{children}</div>}</div>;
}
export function PanelTitle({ title, description, children }: { title: string; description?: string; children?: ReactNode }) {
  return <div className="panel-title"><div><h2>{title}</h2>{description && <p>{description}</p>}</div>{children}</div>;
}
export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: string }) { return <span className={cn('badge', `badge-${tone}`)}>{children}</span>; }
export function IconButton({ icon: Icon, label, className, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { icon: LucideIcon; label: string }) {
  return <button className={cn('icon-button', className)} aria-label={label} title={label} {...props}><Icon size={18} strokeWidth={1.7} /></button>;
}
export function TextLink({ href, children }: { href: string; children: ReactNode }) { return <Link className="text-link" href={href}>{children}<ArrowRight size={14} /></Link>; }
export function Sheet({ open, onOpenChange, title, description, children }: { open: boolean; onOpenChange: (open: boolean) => void; title: string; description: string; children: ReactNode }) {
  return <Dialog.Root open={open} onOpenChange={onOpenChange}><Dialog.Portal><Dialog.Overlay className="sheet-overlay" /><Dialog.Content className="sheet-content"><Dialog.Close asChild><button className="sheet-close icon-button" aria-label="Close panel"><X size={18} /></button></Dialog.Close><p className="eyebrow">WORKSPACE DETAILS</p><Dialog.Title className="sheet-title">{title}</Dialog.Title><Dialog.Description className="sheet-description">{description}</Dialog.Description>{children}</Dialog.Content></Dialog.Portal></Dialog.Root>;
}
export function EmptyState({ title, description }: { title: string; description: string }) { return <div className="empty-state"><h3>{title}</h3><p>{description}</p></div>; }
