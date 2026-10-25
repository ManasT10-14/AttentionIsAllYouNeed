const googleButton = document.querySelector('.google');
googleButton.innerHTML = `<svg width="20" height="20" viewBox="0 0 48 48" aria-hidden="true"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5Z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65Z"/><path fill="#FBBC05" d="M10.53 28.59a14.4 14.4 0 0 1 0-9.18l-7.98-6.19A23.86 23.86 0 0 0 0 24c0 3.87.93 7.53 2.56 10.78l7.97-6.19Z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.9-5.8l-7.73-6c-2.15 1.45-4.92 2.3-8.17 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48Z"/></svg><span>Continue with Google</span>`;
googleButton.insertAdjacentHTML('afterend', '<p class="auth-note">Design preview · authentication is not connected yet.</p>');
document.querySelector('.close').setAttribute('aria-label', 'Close sign-in dialog');
document.addEventListener('keydown', (event) => { if (event.key === 'Escape') closeAuth(); });

const graphNodes = [
  { id: 'northstar', type: 'party', x: 24, y: 106, label: 'Northstar Labs', detail: 'Party · linked to both sample contracts.' },
  { id: 'cobalt', type: 'contract', x: 230, y: 40, label: 'Cobalt MSA', detail: 'Contract · renewal obligation depends on delivery of written notice under clause 12.2.' },
  { id: 'orbital', type: 'contract', x: 230, y: 210, label: 'Orbital Services', detail: 'Contract · service credits and claims are governed by clause 8.4.' },
  { id: 'renewal', type: 'clause', x: 462, y: 40, label: 'Clause 12.2', detail: 'Sample source: “This Agreement shall renew unless either party provides written notice.” Notice timing requires review.' },
  { id: 'credits', type: 'clause', x: 462, y: 210, label: 'Clause 8.4', detail: 'Sample analysis: service-credit claim deadlines may conflict with the notice delivery workflow. This is a demonstration finding.' },
  { id: 'supplier', type: 'party', x: 668, y: 106, label: 'Cobalt Systems', detail: 'Party · counterparty to the Cobalt master service agreement.' }
];
function graphMarkup(prefix) {
  return `<svg class="contract-graph" viewBox="0 0 850 300" aria-label="Sample contract graph with selectable contracts, clauses and parties">
    <path class="edge" d="M174 130L230 64M174 130L230 234M380 64H462M380 234H462M612 64L668 130"/>
    <path class="edge conflict" d="M537 88V210"/><text class="edge-label" x="550" y="152">conflict</text>
    <text class="edge-label" x="398" y="54">depends on</text>
    ${graphNodes.map(node => `<g class="node ${node.type}" tabindex="0" role="button" data-graph-node="${node.id}" data-evidence="${prefix}" aria-label="${node.type}: ${node.label}" transform="translate(${node.x},${node.y})"><rect width="150" height="48" rx="9"/><text x="75" y="29" text-anchor="middle">${node.label}</text></g>`).join('')}
  </svg><div class="graph-legend"><span>Lavender · party</span><span>White · contract</span><span>Sand · clause</span><span>Dashed red · conflict</span></div><div class="graph-evidence" id="${prefix}" aria-live="polite"><strong>Inspect a connection</strong>Select a node to view its source or relationship. Sample data shown.</div>`;
}
const overviewGraph = document.createElement('article');
overviewGraph.className = 'panel graph-overview';
overviewGraph.innerHTML = `<div class="graph-heading"><div><h2>Contract graph</h2><p>Explore contracts, clauses, parties, and conflicts.</p></div><button class="secondary" onclick="showView('map')">Open full graph →</button></div>${graphMarkup('overview-evidence')}`;
document.querySelector('#overview .stats').insertAdjacentElement('afterend', overviewGraph);
overviewGraph.style.marginBottom = '18px';

const originalShowView = showView;
showView = function(name) {
  originalShowView(name);
  const labels = { overview: 'Overview', contracts: 'Contracts', timeline: 'Timeline', map: 'Risk map', review: 'Agent review', actions: 'Actions' };
  document.querySelector('.breadcrumb b').textContent = labels[name];
  document.querySelectorAll('.nav button').forEach(button => button.classList.toggle('active', button.textContent.includes(labels[name])));
  if (name === 'map') {
    const canvas = document.querySelector('.map-canvas');
    canvas.className = 'panel';
    canvas.innerHTML = graphMarkup('map-evidence');
    document.querySelector('.map-key').remove();
  }
  document.querySelector('.main').scrollTop = 0;
};
function selectGraphNode(target) {
  const node = graphNodes.find(item => item.id === target.dataset.graphNode);
  target.closest('svg').querySelectorAll('.node').forEach(item => item.classList.toggle('selected', item === target));
  const evidence = document.getElementById(target.dataset.evidence);
  evidence.replaceChildren();
  const heading = document.createElement('strong');
  heading.textContent = node.label;
  evidence.append(heading, document.createTextNode(node.detail));
}
document.addEventListener('click', (event) => {
  const node = event.target.closest('[data-graph-node]');
  if (node) selectGraphNode(node);
});
document.addEventListener('keydown', (event) => {
  const node = event.target.closest('[data-graph-node]');
  if (node && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); selectGraphNode(node); }
});
