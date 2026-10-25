export type HeatCell={contract_id:string;clause_type:string;month:string;amount:number};
export function heatScaleMaximum(cells:HeatCell[],group:'contract'|'type') {
 const sums=new Map<string,number>();
 for(const cell of cells){const key=(group==='contract'?cell.contract_id:cell.clause_type)+'\u0000'+cell.month;sums.set(key,(sums.get(key)??0)+cell.amount);}
 return Math.max(1,...sums.values());
}
export function heatLevel(amount:number,maximum:number) {
 if(amount<=0)return 0;
 const ratio=amount/maximum;
 return ratio<=.2?1:ratio<=.45?2:ratio<=.72?3:4;
}
