/* Pointer-based block movement: the same path handles mouse, pen and touch.
   Document changes are committed once, on a valid drop. */
export function blockFromDOM(view, element) {
 for(let el=element?.nodeType===1?element:element?.parentElement;el&&el!==view.dom;el=el.parentElement){
  if(el.parentElement===view.dom||el.parentElement?.classList.contains('nb-toggle-body')){
   try{const pos=view.posAtDOM(el.parentElement,[...el.parentElement.childNodes].indexOf(el)),node=view.state.doc.nodeAt(pos);if(node&&['paragraph','toggle','image','rule'].includes(node.type.name))return {pos,node,dom:el};}catch(_){}
  }
 }
 return null;
}
// The writing gutter is part of its row. Hovering it must not require first
// crossing the text, and an open toggle's padding is not its title's row.
export function blockFromPoint(view,x,y){
 const host=view.dom.getBoundingClientRect();
 if(x<host.left||x>host.right||y<host.top||y>host.bottom)return null;
 let found=null;
 view.state.doc.descendants((node,pos)=>{
  if(!['paragraph','toggle','image','rule'].includes(node.type.name))return;
  const dom=view.nodeDOM(pos),row=node.type.name==='toggle'?dom?.querySelector('.nb-toggle-title'):dom;
  const rect=row?.getBoundingClientRect();
  if(rect?.width&&rect.height&&x>=rect.left-44&&x<=rect.right&&y>=rect.top&&y<=rect.bottom)found={pos,node,dom};
 });
 return found;
}
export function installBlockMoving(hooks){
 let session=null,frame=0,suppressClickUntil=0;
 function stopFrame(){cancelAnimationFrame(frame);frame=0;}
 function clear(){
  const old=session;if(!old)return;session=null;stopFrame();
  old.marker?.remove();old.ghost?.remove();document.body.classList.remove('nb-moving');
  try{if(old.handle.hasPointerCapture(old.pointerId))old.handle.releasePointerCapture(old.pointerId);}catch(_){}
  hooks.session(null);hooks.refresh(old.view);
 }
 function cancel(){if(!session)return false;suppressClickUntil=Date.now()+500;clear();return true;}
 function insideSource(at){return at>=session.range.from&&at<=session.range.to;}
 function asBlock(view,pos){const dom=view.nodeDOM(pos),node=view.state.doc.nodeAt(pos);return dom?.getBoundingClientRect&&node?{pos,node,dom}:null;}
 function visibleBlocks(view){const rows=[];view.state.doc.descendants((node,pos)=>{if(!['paragraph','toggle','image','rule'].includes(node.type.name))return;const b=asBlock(view,pos);if(b){const rect=b.dom.getBoundingClientRect();if(rect.width&&rect.height)rows.push({...b,rect});}});return rows;}
 function destination(x,y){
  const {view}=session,host=view.dom,rect=host.getBoundingClientRect();
  if(x<rect.left-72||x>rect.right+24||y<rect.top-24||y>rect.bottom+24)return null;
  const hit=document.elementFromPoint(Math.max(rect.left+2,Math.min(rect.right-2,x)),y);
  // The handle sits outside the text block. elementFromPoint there hits a
  // toggle's padding instead of its child; resolve the visible row by geometry.
  let parent=host;
  for(const body of host.querySelectorAll('.nb-toggle-body')){
   const r=body.getBoundingClientRect(),left=r.left+(parseFloat(getComputedStyle(body).paddingLeft)||0);
   if(r.width&&r.height&&y>=r.top-4&&y<=r.bottom+4&&x>=left-28&&x<=r.right+24&&parent.contains(body))parent=body;
  }
  const distance=r=>y<r.top?r.top-y:y>r.bottom?y-r.bottom:0;
  const rows=visibleBlocks(view).filter(b=>b.dom.parentElement===parent);
  // Resolve gaps between paragraphs to the same boundary as their adjacent rows.
  let b=rows.sort((a,b)=>distance(a.rect)-distance(b.rect))[0];
  if(!b)return null;
  // The left gutter is a real drop surface, including when lifting a nested block.
  while(x<b.dom.getBoundingClientRect().left-28){const wrap=b.dom.parentElement?.closest('.nb-toggle');if(!wrap||!host.contains(wrap))break;const parent=blockFromDOM(view,wrap);if(!parent||parent.pos===b.pos)break;b=parent;}
  const r=b.dom.getBoundingClientRect();
  if(b.node.type.name==='toggle'){
   const title=b.dom.querySelector('.nb-toggle-title'),body=b.dom.querySelector('.nb-toggle-body'),tr=title.getBoundingClientRect();
   const overTitle=y>=tr.top+6&&y<=tr.bottom-5&&x>=tr.left+28;
   const overEmptyBody=body?.contains(hit)&&hit===body;
   if(overTitle||overEmptyBody){const at=b.pos+b.node.nodeSize-2;if(insideSource(at)||b.pos>=session.range.from&&b.pos<session.range.to)return null;const br=body?.getBoundingClientRect();return {at,openAt:b.pos,left:r.left+28,top:b.node.attrs.open&&br?.height?br.bottom-1:tr.bottom,width:Math.max(35,r.width-28),label:'토글 안으로 이동'};}
  }
  const before=y<r.top+r.height/2,at=b.pos+(before?0:b.node.nodeSize);
  if(insideSource(at))return null;
  return {at,left:r.left,top:before?r.top:r.bottom,width:r.width,label:''};
 }
 function showTarget(){
  if(!session?.started)return;const d=destination(session.x,session.y);session.target=d;const marker=session.marker;
  marker.hidden=!d;if(d){marker.style.left=Math.max(4,d.left)+'px';marker.style.top=d.top+'px';marker.style.width=Math.max(35,Math.min(d.width,innerWidth-d.left-8))+'px';marker.textContent=d.label;}
  session.ghost.style.left=Math.max(6,Math.min(innerWidth-180,session.x+16))+'px';session.ghost.style.top=Math.max(6,Math.min(innerHeight-44,session.y+16))+'px';
 }
 function begin(){
  session.started=true;suppressClickUntil=Date.now()+500;hooks.closeMenu();document.body.classList.add('nb-moving');
  const marker=document.createElement('div');marker.className='nb-drop-indicator';marker.hidden=true;marker.setAttribute('aria-hidden','true');
  const ghost=document.createElement('div');ghost.className='nb-drag-preview';ghost.setAttribute('aria-hidden','true');
  const first=session.range.nodes[0];ghost.textContent=(session.range.nodes.length>1?session.range.nodes.length+'개 문단 · ':'')+(first.textContent||({image:'사진',rule:'구분선'}[first.type.name])||'문단').slice(0,50);
  session.marker=marker;session.ghost=ghost;document.body.append(marker,ghost);showTarget();frame=requestAnimationFrame(autoScroll);
 }
 function autoScroll(){
  frame=0;if(!session?.started)return;
  const viewport=window.visualViewport,vTop=viewport?.offsetTop||0,vBottom=vTop+(viewport?.height||innerHeight);
  const parents=[];for(let el=session.view.dom;el;el=el.parentElement)if(el.scrollHeight>el.clientHeight+2&&/(auto|scroll)/.test(getComputedStyle(el).overflowY))parents.push(el);
  parents.push(document.scrollingElement);
  for(const el of [...new Set(parents)]){
   const isPage=el===document.scrollingElement,r=isPage?{top:vTop,bottom:vBottom}:el.getBoundingClientRect(),top=Math.max(vTop,r.top),bottom=Math.min(vBottom,r.bottom),edge=Math.min(60,(bottom-top)/4);
   let delta=session.y<top+edge?-Math.min(18,(top+edge-session.y)*.3):session.y>bottom-edge?Math.min(18,(session.y-bottom+edge)*.3):0;
   if(!delta)continue;const old=el.scrollTop;el.scrollTop+=delta;if(el.scrollTop!==old){showTarget();break;}
  }
  frame=requestAnimationFrame(autoScroll);
 }
 function finish(event,canceled=false){
  if(!session||event.pointerId!==session.pointerId)return;const old=session;
  if(canceled){cancel();return;}
  if(!old.started){suppressClickUntil=Date.now()+500;clear();hooks.menu(old.view,old.context);return;}
  event.preventDefault();suppressClickUntil=Date.now()+500;showTarget();
  const target=old.target;const valid=target&&old.view.dom.isConnected&&old.view.state.doc===old.doc;
  // Clear before dispatch so the new block controls can follow the moved selection.
  clear();if(valid)hooks.move(old.view,old.range,{...target,selectBlock:true});
 }
 document.addEventListener('pointerdown',event=>{
  const handle=event.target.closest?.('[data-block-menu]');if(!handle||event.button>0||session)return;
  const context=hooks.context();if(!context?.view.dom.isConnected)return;
  const range=hooks.range(context.view,context.pos);if(!range)return;
  event.preventDefault();event.stopPropagation();
  session={view:context.view,context,range,doc:context.view.state.doc,handle,pointerId:event.pointerId,pointerType:event.pointerType,startX:event.clientX,startY:event.clientY,x:event.clientX,y:event.clientY,started:false,target:null};hooks.session(session);
  try{handle.setPointerCapture(event.pointerId);}catch(_){}
 },true);
 document.addEventListener('pointermove',event=>{
  if(session){if(event.pointerId!==session.pointerId)return;session.x=event.clientX;session.y=event.clientY;const distance=Math.hypot(session.x-session.startX,session.y-session.startY);if(!session.started&&distance>=(session.pointerType==='touch'?9:5))begin();if(session.started){event.preventDefault();showTarget();}return;}
  if(event.pointerType==='touch'||event.buttons||event.target.closest?.('.nb-tools,.nb-menu,.nb-inline'))return;
  const host=event.target.closest?.('.nb-editor'),view=host&&hooks.view(host);if(!view)return;const b=blockFromPoint(view,event.clientX,event.clientY);if(b)hooks.hover(view,b);
 },{passive:false});
 document.addEventListener('pointerup',event=>finish(event));
 document.addEventListener('pointercancel',event=>finish(event,true));
 document.addEventListener('lostpointercapture',event=>{if(session?.pointerId===event.pointerId)cancel();});
 document.addEventListener('keydown',event=>{if(session&&event.key==='Escape'){event.preventDefault();event.stopImmediatePropagation();cancel();}},true);
 document.addEventListener('click',event=>{if(event.target.closest?.('[data-block-menu]')&&Date.now()<suppressClickUntil){event.preventDefault();event.stopImmediatePropagation();}},true);
 document.addEventListener('dragstart',event=>{if(event.target.closest?.('[data-block-menu]'))event.preventDefault();});
 document.addEventListener('contextmenu',event=>{if(event.target.closest?.('[data-block-menu]'))event.preventDefault();});
 window.addEventListener('blur',cancel);
 return {cancel};
}
