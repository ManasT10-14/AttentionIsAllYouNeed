'use client';

import { motion } from 'motion/react';
import { ArrowUpRight, CalendarDays, FileCheck2, ShieldCheck, Check } from 'lucide-react';

const features = [
  { icon: FileCheck2, title: 'Grounded in source', text: 'Every risk and recommendation links directly to the clause that supports it.', label: 'SOURCE VERIFIED' },
  { icon: CalendarDays, title: 'Always time-aware', text: 'Explore obligations, renewals, and financial exposure before they become urgent.', label: 'STAY A STEP AHEAD' },
  { icon: ShieldCheck, title: 'Human in control', text: 'Clear approvals keep consequential actions with the people responsible for them.', label: 'YOUR DECISION' }
];

export function FeatureCards() {
  return <div className="landing-feature-grid">{features.map((item, index) => <motion.article className={`feature-card feature-card-${index}`} key={item.title} initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: .2 }} transition={{ delay: index * .1, duration: .5 }}>
    <div className="feature-topline"><span className="feature-icon"><item.icon size={22} strokeWidth={1.8} /></span><span className="feature-number">0{index + 1}</span></div>
    <div className="feature-illustration" aria-hidden="true">{index === 0 ? <div className="mini-document"><span>CLAUSE 12.2</span><i /><i /><i /><b><Check size={12} /> Source matched</b><div className="document-scan" /></div> : index === 1 ? <div className="mini-timeline"><div className="timeline-progress" /><span><i />Today</span><span><i />30 days</span><span><i />60 days</span><b>Renewal approaching</b></div> : <div className="mini-approval"><span><ShieldCheck size={19} />Review complete</span><div><i /><i /><i /></div><b><Check size={13} /> Ready for your approval</b></div>}</div>
    <small className="feature-kicker">{item.label}</small><h3>{item.title}</h3><p>{item.text}</p><ArrowUpRight className="feature-corner" size={18} aria-hidden="true" />
  </motion.article>)}</div>;
}
