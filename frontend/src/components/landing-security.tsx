'use client';

import { useId, useRef, useState, type KeyboardEvent } from 'react';
import Link from 'next/link';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { ArrowRight, Check, CheckCheck, FileCheck2, FileText, Fingerprint, LockKeyhole, ShieldCheck, UserCheck } from 'lucide-react';

const controls = [
  { id: 'evidence', icon: FileCheck2, title: 'Follow every finding to its source.', description: 'Keep the original clause a click away.' },
  { id: 'approval', icon: UserCheck, title: 'Make the final decision yourself.', description: 'Review and approve before anything is sent or applied.' },
  { id: 'access', icon: Fingerprint, title: 'Keep access with the right people.', description: 'Your company workspace, with clear roles and permissions.' }
] as const;
type Control = typeof controls[number]['id'];

export function LandingSecurity({ onExplore }: { onExplore: () => void }) {
  const [active, setActive] = useState<Control>('evidence');
  const reduced = useReducedMotion();
  const prefix = useId();
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  function navigate(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let next = index;
    if (event.key === 'ArrowDown' || event.key === 'ArrowRight') next = (index + 1) % controls.length;
    else if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') next = (index + controls.length - 1) % controls.length;
    else if (event.key === 'Home') next = 0;
    else if (event.key === 'End') next = controls.length - 1;
    else return;
    event.preventDefault(); setActive(controls[next].id); tabs.current[next]?.focus();
  }
  return <section id="security" className="trust-section" aria-labelledby={prefix + '-heading'}>
    <div className="trust-section-inner">
      <motion.div className="trust-copy" initial={{ opacity: 0, y: reduced ? 0 : 18 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: .2 }} transition={{ duration: .5 }}>
        <span className="trust-eyebrow"><ShieldCheck size={15} />TRUST, BUILT INTO THE WORKFLOW</span>
        <h2 id={prefix + '-heading'}>A clear source.<br /><span>A human decision.</span></h2>
        <p className="trust-intro">Your agreements carry real consequences. Odin keeps the evidence visible and the important decisions in your hands.</p>
        <div className="trust-controls" role="tablist" aria-label="Explore Odin's controls" aria-orientation="vertical">
          {controls.map((control, index) => <button key={control.id} ref={element => { tabs.current[index] = element; }} role="tab" id={prefix + '-tab-' + control.id} aria-controls={prefix + '-panel'} aria-selected={active === control.id} tabIndex={active === control.id ? 0 : -1} className={'trust-control ' + (active === control.id ? 'is-active' : '')} onClick={() => setActive(control.id)} onKeyDown={event => navigate(event, index)}>
            <span className="trust-control-icon"><control.icon size={20} strokeWidth={1.7} /></span><span><strong>{control.title}</strong><small>{control.description}</small></span><ArrowRight size={15} className="trust-control-arrow" />
          </button>)}
        </div>
        <div className="trust-cta"><Link href="/auth/sign-up" className="button button-primary">Create your workspace<ArrowRight size={15} /></Link><button onClick={onExplore} className="trust-demo-link">Explore the demo<ArrowRight size={14} /></button></div>
      </motion.div>
      <motion.div className="trust-preview-wrap" initial={{ opacity: 0, y: reduced ? 0 : 25 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: .2 }} transition={{ duration: .6, delay: .1 }}>
        <div className="trust-preview" role="tabpanel" id={prefix + '-panel'} aria-labelledby={prefix + '-tab-' + active} tabIndex={0}>
          <div className="trust-preview-top"><span className="trust-mini-logo">O</span><span>CONTROL, AT EVERY STEP</span><span className="trust-example-label">Example workflow</span></div>
          <AnimatePresence mode="wait" initial={false}><motion.div key={active} className="trust-preview-content" initial={{ opacity: 0, y: reduced ? 0 : 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: reduced ? 0 : -6 }} transition={{ duration: reduced ? 0 : .2 }}>
            {active === 'evidence' && <><div className="trust-record-header"><span className="trust-record-icon"><FileText size={22} /></span><div><small>ORIGINAL AGREEMENT</small><h3>Cobalt Systems MSA</h3></div><span className="trust-version">v.01</span></div><div className="trust-clause"><div><span aria-label="Section 12.2" title="Section 12.2">§ 12.2</span><small>RENEWAL TERMS</small></div><blockquote>This Agreement shall renew for a further twelve months unless either party provides written notice <mark>at least sixty days</mark> before the renewal date.</blockquote><div className="trust-clause-footer"><FileCheck2 size={14} /><span>Original clause attached to the finding</span></div></div><div className="trust-finding"><span className="trust-blue-dot" /><div><small>LINKED FINDING</small><strong>Renewal notice needs a decision.</strong><p>Review the notice window with the source in view.</p></div></div><div className="trust-preview-note"><CheckCheck size={16} /><p>See the clause behind the recommendation.</p></div></>}
            {active === 'approval' && <><div className="trust-record-header"><span className="trust-record-icon"><UserCheck size={22} /></span><div><small>ACTION REVIEW</small><h3>Notice of non-renewal</h3></div><span className="trust-review-label">Draft</span></div><div className="trust-letter"><span>To: Legal team · Cobalt Systems</span><strong>Re: Master Service Agreement</strong><div aria-hidden="true"><i /><i /><i /><i /></div><span className="trust-reference-tag"><FileText size={12} />Clause 12.2 referenced</span></div><div className="trust-approval-flow"><div className="completed"><span><Check size={13} /></span><strong>Draft prepared</strong></div><i /><div className="current"><span><UserCheck size={14} /></span><strong>Your approval</strong></div><i /><div><span><LockKeyhole size={13} /></span><strong>Send notice</strong></div></div><div className="trust-preview-note trust-note-amber"><LockKeyhole size={16} /><p>Sending stays locked until an administrator approves.</p></div></>}
            {active === 'access' && <><div className="trust-record-header"><span className="trust-record-icon"><Fingerprint size={22} /></span><div><small>COMPANY WORKSPACE</small><h3>Northstar Labs</h3></div><span className="trust-version"><ShieldCheck size={14} /></span></div><div className="trust-member"><span className="trust-member-avatar">NS</span><div><strong>Your company team</strong><small>Signed in to the workspace</small></div><span className="trust-role-label">Administrator</span></div><div className="trust-permissions">{[{ label: 'Review contracts and findings',icon: FileCheck2 },{ label: 'Approve or reject a draft',icon: UserCheck },{ label: 'Send approved notices',icon: CheckCheck }].map(item => <div key={item.label}><item.icon size={16} /><span>{item.label}</span><Check size={15} /></div>)}</div><div className="trust-preview-note"><ShieldCheck size={16} /><p>Company access and action permissions stay explicit.</p></div></>}
          </motion.div></AnimatePresence>
        </div>
        <div className="trust-preview-caption"><span /><p>Evidence. Review. Accountability.</p><span /></div>
      </motion.div>
    </div>
  </section>;
}
