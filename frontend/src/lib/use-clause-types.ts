'use client';
import { useEffect,useState } from 'react';
import { useWorkspace } from '@/components/providers';
import { indexClauseTypes,list,record,text } from './api';
export function useClauseTypes(contractIds:string[],enabled:boolean) {
 const {request,revision} = useWorkspace();
 const key=enabled?JSON.stringify([...new Set(contractIds)].sort()):'';
 const [retry,setRetry]=useState(0);
 const [state,setState]=useState<{key:string;index:Record<string,string>;loading:boolean;error:string}>({key:'',index:{},loading:false,error:''});
 useEffect(()=>{
  if(!enabled){setState({key:'',index:{},loading:false,error:''});return;}
  const ids:string[]=JSON.parse(key);let active=true;const controller=new AbortController();
  setState(previous=>({key,index:previous.key===key?previous.index:{},loading:Boolean(ids.length),error:''}));
  if(ids.length)void Promise.allSettled(ids.map(async id=>{
   const contract=record(await request('/api/contracts/'+encodeURIComponent(id),{signal:controller.signal}));
   if(!Array.isArray(contract.clauses))throw new Error('Clause types were not supplied for '+id+'.');
   return {id,clauses:list(contract.clauses)};
  })).then(results=>{
   if(!active)return;
   const failed=results.filter(r=>r.status==='rejected');
   const contracts=results.flatMap(r=>r.status==='fulfilled'?[r.value]:[]);
   setState({key,index:indexClauseTypes(contracts),loading:false,error:failed.length?'Could not load clause types for '+failed.length+' contract(s). Retry the view.':''});
  });
  return()=>{active=false;controller.abort();};
 },[key,enabled,request,revision,retry]);
 const visible=state.key===key?state:{key,index:{},loading:enabled,error:''};
 return {...visible,reload:()=>setRetry(v=>v+1)};
}
