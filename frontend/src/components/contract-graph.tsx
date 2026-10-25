'use client';
import { useEffect,useMemo,useRef,useState } from 'react';
import Link from 'next/link';
import { Background,Controls,Handle,MarkerType,MiniMap,Position,ReactFlow,ReactFlowProvider,useNodesState,useReactFlow,type Node,type NodeProps,type Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Building2,FileText,Focus,Layers3,Search,ArrowUpRight,GitBranch,RotateCcw,MousePointer2,ArrowRight,Network } from 'lucide-react';
import { motion,useReducedMotion } from 'motion/react';
import { useResource } from '@/lib/use-resource';
import { cascadeNodeIds,query,text,record,list,type Graph,type GraphNode } from '@/lib/api';
import { layoutGraph } from '@/lib/graph-layout';
import { useTheme } from './theme-provider';
import { Badge,Button,Panel } from './ui';
import { CitationChip,ResourceState,SourceBadge,Status } from './api-ui';

type FlowNode=Node<{label:string;kind:string;raw:GraphNode;connections:number},'intelligence'>;
const edgeNames:Record<string,string>={conflicts_with:'Conflict',depends_on:'Dependency',supersedes:'Supersedes',governs:'Governs',party_to:'Party to',contains:'Contains'};
function IntelligenceNode({data,selected}:NodeProps<FlowNode>) {
 const Icon=data.kind==='party'?Building2:data.kind==='clause'?Layers3:FileText;
 const reference=data.raw.clause_number;
 return <div className={'map-node map-node-'+data.kind+(selected?' is-selected':'')}>
  <Handle type="target" position={Position.Left}/><div className="map-node-top"><span className="map-node-icon"><Icon size={17} strokeWidth={1.7}/></span><small>{data.kind==='clause'?'CONTRACT CLAUSE':data.kind==='party'?'PARTY':'AGREEMENT'}</small>{data.kind==='clause'&&reference?<b title={"Section " + text(reference)}>§{text(reference)}</b>:<ArrowUpRight size={13}/>}</div>
  <strong>{data.label}</strong><footer><span><i/>{data.connections} connection{data.connections===1?'':'s'}</span>{data.raw.version?<span>v{text(data.raw.version)}</span>:null}</footer><Handle type="source" position={Position.Right}/>
 </div>;
}
const nodeTypes={intelligence:IntelligenceNode};
function Workspace() {
 const {theme}=useTheme();const dark=theme==='dark';
 const r=useResource<Graph>('/api/graph');const graph=r.data;
 const [kind,setKind]=useState('');const [search,setSearch]=useState('');const [selected,setSelected]=useState('');const [edgeId,setEdgeId]=useState('');const [cascade,setCascade]=useState('');
 const flow=useReactFlow();const reduced=useReducedMotion();const fitted=useRef(false);
 const initial=useMemo<FlowNode[]>(()=>graph?layoutGraph(graph).map(n=>({id:n.id,type:'intelligence',position:n.position,data:{label:n.label,kind:n.type,raw:n,connections:graph.edges.filter(e=>e.source===n.id||e.target===n.id).length}})):[],[graph]);
 const [nodes,setNodes,onNodesChange]=useNodesState<FlowNode>(initial);
 useEffect(()=>{setNodes(old=>initial.map(n=>({...n,position:old.find(o=>o.id===n.id)?.position??n.position})));},[initial,setNodes]);
 useEffect(()=>{if(!nodes.length||fitted.current)return;fitted.current=true;const timer=setTimeout(()=>void flow.fitView({duration:reduced?0:400,padding:.16,maxZoom:1}),80);return()=>clearTimeout(timer);},[nodes.length,flow,reduced]);
 const rawEdges=graph?.edges??[];const cascadeIds=cascadeNodeIds(graph??{nodes:[],edges:[]},cascade);
 const chosen=rawEdges.filter(e=>!kind||e.kind===kind);const connected=new Set(chosen.flatMap(e=>[e.source,e.target]));
 const matching=new Set(nodes.filter(n=>!search||(n.data.label+' '+text(n.data.raw.contract_id,'')).toLowerCase().includes(search.toLowerCase())).map(n=>n.id));
 // Keep a search result's immediate neighbours visible so relationships remain legible.
 const context=new Set([...matching,...(search?rawEdges.filter(e=>matching.has(e.source)||matching.has(e.target)).flatMap(e=>[e.source,e.target]):[])]);
 const visible=nodes.filter(n=>(!kind||connected.has(n.id))&&context.has(n.id)).map(n=>({...n,selected:n.id===selected,style:{opacity:cascade&&!cascadeIds.has(n.id)?.25:search&&!matching.has(n.id)?.5:1}}));
 const visibleIds=new Set(visible.map(n=>n.id));
 const edges:Edge[]=chosen.map(e=>{
  const eid='edge-'+rawEdges.indexOf(e);const conflict=e.kind==='conflicts_with';const dependency=e.kind==='depends_on';const active=eid===edgeId;const highlighted=cascadeIds.has(e.source)&&cascadeIds.has(e.target)&&dependency;const color=conflict?(dark?'#f08d7e':'#c9504d'):dependency?(dark?'#d8af72':'#ad7b38'):active?(dark?'#8db6ff':'#3166cd'):(dark?'#6a809e':'#a5b7ce');
  return {id:eid,source:e.source,target:e.target,type:'smoothstep',label:conflict||dependency||active?edgeNames[e.kind]??e.kind:undefined,animated:conflict&&!reduced,style:{stroke:color,strokeWidth:active||highlighted?2.8:conflict||dependency?1.8:1.3,strokeDasharray:conflict?'6 4':undefined,opacity:cascade&&!highlighted?.2:1},markerEnd:{type:MarkerType.ArrowClosed,color,width:15,height:15},labelStyle:{fontSize:10,fontWeight:600,fill:dark?(conflict?'#f4b1a2':dependency?'#efd09a':'#c2d4ed'):(conflict?'#a33f39':dependency?'#8b612c':'#3e608d')},labelBgStyle:{fill:dark?(conflict?'#3b272a':dependency?'#342d23':'#1b2635'):(conflict?'#fff2ee':dependency?'#fff7e9':'#fff')},labelBgPadding:[7,4] as [number,number],labelBgBorderRadius:5};
 }).filter(e=>visibleIds.has(e.source)&&visibleIds.has(e.target));
 const node=graph?.nodes.find(n=>n.id===selected);const edge=edgeId?rawEdges[Number(edgeId.slice(5))]:undefined;
 const related=rawEdges.filter(e=>e.source===selected||e.target===selected);
 const name=(id:string)=>graph?.nodes.find(n=>n.id===id)?.label??id;
 const fit=()=>void flow.fitView({duration:reduced?0:400,padding:.16,maxZoom:1.1});
 function reset(){setSearch('');setKind('');setCascade('');setNodes(initial);requestAnimationFrame(fit);}
 return <ResourceState resource={r} empty={Boolean(graph&&!graph.nodes.length)}><div className="map-workspace"><Panel className="map-panel"><div className="map-heading"><span className="map-heading-icon"><Network size={20}/></span><div><strong>Contract network</strong><small>Follow connections between agreements, parties and clauses</small></div><span className="map-count">{visible.length} nodes · {edges.length} links</span></div>
  <div className="map-toolbar"><label className="map-search"><Search size={15}/><input aria-label="Search the contract graph" placeholder="Find a contract, clause or party…" value={search} onChange={e=>setSearch(e.target.value)}/></label><select className="compact-select" aria-label="Filter relationships" value={kind} onChange={e=>setKind(e.target.value)}><option value="">All relationships</option>{[...new Set(rawEdges.map(e=>e.kind))].map(k=><option key={k} value={k}>{edgeNames[k]??k}</option>)}</select><button onClick={fit} className="map-tool"><Focus size={15}/>Fit</button><button onClick={reset} className="map-tool"><RotateCcw size={14}/>Reset</button></div>
  {Object.keys(graph?.cascades??{}).length>0&&<label className="map-cascade">Explore downstream impact<select value={cascade} onChange={e=>setCascade(e.target.value)}><option value="">Choose an agreement</option>{Object.keys(graph?.cascades??{}).map(root=><option key={root} value={root}>{name('c:'+root)}</option>)}</select>{cascade&&<small>{cascadeIds.size-1} downstream agreements</small>}</label>}
  <div className="map-canvas"><ReactFlow<FlowNode> colorMode={theme} nodes={visible} edges={edges} nodeTypes={nodeTypes} onNodesChange={onNodesChange} onNodeClick={(_,n)=>{setSelected(n.id);setEdgeId('');}} onEdgeClick={(_,e)=>{setEdgeId(e.id);setSelected('');}} onPaneClick={()=>{setSelected('');setEdgeId('');}} fitView fitViewOptions={{padding:.16,maxZoom:1}} minZoom={.12} maxZoom={1.8} nodesConnectable={false} deleteKeyCode={null}><Background gap={22} size={1} color="var(--graph-dot)"/><Controls showInteractive={false}/><MiniMap pannable zoomable nodeColor={n=>n.data.kind==='party'?'#7fa99a':n.data.kind==='clause'?'#d3ad74':'#7399d6'} maskColor="var(--graph-mask)"/></ReactFlow>{!visible.length&&<div className="map-no-results"><Search size={23}/><strong>No matching connections</strong><button onClick={reset}>Clear filters</button></div>}<span className="map-interaction-hint"><MousePointer2 size={12}/>Drag to arrange · scroll to zoom</span></div>
  <div className="map-legend"><span><i className="map-key-contract"/>Agreement</span><span><i className="map-key-clause"/>Clause</span><span><i className="map-key-party"/>Party</span><span><b className="map-key-dependency"/>Dependency</span><span><b className="map-key-conflict"/>Conflict</span></div>
 </Panel><motion.aside key={selected||edgeId||'none'} className="map-inspector" initial={{opacity:0,x:reduced?0:6}} animate={{opacity:1,x:0}} transition={{duration:.18}}><div className="map-inspector-label"><GitBranch size={14}/>CONNECTION DETAILS</div>{node?<><span className={'map-inspector-icon map-icon-'+node.type}>{node.type==='party'?<Building2 size={26}/>:node.type==='clause'?<Layers3 size={26}/>:<FileText size={26}/>}</span><Badge>{node.type==='contract'?'Agreement':node.type}</Badge><h2>{node.label}</h2><p>{node.type==='contract'?'Inspect the agreement and follow its related clauses.':node.type==='clause'?'Open the original clause to inspect its source.':'Explore the agreements connected to this party.'}</p>
 <div className="map-facts"><span>Connections<strong>{related.length}</strong></span>{node.version?<span>Version<strong>{text(node.version)}</strong></span>:null}</div>
 {node.type==='contract'&&<Link className="button button-primary full-width" href={query('/dashboard/contracts',{contract:text(node.contract_id??node.id.replace(/^c:/,''))})}>Open agreement<ArrowUpRight size={14}/></Link>}
 {node.type==='clause'&&<CitationChip value={node.citation??{contract_id:node.contract_id,clause_number:node.clause_number,version:node.version}}/>}
 {node.text||node.quote?<blockquote className="source-quote">{text(node.text??node.quote)}<SourceBadge value={node.source}/></blockquote>:null}
 <h3 className="map-related-title">Connected records</h3><div className="map-related">{related.slice(0,6).map((e,i)=><button key={i} onClick={()=>{setSelected('');setEdgeId('edge-'+rawEdges.indexOf(e));}}><span><small>{edgeNames[e.kind]??e.kind}</small><strong>{name(e.source===selected?e.target:e.source)}</strong></span><ArrowRight size={14}/></button>)}</div></>:edge?<><span className="map-inspector-icon map-icon-clause"><GitBranch size={26}/></span>{edge.severity!==undefined&&<Status value={edge.severity} severity/>}<h2>{edgeNames[edge.kind]??edge.kind}</h2><div className="map-edge-path"><strong>{name(edge.source)}</strong><ArrowRight size={15}/><strong>{name(edge.target)}</strong></div><SourceBadge value="analysis"/><h3 className="map-related-title">Why this connection matters</h3><p>{edge.reason??'Open the linked records to inspect this relationship.'}</p>{edge.finding_id&&<Link className="button button-secondary full-width" href={query('/dashboard/agent-review',{finding:edge.finding_id})}>Inspect the debate<ArrowUpRight size={14}/></Link>}<Button variant="ghost" onClick={()=>{setSelected(edge.target);setEdgeId('');}}>Inspect connected record<ArrowRight size={14}/></Button></>:<div className="map-inspector-empty"><span><MousePointer2 size={29} strokeWidth={1.4}/></span><h2>Follow a connection.</h2><p>Select an agreement, clause or relationship to see the details here.</p><div><FileText size={15}/><span>Agreement details</span></div><div><Layers3 size={15}/><span>Original clause references</span></div><div><GitBranch size={15}/><span>Dependencies and conflicts</span></div></div>}</motion.aside></div></ResourceState>;
}
export function ContractGraph(){return <ReactFlowProvider><Workspace/></ReactFlowProvider>;}
