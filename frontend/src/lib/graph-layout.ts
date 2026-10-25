import dagre from '@dagrejs/dagre';
import type {Graph} from './api';
export function layoutGraph(graph:Graph) {
 const layout=new dagre.graphlib.Graph({multigraph:true});
 layout.setGraph({rankdir:'LR',nodesep:40,ranksep:95,edgesep:25,marginx:35,marginy:35,ranker:'network-simplex'});
 layout.setDefaultEdgeLabel(()=>({}));
 for(const node of graph.nodes)layout.setNode(node.id,{width:node.type==='party'?220:260,height:node.type==='party'?106:142});
 graph.edges.forEach((edge,i)=>layout.setEdge(edge.source,edge.target,{weight:['contains','party_to'].includes(edge.kind)?3:1},String(i)));
 dagre.layout(layout);
 return graph.nodes.map(node=>{const position=layout.node(node.id);return {...node,position:{x:position.x-position.width/2,y:position.y-position.height/2}};});
}
