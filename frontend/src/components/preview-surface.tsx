'use client';

import { useRef, type PointerEvent, type ReactNode } from 'react';
import { motion, useMotionValue, useReducedMotion, useSpring } from 'motion/react';

export function PreviewSurface({ children, onClick }: { children: ReactNode; onClick: () => void }) {
  const reducedMotion = useReducedMotion();
  const bounds = useRef<DOMRect | null>(null);
  const pitch = useMotionValue(0);
  const yaw = useMotionValue(0);
  const rotateX = useSpring(pitch, { stiffness: 130, damping: 22, mass: .7 });
  const rotateY = useSpring(yaw, { stiffness: 130, damping: 22, mass: .7 });
  function movePointer(event: PointerEvent<HTMLButtonElement>) {
    if (reducedMotion || event.pointerType !== 'mouse') return;
    const rect = bounds.current ?? event.currentTarget.getBoundingClientRect();
    pitch.set(-((event.clientY - rect.top) / rect.height - .5) * 7);
    yaw.set(((event.clientX - rect.left) / rect.width - .5) * 7);
  }
  return <motion.button className="product-preview" aria-label="Explore Odin demo dashboard" onClick={onClick} style={!reducedMotion ? { rotateX, rotateY, transformPerspective: 1400 } : undefined} onPointerEnter={event => { bounds.current = event.currentTarget.getBoundingClientRect(); }} onPointerMove={movePointer} onPointerLeave={() => { bounds.current = null; pitch.set(0); yaw.set(0); }} whileTap={reducedMotion ? undefined : { scale: .99 }}>{children}</motion.button>;
}
