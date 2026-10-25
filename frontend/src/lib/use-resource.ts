'use client';
import { useCallback,useEffect,useState } from 'react';
import { useWorkspace } from '@/components/providers';
import { canReuseSnapshot,snapshotDate } from './resource-state';
type State<T>={path:string|null;data?:T;error:string;loading:boolean};
export function useResource<T=unknown>(path:string|null,delay=0) {
 const {request,revision}=useWorkspace();
 const [state,setState]=useState<State<T>>({path:null,error:'',loading:Boolean(path)});
 const [retry,setRetry]=useState(0);
 useEffect(()=>{
  if(!path){setState({path:null,error:'',loading:false});return;}
  let active=true;const controller=new AbortController();
  setState(previous=>canReuseSnapshot(previous.path,path)?{...previous,error:'',loading:true}:{path,data:undefined,error:'',loading:true});
  const timer=setTimeout(()=>{
   request<T>(path,{signal:controller.signal}).then(data=>{if(active)setState({path,data,error:'',loading:false});}).catch(error=>{if(active)setState(previous=>({...previous,error:error instanceof Error?error.message:'Could not load this view.',loading:false}));});
  },delay);
  return()=>{active=false;clearTimeout(timer);controller.abort();};
 },[path,revision,request,retry,delay]);
 const reuse=canReuseSnapshot(state.path,path);
 const visible=reuse?state:{path,data:undefined,error:'',loading:Boolean(path)};
 return {...visible,loading:visible.loading||(reuse&&state.path!==path&&!state.error),dataDate:snapshotDate(visible.path),stale:reuse&&state.path!==path,reload:useCallback(()=>setRetry(v=>v+1),[])};
}
