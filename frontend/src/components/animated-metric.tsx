'use client';
import { useEffect } from 'react';
import { motion,useReducedMotion,useSpring,useTransform } from 'motion/react';
export function AnimatedMetric({value}:{value:number}) {
 const reduced=useReducedMotion();const spring=useSpring(0,{stiffness:85,damping:22,restDelta:.1});const display=useTransform(spring,current=>String(Math.round(current)));
 useEffect(()=>{if(reduced)spring.jump(value);else spring.set(value);},[value,spring,reduced]);
 return <strong className="stat-value" aria-label={String(value)}><motion.span aria-hidden="true">{display}</motion.span></strong>;
}
