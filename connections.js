// Links refer to original documents. Old documents need no migration.
const COLLECTIONS=new Set(['todos','projects','notes','refs','ents','moms','logs','exps','fbk']);
const LABELS={todos:'할 일·일정',projects:'프로젝트',notes:'글',refs:'자료',ents:'업체·항목',moms:'기록',logs:'메모',exps:'지출',fbk:'피드백'};
export function connectionRef(value){
 if(!value||!COLLECTIONS.has(value.c)||typeof value.id!=='string'||!value.id||value.id.length>1500||/[\/\u0000-\u001f]/.test(value.id))return null;
 if(value.day&&(!/^\d{4}-\d{2}-\d{2}$/.test(value.day)||value.c!=='notes'))return null;
 return {c:value.c,id:value.id,...(value.day?{day:value.day}:{})};
}
export const connectionKey=ref=>JSON.stringify([ref.c,ref.id,ref.day||'']);
export function createConnections(host){
 const {D,plain,getLogs,getSpace,isEvent,dayExists}=host;
 let cached=null,indexed=null;
 function raw(ref){if(ref.c==='logs')return D.logs[ref.id];if(!indexed)indexed=new Map([...COLLECTIONS].filter(c=>c!=='logs').map(c=>[c,new Map((D[c]||[]).map(row=>[row.id,row]))]));return indexed.get(ref.c)?.get(ref.id);}
 function node(value){
  const ref=connectionRef(value);if(!ref)return null;const row=raw(ref);if(!row||row.isFolder||ref.c==='ents'&&!D.projects.some(p=>p.id===row.pid))return null;
  const space=getSpace(ref,row)==='life'?'life':'work';let title,body,date,pid=row.projectId||row.pid||'';
  if(ref.day){const log=getLogs(space)[ref.day];if(!log||log.src.nid!==ref.id)return null;title=ref.day+' '+(space==='life'?'일기':'업무일지');body=plain(log.html);date=ref.day;}
  else {if(ref.c==='notes'&&row.log)return null;if(ref.c==='logs'&&!['memo_work','memo_life'].includes(ref.id))return null;
   title=ref.c==='moms'?(String(row.t||plain(row.h)||'사진 기록').split('\n').find(line=>line.trim())||'기록'):row.title||row.name||row.t||(ref.c==='logs'?'잊지 말 것':LABELS[ref.c]);
   body=plain(row.html||row.h||row.memoH||row.noteH||'')||row.memo||row.note||row.n||row.text||'';
   date=row.date||row.d||(row.created?host.date(row.created):'');
  }
  const label=ref.day?(space==='life'?'일기':'업무일지'):ref.c==='todos'?(isEvent(row)?'일정':'할 일'):LABELS[ref.c];
  return {ref,key:connectionKey(ref),row,space,pid,title:String(title),body:String(body),date:typeof date==='string'?date:'',label,detail:ref.c==='exps'?Number(host.expenseAmount(row)).toLocaleString('ko-KR')+'원':''};
 }
 function storedEdges(ref,row){return (Array.isArray(row.connections)?row.connections:[]).filter(edge=>edge?.sourceId===ref.id&&(edge.sourceDay||'')===(ref.day||'')).map(connectionRef).filter(Boolean);}
 function graph(){
  if(cached)return cached;const nodes=new Map(),links=new Map();
  const put=ref=>{const n=node(ref);if(n){nodes.set(n.key,n);links.set(n.key,new Map());}};
  for(const c of COLLECTIONS){if(c==='logs')continue;for(const row of D[c]||[])if(!(c==='notes'&&row.log))put({c,id:row.id});}
  for(const space of ['work','life'])for(const [day,log] of Object.entries(getLogs(space)))put({c:'notes',id:log.src.nid,day});
  for(const id of ['memo_work','memo_life'])if(D.logs[id])put({c:'logs',id});
  const pair=(aRef,bRef,reason,manual=false)=>{const a=nodes.get(connectionKey(aRef)),b=nodes.get(connectionKey(bRef));if(!a||!b||a.key===b.key||a.space!==b.space)return;
   for(const [from,to] of [[a,b],[b,a]]){const before=links.get(from.key).get(to.key);links.get(from.key).set(to.key,{node:to,manual:manual||!!before?.manual,reasons:[...new Set([...(before?.reasons||[]),reason])],implicit:!manual||!!before?.implicit});}
  };
  for(const n of nodes.values()){
   for(const ref of storedEdges(n.ref,n.row))pair(n.ref,ref,'직접 연결',true);
   if(n.pid)pair(n.ref,{c:'projects',id:n.pid},'같은 프로젝트');
   if(n.ref.c==='todos'&&n.row.eid)pair(n.ref,{c:'ents',id:n.row.eid},'업체·항목 연결');
   if(n.ref.c==='exps'){
    if(n.row.tid)pair(n.ref,{c:'todos',id:n.row.tid},'할 일에 쓴 비용');
    const eid=host.expenseRowId(n.row);if(eid)pair(n.ref,{c:'ents',id:eid},'업체·항목 연결');
   }
  }
  // A diary day is a view of its original monthly note, not a copied entry.
  const days=new Map();for(const n of nodes.values())if(n.ref.day)days.set(n.space+':'+n.ref.day,n.ref);
  for(const n of nodes.values())if(!n.ref.day&&['todos','moms','notes','exps','fbk'].includes(n.ref.c)&&n.date){const day=days.get(n.space+':'+n.date);if(day)pair(n.ref,day,'같은 날');}
  cached={nodes,links};return cached;
 }
 function neighbors(ref){return [...(graph().links.get(connectionKey(ref))?.values()||[])].sort((a,b)=>Number(b.manual)-Number(a.manual)||(b.node.date||'').localeCompare(a.node.date||'')||a.node.title.localeCompare(b.node.title));}
 const edge=(from,to)=>({...to,sourceId:from.id,...(from.day?{sourceDay:from.day}:{})});
 const matches=(entry,from,to)=>entry?.sourceId===from.id&&(entry.sourceDay||'')===(from.day||'')&&connectionRef(entry)&&connectionKey(connectionRef(entry))===connectionKey(to);
 function usable(ref,row){if(!row||row.isFolder||(ref.day&&!dayExists(row,ref.day))||(ref.c==='notes'&&row.log&&!ref.day))throw new Error('원본 항목을 찾지 못했어요. 삭제되었는지 확인해 주세요.');}
 async function change(aValue,bValue,remove=false){
  const a=connectionRef(aValue),b=connectionRef(bValue);if(!a||!b||connectionKey(a)===connectionKey(b))throw new Error('다른 항목을 선택해 주세요.');
  const uid=host.uid();if(!uid)throw new Error('로그인을 확인해 주세요.');
  const changes=await host.transaction(async tx=>{
   const docs=new Map();for(const ref of [a,b]){const key=ref.c+':'+ref.id;if(!docs.has(key)){const dbRef=host.ref(uid,ref.c,ref.id),snap=await tx.get(dbRef);docs.set(key,{ref,dbRef,row:snap.exists()?snap.data():null});}}
   const aRow=docs.get(a.c+':'+a.id).row,bRow=docs.get(b.c+':'+b.id).row;usable(a,aRow);if(!remove)usable(b,bRow);
   if(bRow&&getSpace(a,aRow)!==getSpace(b,bRow))throw new Error('WORK와 LIFE는 같은 공간 안에서 연결해 주세요.');
   for(const [from,to] of [[a,b],[b,a]]){const record=docs.get(from.c+':'+from.id);if(!record.row)continue;
    const existing=Array.isArray(record.row.connections)?record.row.connections:[],list=existing.filter(entry=>!matches(entry,from,to));
    if(!remove)list.push(edge(from,to));record.row={...record.row,connections:list};
   }
   for(const record of docs.values())if(record.row)tx.update(record.dbRef,{connections:record.row.connections});
   return [...docs.values()].filter(record=>record.row).map(record=>({ref:record.ref,connections:record.row.connections}));
  });
  if(host.uid()===uid)for(const item of changes){const row=raw(item.ref);if(row)row.connections=item.connections;}
  cached=null;indexed=null;host.changed();
 }
 async function create(c,data,origin){
  const source=connectionRef(origin);if(!source||!['todos','moms'].includes(c))throw new Error('연결할 원본을 확인해 주세요.');
  const uid=host.uid();if(!uid)throw new Error('로그인을 확인해 주세요.');const target=host.newRef(uid,c),ref={c,id:target.id};
  const result=await host.transaction(async tx=>{
   const sourceRef=host.ref(uid,source.c,source.id),snap=await tx.get(sourceRef);const fresh=snap.exists()?snap.data():null;usable(source,fresh);
   if(getSpace(source,fresh)!==getSpace(ref,data))throw new Error('원본과 같은 공간에서 만들어 주세요.');
   const connections=[...(Array.isArray(fresh.connections)?fresh.connections:[]),edge(source,ref)],value={...data,connections:[edge(ref,source)]};
   tx.set(target,value);tx.update(sourceRef,{connections});return {value,connections};
  });
  if(host.uid()===uid){const row=raw(source);if(row)row.connections=result.connections;if(!D[c].some(row=>row.id===ref.id))D[c].push({id:ref.id,...result.value});}
  cached=null;indexed=null;host.changed();return {id:ref.id,...result.value};
 }
 function projectFor(ref){const n=node(ref);if(!n)return '';if(ref.c==='projects')return ref.id;if(n.pid&&node({c:'projects',id:n.pid})?.space===n.space)return n.pid;const projects=neighbors(ref).filter(link=>link.node.ref.c==='projects');return projects.length===1?projects[0].node.ref.id:'';}
 return {node,neighbors,graph,projectFor,connect:(a,b)=>change(a,b),disconnect:(a,b)=>change(a,b,true),create,invalidate:()=>{cached=null;indexed=null;},key:connectionKey,ref:connectionRef};
}
