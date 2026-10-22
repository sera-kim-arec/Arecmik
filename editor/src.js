/* Shared block editor. The checked-in bundle runs locally without a CDN. */
import {Schema, DOMParser as PMParser, DOMSerializer, Fragment} from 'prosemirror-model';
import {EditorState, TextSelection, NodeSelection, Plugin} from 'prosemirror-state';
import {EditorView, Decoration, DecorationSet} from 'prosemirror-view';
import {baseKeymap, toggleMark, splitBlock} from 'prosemirror-commands';
import {history, undo, redo, closeHistory} from 'prosemirror-history';
import {keymap} from 'prosemirror-keymap';
import {inputRules, InputRule, undoInputRule} from 'prosemirror-inputrules';
import {installBlockMoving,blockFromDOM} from './block-moving.js';

const kinds=['h1','h2','h3','li','num','todo','qt','co','coc','cite','src','code'];
const safeURL=(url,image=false)=>/^(https?:\/\/|mailto:|tel:|\/|#)/i.test(url||'')||(image&&/^data:image\/(png|gif|jpeg|webp);base64,/i.test(url||''));
function attrsFor(el){let listDepth=0;for(let p=el.parentElement;p;p=p.parentElement)if(/^(UL|OL)$/.test(p.tagName))listDepth++;return {kind:kinds.find(k=>el.classList.contains(k))||({H1:'h1',H2:'h2',H3:'h3',LI:el.parentElement?.tagName==='OL'?'num':'li',BLOCKQUOTE:'qt',PRE:'code'}[el.tagName]||''),depth:Math.min(4,Math.max(0,(+el.dataset.depth||0)+(el.tagName==='LI'?Math.max(0,listDepth-1):0))),checked:el.classList.contains('on'),day:el.classList.contains('dayh')};}
function blockAttrs(a){const cls=[a.kind,a.checked?'on':'',a.day?'dayh':''].filter(Boolean).join(' ');return {...(cls?{class:cls}:{}),...(a.depth?{'data-depth':a.depth}:{})};}
const schema=new Schema({nodes:{
 doc:{content:'block+'},
 paragraph:{group:'block',content:'inline*',attrs:{kind:{default:''},depth:{default:0},checked:{default:false},day:{default:false}},parseDOM:[{tag:'div',getAttrs:el=>el.matches('.nb-toggle,.nb-toggle-title,.nb-toggle-body,.nb-toggle-content,.img,.hrl2')?false:attrsFor(el)},{tag:'p',getAttrs:attrsFor},...['h1','h2','h3','li','blockquote','pre'].map(tag=>({tag,getAttrs:attrsFor}))],toDOM:n=>['div',blockAttrs(n.attrs),0]},
 toggle:{group:'block',content:'toggle_title toggle_body',defining:true,isolating:true,attrs:{open:{default:true}},parseDOM:[{tag:'div.nb-toggle',getAttrs:el=>({open:el.dataset.expanded!=='false'})}],toDOM:n=>['div',{class:'nb-toggle','data-expanded':String(n.attrs.open)},0]},
 toggle_title:{content:'inline*',defining:true,selectable:false,parseDOM:[{tag:'div.nb-toggle-title'}],toDOM:()=>['div',{class:'nb-toggle-title'},0]},
 toggle_body:{content:'block+',defining:true,selectable:false,parseDOM:[{tag:'div.nb-toggle-body'}],toDOM:()=>['div',{class:'nb-toggle-body'},0]},
 image:{group:'block',atom:true,draggable:true,attrs:{id:{default:''},src:{default:''},alt:{default:''},size:{default:''}},parseDOM:[{tag:'div.img',getAttrs:el=>{const im=el.querySelector('img');return im?{id:im.dataset.img||'',src:im.dataset.img?'':safeURL(im.getAttribute('src'),true)?im.getAttribute('src'):'',alt:im.alt||'',size:el.dataset.sz||''}:false}},{tag:'img',getAttrs:im=>({id:im.dataset.img||'',src:im.dataset.img?'':safeURL(im.getAttribute('src'),true)?im.getAttribute('src'):'',alt:im.alt||''})}],toDOM:n=>['div',{class:'img',...(n.attrs.size?{'data-sz':n.attrs.size}:{})},['img',{...(n.attrs.id?{'data-img':n.attrs.id}:n.attrs.src?{src:n.attrs.src}:{}),alt:n.attrs.alt}]]},
 rule:{group:'block',atom:true,parseDOM:[{tag:'hr'},{tag:'div.hrl2'}],toDOM:()=>['div',{class:'hrl2'}]},
 text:{group:'inline'},hard_break:{inline:true,group:'inline',selectable:false,parseDOM:[{tag:'br'}],toDOM:()=>['br']}
},marks:{
 strong:{parseDOM:[{tag:'strong'},{tag:'b'},{style:'font-weight',getAttrs:v=>/^(bold(er)?|[6-9]\d{2,})$/.test(v)?null:false}],toDOM:()=>['strong',0]},
 em:{parseDOM:[{tag:'em'},{tag:'i'},{style:'font-style=italic'}],toDOM:()=>['em',0]},
 underline:{parseDOM:[{tag:'u'},{style:'text-decoration',getAttrs:v=>v.includes('underline')?null:false}],toDOM:()=>['u',0]},
 strike:{parseDOM:[{tag:'s'},{tag:'del'},{style:'text-decoration',getAttrs:v=>v.includes('line-through')?null:false}],toDOM:()=>['s',0]},
 code:{code:true,parseDOM:[{tag:'code'}],toDOM:()=>['code',0]},
 link:{attrs:{href:{},chip:{default:false}},inclusive:false,parseDOM:[{tag:'a[href]',getAttrs:el=>safeURL(el.getAttribute('href'))?{href:el.getAttribute('href'),chip:el.classList.contains('lk')}:false}],toDOM:n=>['a',{href:n.attrs.href,target:'_blank',rel:'noopener',...(n.attrs.chip?{class:'lk'}:{})},0]},
 color:{attrs:{color:{}},parseDOM:[{style:'color',getAttrs:v=>({color:v})}],toDOM:n=>['span',{style:'color:'+n.attrs.color},0]},
 highlight:{attrs:{color:{}},parseDOM:[{tag:'mark',getAttrs:()=>({color:'#fff1a5'})},{style:'background-color',getAttrs:v=>({color:v})}],toDOM:n=>['span',{style:'background-color:'+n.attrs.color},0]}
}});

/* Old toggles were a title followed by unrelated .tgc siblings. Group them only
   in the rendered copy. Opening a page never writes a migration to the DB. */
export function normalizeRichHTML(html){
 const t=document.createElement('template');t.innerHTML=html||'';
 t.content.querySelectorAll('script,style,iframe,object,embed').forEach(el=>el.remove());
 t.content.querySelectorAll('*').forEach(el=>{for(const a of [...el.attributes])if(/^on/i.test(a.name)||a.name==='href'&&!safeURL(a.value)||a.name==='src'&&!safeURL(a.value,true))el.removeAttribute(a.name)});
 // Native lists contain other lists inside an LI. The editor stores flat blocks
 // with explicit depth; feeding an LI to the inline parser loses its parent text.
 function flattenList(list,depth=0){
  const result=document.createDocumentFragment();
  for(const item of [...list.children]){
   if(item.tagName!=='LI')continue;
   const before=result.childNodes.length;let line=null;
   const addLine=()=>{line=document.createElement('div');line.className=list.tagName==='OL'?'num':'li';if(depth)line.dataset.depth=String(Math.min(4,depth));result.append(line);return line;};
   for(const child of [...item.childNodes]){
    if(child.nodeType===1&&/^(UL|OL)$/.test(child.tagName)){if(!line)addLine();result.append(flattenList(child,depth+1));line=null;}
    else if(child.nodeType===1&&/^(P|DIV)$/.test(child.tagName)&&!child.matches('.img,.nb-toggle')){if(!line||line.childNodes.length)addLine();line.append(...child.childNodes);}
    else if(child.nodeType!==3||child.textContent.trim()||line)(line||addLine()).append(child);
   }
   if(result.childNodes.length===before)addLine();
  }
  return result;
 }
 for(const list of [...t.content.querySelectorAll('ul,ol')])if(!list.parentElement?.closest('ul,ol'))list.replaceWith(flattenList(list));
 let old;while((old=t.content.querySelector('.tgl'))){
  const wrap=document.createElement('div');wrap.className='nb-toggle';wrap.dataset.expanded=String(old.classList.contains('open'));
  const title=document.createElement('div');title.className='nb-toggle-title';title.innerHTML=old.innerHTML;
  const body=document.createElement('div');body.className='nb-toggle-body';let next=old.nextElementSibling;
  while(next?.classList.contains('tgc')){const after=next.nextElementSibling;next.classList.remove('tgc','hid');if(!next.className)next.removeAttribute('class');body.append(next);next=after}
  if(!body.childNodes.length)body.innerHTML='<div><br></div>';
  wrap.append(title,body);old.replaceWith(wrap);
 }
 t.content.querySelectorAll('div,p,h1,h2,h3').forEach(el=>{if(el.childNodes.length&&[...el.childNodes].every(n=>n.nodeType===3?!n.textContent.trim():n.nodeName==='BR')&&el.querySelectorAll('br').length===1)el.replaceChildren();});
 return t.innerHTML;
}

const commands=[
 ['text','본문','T','평범한 글'],['h1','큰 제목','H₁','큰 구분'],['h2','작은 제목','H₂','작은 구분'],['h3','소제목','H₃','문단 제목'],
 ['li','글머리 목록','•','목록'],['num','번호 목록','1.','순서대로'],['todo','체크 목록','☑','체크할 것'],['toggle','토글','▸','접고 펼치는 내용'],
 ['qt','인용','❝','인용문'],['co','강조 상자','!','기억할 내용'],['code','코드','⌘','코드 블록'],['rule','구분선','―','내용 나누기'],['link','링크','↗','주소 넣기'],['image','사진','▧','사진 추가']
];
const paragraph=()=>schema.nodes.paragraph.create();
const views=new Map();let menu=null,tools=null,inline=null,active=null,drag=null,toolContext=null;
function blockAt(state){if(state.selection instanceof NodeSelection)return {node:state.selection.node,pos:state.selection.from,depth:state.selection.$from.depth};const $p=state.selection.$from;for(let d=$p.depth;d>0;d--){const n=$p.node(d);if(n.type===schema.nodes.toggle_title)return {node:$p.node(d-1),pos:$p.before(d-1),depth:d-1};if(n.type.isBlock&&n.type!==schema.nodes.toggle_body)return {node:n,pos:$p.before(d),depth:d};}return null;}
function textBlock(state){const {$from}=state.selection;return $from.parent.isTextblock?{node:$from.parent,pos:$from.before()}:null;}
function selectText(tr,pos){return tr.setSelection(TextSelection.near(tr.doc.resolve(Math.max(0,Math.min(tr.doc.content.size,pos)))));}
function withView(ed){const entry=views.get(ed);if(entry&&!entry.flushing){entry.flushing=true;entry.view.domObserver.flush();entry.flushing=false}return entry?.view;}
function emit(entry){if(entry.emitPending)return;entry.emitPending=true;queueMicrotask(()=>{entry.emitPending=false;if(entry.host.isConnected)entry.host.dispatchEvent(new Event('input',{bubbles:true}))});}
function closeMenu(){menu?.dom.remove();menu=null;}
function hideUI(){closeMenu();tools?.remove();tools=null;inline?.remove();inline=null;}
function place(el,rect,above=false){
 const viewport=window.visualViewport,top=viewport?.offsetTop||0,left=viewport?.offsetLeft||0;
 const width=Math.min(innerWidth,viewport?.width||innerWidth),height=Math.min(innerHeight,viewport?.height||innerHeight);
 if(el.classList.contains('nb-menu'))el.style.maxHeight=Math.min(410,Math.floor(height*.65))+'px';
 el.style.position='fixed';el.style.left=Math.max(left+8,Math.min(left+width-el.offsetWidth-8,rect.left))+'px';
 const y=above?rect.top-el.offsetHeight-7:rect.bottom+7;el.style.top=Math.max(top+8,Math.min(top+height-el.offsetHeight-8,y))+'px';
}
function consumeSlash(view){if(!menu?.typed)return;const s=view.state,{from}=s.selection,pre=s.selection.$from.parent.textBetween(0,s.selection.$from.parentOffset,'\n','\n'),m=pre.match(/(?:^|\s)(\/[^\s/]*)$/);if(m)view.dispatch(s.tr.delete(from-m[1].length,from));}
function changeKind(view,kind){
 const range=blockRange(view);if(!range)return false;const s=view.state,tr=closeHistory(s.tr);
 if(kind==='rule'){
  const empty=range.nodes.length===1&&range.nodes[0].type===schema.nodes.paragraph&&!range.nodes[0].content.size;
  const at=empty?range.from:range.to;tr.replaceWith(at,empty?range.to:at,Fragment.fromArray([schema.nodes.rule.create(),paragraph()]));
  view.dispatch(selectText(tr,at+2));view.focus();return true;
 }
 if(kind!=='toggle'&&range.nodes.every(n=>n.type===schema.nodes.paragraph)){
  let at=range.from;for(const node of range.nodes){tr.setNodeMarkup(at,null,{...node.attrs,kind:kind==='text'?'':kind,checked:false});at+=node.nodeSize;}
  view.dispatch(tr);view.focus();return true;
 }
 const converted=[];
 for(const node of range.nodes){
  if(node.type===schema.nodes.image||node.type===schema.nodes.rule){converted.push(node);continue;}
  if(node.type===schema.nodes.toggle){
   if(kind==='toggle')converted.push(node);
   else converted.push(schema.nodes.paragraph.create({kind:kind==='text'?'':kind},node.firstChild.content),...node.lastChild.content.content);
  }else if(kind==='toggle')converted.push(schema.nodes.toggle.create({open:true},[schema.nodes.toggle_title.create(null,node.content),schema.nodes.toggle_body.create(null,paragraph())]));
  else converted.push(schema.nodes.paragraph.create({...node.attrs,kind:kind==='text'?'':kind,checked:false},node.content));
 }
 if(converted.every((n,i)=>n===range.nodes[i]))return false;
 tr.replaceWith(range.from,range.to,Fragment.fromArray(converted));
 if(range.nodes.length>1)selectMoved(tr,range.from,{nodes:converted,content:Fragment.fromArray(converted)});
 else selectText(tr,range.from+(converted[0].type===schema.nodes.toggle?2:1)+Math.min(s.selection.$from.parentOffset,converted[0].type===schema.nodes.toggle?converted[0].firstChild.content.size:converted[0].content.size));
 view.dispatch(tr);view.focus();return true;
}
function blockRange(view,pos=blockAt(view.state)?.pos){
 if(pos===undefined)return null;const node=view.state.doc.nodeAt(pos);if(!node)return null;
 const $pos=view.state.doc.resolve(pos),parent=$pos.parent,start=$pos.start(),selection=view.state.selection;
 const siblings=[];let at=start;parent.forEach(n=>{siblings.push({node:n,pos:at});at+=n.nodeSize;});
 const selected=!selection.empty?siblings.filter(b=>b.pos<selection.to&&b.pos+b.node.nodeSize>selection.from):[];
 const group=selected.length>1&&selected.some(b=>b.pos===pos)&&selection.from>=start&&selection.to<=start+parent.content.size?selected:[{pos,node}];
 const from=group[0].pos,to=group.at(-1).pos+group.at(-1).node.nodeSize;
 return {from,to,nodes:group.map(b=>b.node),content:Fragment.fromArray(group.map(b=>b.node)),parent,start};
}
function selectMoved(tr,at,range){if(range.nodes.length===1&&range.nodes[0].isAtom){tr.setSelection(NodeSelection.create(tr.doc,at));return tr;}if(range.nodes.length>1){tr.setSelection(TextSelection.between(tr.doc.resolve(at+1),tr.doc.resolve(at+range.content.size-1)));return tr;}return selectText(tr,at+1);}
function moveRange(view,range,target){
 if(target.at>=range.from&&target.at<=range.to)return false;
 const tr=closeHistory(view.state.tr);
 if(target.openAt!==undefined){const toggle=tr.doc.nodeAt(target.openAt);if(toggle?.type===schema.nodes.toggle)tr.setNodeMarkup(target.openAt,null,{...toggle.attrs,open:true});}
 if(range.parent.type===schema.nodes.toggle_body&&range.content.size===range.parent.content.size)tr.replaceWith(range.from,range.to,paragraph());else tr.delete(range.from,range.to);
 const at=tr.mapping.map(target.at);try{tr.insert(at,range.content);selectMoved(tr,at,range);}catch(_){return false;}
 view.dispatch(tr.scrollIntoView());view.focus();return true;
}
function moveBlock(view,dir){const range=blockRange(view);if(!range)return;const $p=view.state.doc.resolve(range.from),index=$p.index();
 const other=range.parent.maybeChild(dir<0?index-1:index+range.nodes.length);if(!other)return;
 moveRange(view,range,{at:dir<0?range.from-other.nodeSize:range.to+other.nodeSize});
}
function indent(view,dir){
 const range=blockRange(view);if(!range)return false;const state=view.state,$p=state.doc.resolve(range.from);
 if(dir<0&&range.parent.type===schema.nodes.toggle_body){const depth=$p.depth-1,pos=$p.before(depth),outer=$p.node(depth);moveRange(view,range,{at:pos+outer.nodeSize});return true;}
 const index=$p.index(),previous=index>0?range.parent.child(index-1):null;
 if(dir>0&&previous?.type===schema.nodes.toggle){moveRange(view,range,{at:range.from-2,openAt:range.from-previous.nodeSize});return true;}
 const tr=state.tr;state.doc.nodesBetween(range.from,range.to,(node,pos)=>{if(node.type===schema.nodes.paragraph)tr.setNodeMarkup(pos,null,{...node.attrs,depth:Math.min(4,Math.max(0,node.attrs.depth+dir))});});
 if(tr.docChanged)view.dispatch(tr);return true;
}
function enter(view){
 if(!view.state.selection.empty){view.dispatch(view.state.tr.deleteSelection());return enter(view);}
 const s=view.state,{$from}=s.selection;
 if($from.parent.type===schema.nodes.toggle_title){
  const depth=$from.depth-1,pos=$from.before(depth),tail=$from.parent.content.cut($from.parentOffset),tr=s.tr;
  // Enter starts a separate body line. It must never prepend to an existing note.
  if(tail.size)tr.delete($from.pos,$from.end());
  let toggle=tr.doc.nodeAt(pos);if(!toggle.attrs.open)tr.setNodeMarkup(pos,null,{open:true});
  const at=pos+toggle.firstChild.nodeSize+2,first=toggle.lastChild.firstChild;
  const reusable=first.type===schema.nodes.paragraph&&!first.content.size&&!first.attrs.kind&&!first.attrs.depth;
  if(tail.size||!reusable)tr.replaceWith(at,reusable?at+first.nodeSize:at,schema.nodes.paragraph.create(null,tail));
  view.dispatch(selectText(tr,at+1).scrollIntoView());return true;
 }
 const b=textBlock(s);if(!b)return false;
 if(!b.node.textContent&&$from.parent.type===schema.nodes.paragraph){
  if(b.node.attrs.kind||b.node.attrs.depth){view.dispatch(s.tr.setNodeMarkup(b.pos,null,{...b.node.attrs,kind:'',depth:0,checked:false}));return true;}
  if($from.depth>1&&$from.node($from.depth-1).type===schema.nodes.toggle_body){const depth=$from.depth-2,outerPos=$from.before(depth),toggle=$from.node(depth),tr=s.tr;const body=$from.node($from.depth-1);if(body.childCount>1)tr.delete(b.pos,b.pos+b.node.nodeSize);const after=tr.mapping.map(outerPos+toggle.nodeSize);tr.insert(after,paragraph());view.dispatch(selectText(tr,after+1));return true;}
 }
 if(b.node.attrs.kind==='code')return false;
 if($from.parentOffset===b.node.content.size&&['h1','h2','h3','qt','co'].includes(b.node.attrs.kind)){const at=b.pos+b.node.nodeSize,tr=s.tr.insert(at,paragraph());view.dispatch(selectText(tr,at+1));return true;}
 return splitBlock(s,tr=>{const p=tr.selection.$from;if(p.parent.type===schema.nodes.paragraph&&p.parent.attrs.checked)tr.setNodeMarkup(p.before(),null,{...p.parent.attrs,checked:false});view.dispatch(tr)});
}
// Skip required empty body placeholders when returning from the following line.
function toggleEnd(node,pos){
 let end=pos+node.firstChild.nodeSize;if(!node.attrs.open)return end;
 let at=pos+node.firstChild.nodeSize+2;const blocks=[];node.lastChild.forEach(child=>{blocks.push({node:child,pos:at});at+=child.nodeSize;});
 for(const b of blocks.reverse()){
  if(b.node.type===schema.nodes.toggle)return toggleEnd(b.node,b.pos);
  if(b.node.isTextblock&&b.node.content.size)return b.pos+b.node.nodeSize-1;
 }
 return end;
}
function backspace(view){if(undoInputRule(view.state,view.dispatch))return true;const s=view.state,{$from,empty}=s.selection;if(!empty||$from.parentOffset!==0)return false;const b=textBlock(s);if(!b)return false;
 if(b.node.type===schema.nodes.toggle_title)return changeKind(view,'text');
 if(b.node.attrs.kind||b.node.attrs.depth){view.dispatch(s.tr.setNodeMarkup(b.pos,null,{...b.node.attrs,kind:'',depth:0,checked:false}));return true;}
 if($from.depth>1&&$from.node($from.depth-1).type===schema.nodes.toggle_body&&$from.index($from.depth-1)===0){
  if(!b.node.content.size){const body=$from.node($from.depth-1),depth=$from.depth-2,pos=$from.before(depth),titleEnd=pos+$from.node(depth).firstChild.nodeSize,tr=closeHistory(s.tr);if(body.childCount>1)tr.delete(b.pos,b.pos+b.node.nodeSize);view.dispatch(selectText(tr,titleEnd).scrollIntoView());return true;}
  return indent(view,-1);
 }
 const $pos=s.doc.resolve(b.pos),previous=$pos.nodeBefore;
 if(previous?.type===schema.nodes.toggle){const tr=s.tr;if(!b.node.content.size)tr.delete(b.pos,b.pos+b.node.nodeSize);view.dispatch(selectText(closeHistory(tr),toggleEnd(previous,b.pos-previous.nodeSize)).scrollIntoView());return true;}
 return false;
}
function textStart(node,pos){return node.type===schema.nodes.toggle?pos+2:node.isTextblock?pos+1:null;}
function followingToggleText(state,pos,node){const $pos=state.doc.resolve(pos),next=$pos.parent.maybeChild($pos.index()+1);return next?textStart(next,pos+node.nodeSize):null;}
function forwardDelete(view){
 const s=view.state,{$from,empty}=s.selection;if(!empty||$from.parentOffset!==$from.parent.content.size)return false;const b=textBlock(s);if(!b)return false;
 if(b.node.type===schema.nodes.toggle_title){
  const depth=$from.depth-1,pos=$from.before(depth),toggle=$from.node(depth);let at=null;
  if(toggle.attrs.open){let childPos=pos+toggle.firstChild.nodeSize+2;toggle.lastChild.forEach(child=>{if(at===null)at=textStart(child,childPos);childPos+=child.nodeSize;});}
  else at=followingToggleText(s,pos,toggle);
  if(at!==null)view.dispatch(selectText(s.tr,at).scrollIntoView());return true;
 }
 const $pos=s.doc.resolve(b.pos),next=$pos.parent.maybeChild($pos.index()+1);
 if(next?.type===schema.nodes.toggle){const tr=s.tr;let at=b.pos+b.node.nodeSize;if(!b.node.content.size){tr.delete(b.pos,at);at=tr.mapping.map(at);}view.dispatch(selectText(closeHistory(tr),at+2).scrollIntoView());return true;}
 if(!next&&$from.depth>1&&$from.node($from.depth-1).type===schema.nodes.toggle_body){const depth=$from.depth-2,pos=$from.before(depth),toggle=$from.node(depth),at=followingToggleText(s,pos,toggle);if(at!==null)view.dispatch(selectText(s.tr,at).scrollIntoView());return true;}
 return false;
}
function rules(){const specs=[[/^#\s$/,'h1'],[/^##\s$/,'h2'],[/^###\s$/,'h3'],[/^[-*•]\s$/,'li'],[/^1[.)]\s$/,'num'],[/^\[\s?\]\s$/,'todo'],[/^>>?\s$/,'toggle'],[/^["“]\s$/,'qt'],[/^!\s$/,'co'],[/^```\s$/,'code']];const blocks=specs.map(([re,kind])=>new InputRule(re,(state,match,start,end)=>{
 const $p=state.doc.resolve(start);if($p.parent.type!==schema.nodes.paragraph||$p.parent.attrs.kind)return null;const tr=state.tr.delete(start,end),pos=$p.before();if(kind==='toggle'){const original=tr.doc.nodeAt(pos);const toggle=schema.nodes.toggle.create({open:true},[schema.nodes.toggle_title.create(null,original.content),schema.nodes.toggle_body.create(null,paragraph())]);tr.replaceWith(pos,pos+original.nodeSize,toggle);return selectText(tr,pos+2)}return tr.setNodeMarkup(pos,null,{...$p.parent.attrs,kind});
 }));return [...blocks,...[['->','→'],['<-','←'],['=>','⇒']].map(([from,to])=>new InputRule(new RegExp(from.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'$'),(state,match,start,end)=>state.selection.$from.parent.attrs.kind==='code'?null:state.tr.insertText(to,start,end))),new InputRule(/(https?:\/\/[^\s<]+|www\.[^\s<]+\.[^\s<]+)\s$/,(state,match,start,end)=>{if(state.selection.$from.parent.attrs.kind==='code')return null;const url=/^https?:/i.test(match[1])?match[1]:'https://'+match[1];return state.tr.insertText(' ',end).addMark(start,end,schema.marks.link.create({href:url})).removeStoredMark(schema.marks.link)})];}
function decorations(state,placeholder){const d=[],number=new Map();state.doc.descendants((n,pos,parent)=>{if(n.type===schema.nodes.paragraph||n.type===schema.nodes.toggle_title){const attrs={};if(!n.content.size)attrs['data-placeholder']=n.type===schema.nodes.toggle_title?'토글 제목':parent.type===schema.nodes.toggle_body?'내용을 적거나 / 로 추가':state.doc.childCount===1?placeholder||'내용을 적거나 / 로 블록 추가':'/ 로 블록 추가';if(n.attrs.kind==='num'){let a=number.get(parent)||[0,0,0,0,0];a[n.attrs.depth]++;a.fill(0,n.attrs.depth+1);attrs['data-n']=String(a[n.attrs.depth]);number.set(parent,a)}else if(n.type===schema.nodes.paragraph){const a=number.get(parent)||[0,0,0,0,0];a.fill(0,n.attrs.depth);number.set(parent,a);}if(Object.keys(attrs).length)d.push(Decoration.node(pos,pos+n.nodeSize,attrs));}});const selected=blockRange({state});if(selected?.nodes.length>1){let at=selected.from;for(const node of selected.nodes){d.push(Decoration.node(at,at+node.nodeSize,{class:'nb-selected-block'}));at+=node.nodeSize;}}return DecorationSet.create(state.doc,d);}
class ToggleView{
 constructor(node,view,getPos){
  this.node=node;this.view=view;this.getPos=getPos;
  this.dom=document.createElement('div');this.dom.className='nb-toggle';
  this.button=document.createElement('button');this.button.className='nb-toggle-arrow';this.button.type='button';this.button.contentEditable='false';this.button.tabIndex=-1;
  this.button.innerHTML='<span class="nb-toggle-caret" aria-hidden="true">▸</span>';
  this.button.addEventListener('mousedown',event=>event.preventDefault());
  this.button.addEventListener('click',event=>{
   event.preventDefault();event.stopPropagation();const pos=this.getPos();if(typeof pos!=='number')return;
   const focused=view.hasFocus(),selection=view.state.selection,bodyStart=pos+this.node.firstChild.nodeSize+2;
   const tr=view.state.tr.setNodeMarkup(pos,null,{open:!this.node.attrs.open}).setMeta('addToHistory',false);
   if(this.node.attrs.open&&selection.from>=bodyStart&&selection.to<pos+this.node.nodeSize)selectText(tr,pos+this.node.firstChild.nodeSize);
   view.dispatch(tr);if(focused)view.focus();
  });
  this.contentDOM=document.createElement('div');this.contentDOM.className='nb-toggle-content';this.dom.append(this.button,this.contentDOM);this.update(node);
 }
 update(node){if(node.type!==schema.nodes.toggle)return false;this.node=node;this.dom.dataset.expanded=String(node.attrs.open);this.button.setAttribute('aria-expanded',String(node.attrs.open));this.button.setAttribute('aria-label',node.attrs.open?'내용 접기':'내용 펼치기');return true;}
 stopEvent(event){return this.button.contains(event.target)}
 ignoreMutation(mutation){return mutation.type!=='selection'&&(mutation.target===this.dom||this.button.contains(mutation.target))}
}
export function installBlockEditors(options={}){
 let linkDialog=null,moving=null;
 function openLink(view,anchor=null){
  closeMenu();inline?.remove();inline=null;linkDialog?.cancel();
  const state=view.state;let {from,to}=state.selection,href='';
  if(anchor){try{from=view.posAtDOM(anchor,0);to=from+anchor.textContent.length;href=anchor.getAttribute('href')||'';}catch(_){return;}}
  else{const mark=state.selection.$from.marks().find(m=>m.type===schema.marks.link);if(mark)href=mark.attrs.href;}
  const saved=state.selection.getBookmark(),scrim=document.createElement('div');scrim.className='nb-link-scrim';
  scrim.innerHTML='<form class="nb-link-dialog" role="dialog" aria-modal="true" aria-label="링크 넣기"><label for="nb-link-url">링크 주소</label><input id="nb-link-url" type="text" inputmode="url" autocomplete="url" placeholder="https://" aria-describedby="nb-link-error"><p id="nb-link-error" role="alert"></p><div><button type="button" data-link-cancel>취소</button><button type="submit">적용</button></div></form>';
  const input=scrim.querySelector('input');input.value=href;document.body.append(scrim);
  function finish(){scrim.remove();linkDialog=null;if(view.dom.isConnected){view.focus();refreshUI(view);}}
  function cancel(){if(view.dom.isConnected){try{view.dispatch(view.state.tr.setSelection(saved.resolve(view.state.doc)));}catch(_){}}finish();}
  linkDialog={cancel};
  scrim.addEventListener('click',e=>{if(e.target===scrim||e.target.closest('[data-link-cancel]')){e.preventDefault();cancel();}});
  scrim.addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();e.stopPropagation();cancel();}if(e.key==='Tab'){const controls=[...scrim.querySelectorAll('input,button')],i=controls.indexOf(document.activeElement);if(e.shiftKey&&i===0||!e.shiftKey&&i===controls.length-1){e.preventDefault();controls[e.shiftKey?controls.length-1:0].focus();}}});
  scrim.querySelector('form').addEventListener('submit',e=>{
   e.preventDefault();let url=input.value.trim();if(url&&!/^(https?:|mailto:|tel:|\/|#)/i.test(url))url='https://'+url;
   let valid=!url||safeURL(url);if(valid&&/^https?:/i.test(url)){try{valid=!!new URL(url).hostname}catch(_){valid=false}}
   if(!valid){scrim.querySelector('[role=alert]').textContent='주소를 확인해 주세요. 예: https://example.com';input.setAttribute('aria-invalid','true');input.focus();return;}
   if(!view.dom.isConnected){finish();return;}
   let tr=view.state.tr;if(from===to&&url){tr.insertText(url,from);tr.addMark(from,from+url.length,schema.marks.link.create({href:url}));selectText(tr,from+url.length);}else{tr.removeMark(from,to,schema.marks.link);if(url)tr.addMark(from,to,schema.marks.link.create({href:url}));tr.setSelection(saved.resolve(tr.doc));}
   view.dispatch(closeHistory(tr));finish();
  });
  input.focus();input.select();
 }

 function activateTool(context=toolContext){if(!context?.view.dom.isConnected)return null;const {view,pos}=context,range=blockRange(view,pos);if(!range)return null;const current=blockAt(view.state);if(range.nodes.length===1&&current?.pos!==pos){const tr=view.state.tr;const node=view.state.doc.nodeAt(pos);if(node.isAtom)tr.setSelection(NodeSelection.create(tr.doc,pos));else selectText(tr,pos+1);view.dispatch(tr);}view.focus();return view;}
 function execute(view,key){consumeSlash(view);closeMenu();if(key==='image'){options.photo?.(view.dom,currentBlock(view.dom));return;}if(key==='link'){openLink(view);return;}changeKind(view,key);}
 function openMenu(view,{typed=false,rect=null,actions=false}={}){closeMenu();inline?.remove();inline=null;const dom=document.createElement('div');dom.className='nb-menu';dom.setAttribute('role','listbox');dom.setAttribute('aria-label','문단 메뉴');dom.innerHTML='<div class="nb-menu-label">'+(actions?'문단':'블록 추가')+'</div><div class="nb-menu-items"></div><div class="nb-menu-help">↑↓ 이동 · Enter 선택 · Esc 닫기</div>';document.body.append(dom);menu={view,dom,typed,q:'',index:0,actions,rect:rect||view.coordsAtPos(view.state.selection.from)};drawMenu();}
 function menuItems(){const range=blockRange(menu.view),onlyMedia=menu.actions&&range?.nodes.length===1&&['image','rule'].includes(range.nodes[0].type.name);let items=(onlyMedia?[]:commands).filter(c=>!menu.q||(c[1]+' '+c[0]+' '+c[3]).toLowerCase().includes(menu.q.toLowerCase()));if(menu.actions&&!menu.q)items=[['insert','아래에 문단 추가','+'],['up','위로 이동','↑'],['down','아래로 이동','↓'],['duplicate','복제','⧉'],['delete','삭제','×'],['undo','실행 취소','↶'],['redo','다시 실행','↷'],...items];return items;}
 function pick(index){if(!menu)return;const {view}=menu,key=menuItems()[index]?.[0];if(!key)return;consumeSlash(view);closeMenu();view.focus();const b=blockAt(view.state),range=blockRange(view);if(key==='insert'&&range){const at=range.to;view.dispatch(selectText(view.state.tr.insert(at,paragraph()),at+1));view.focus();return;}if(key==='up'||key==='down'){moveBlock(view,key==='up'?-1:1);return;}if(key==='undo'||key==='redo'){(key==='undo'?undo:redo)(view.state,view.dispatch);return;}if(key==='duplicate'&&range){const at=range.to,tr=view.state.tr.insert(at,range.content);view.dispatch(selectMoved(closeHistory(tr),at,range));return;}if(key==='delete'&&range){const tr=view.state.tr.delete(range.from,range.to);view.dispatch(selectText(closeHistory(tr),Math.min(range.from,tr.doc.content.size)));return;}execute(view,key);}
 function drawMenu(){if(!menu)return;const items=menuItems();menu.index=Math.max(0,Math.min(menu.index,items.length-1));menu.dom.querySelector('.nb-menu-items').innerHTML=items.length?items.map((c,i)=>`<button type="button" role="option" aria-selected="${i===menu.index}" data-block-command="${i}"><span class="nb-menu-icon">${c[2]}</span><span><b>${c[1]}</b>${c[3]?'<small>'+c[3]+'</small>':''}</span></button>`).join(''):'<div class="nb-no-results">맞는 블록이 없어요.</div>';place(menu.dom,menu.rect);menu.dom.querySelector('[aria-selected="true"]')?.scrollIntoView({block:'nearest'});}
 function slashUpdate(view){if(view.composing)return;if(menu&&menu.view!==view)closeMenu();const {$from,empty}=view.state.selection;if(!empty||!$from.parent.isTextblock){if(menu?.typed)closeMenu();return;}const pre=$from.parent.textBetween(0,$from.parentOffset,'\n','\n'),m=pre.match(/(?:^|\s)\/([^\s/]*)$/);if(!m){if(menu?.typed)closeMenu();return;}if(!menu)openMenu(view,{typed:true});if(menu?.typed){menu.q=m[1];drawMenu();}}
 function keyHandler(view,event){if(event.isComposing||view.composing)return false;view.domObserver.flush();if(event.key==='Escape'&&menu){closeMenu();return true;}if(menu?.view===view){const items=menuItems();if(event.key==='ArrowDown'||event.key==='ArrowUp'){menu.index=items.length?(menu.index+(event.key==='ArrowDown'?1:-1)+items.length)%items.length:0;drawMenu();return true;}if(event.key==='Enter'){pick(menu.index);return true;}if(event.key==='Tab'){closeMenu();return false;}}
 if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){openLink(view);return true;}if(event.key==='Tab')return indent(view,event.shiftKey?-1:1);return false;}
 function mount(host){if(views.has(host)||!host.isConnected||host.getAttribute('contenteditable')!=='true')return;const original=host.innerHTML,clean=document.createElement('div');clean.innerHTML=normalizeRichHTML(original);const doc=PMParser.fromSchema(schema).parse(clean);const entry={host,view:null,original,dirty:false,flushing:false};views.set(host,entry);
 const customKeys={'Enter':(s,d,v)=>enter(v),'Backspace':(s,d,v)=>backspace(v),'Delete':(s,d,v)=>forwardDelete(v),'Mod-Backspace':(s,d,v)=>backspace(v),'Mod-Delete':(s,d,v)=>forwardDelete(v),'Mod-z':undo,'Shift-Mod-z':redo,'Mod-y':redo,'Mod-b':toggleMark(schema.marks.strong),'Mod-i':toggleMark(schema.marks.em),'Mod-u':toggleMark(schema.marks.underline),'Mod-`':toggleMark(schema.marks.code),'Shift-Enter':(s,d)=>{d(s.tr.replaceSelectionWith(schema.nodes.hard_break.create()).scrollIntoView());return true},'Alt-ArrowUp':(s,d,v)=>{moveBlock(v,-1);return true},'Alt-ArrowDown':(s,d,v)=>{moveBlock(v,1);return true}};
 const view=new EditorView({mount:host},{state:EditorState.create({schema,doc,plugins:[history(),inputRules({rules:rules()}),keymap(customKeys),keymap(baseKeymap),new Plugin({props:{decorations:state=>decorations(state,host.dataset.ph)}})]}),attributes:{class:'nb-editor',role:'textbox','aria-multiline':'true','aria-label':host.getAttribute('aria-label')||'글과 메모 편집기',spellcheck:'true'},nodeViews:{toggle:(...args)=>new ToggleView(...args)},handleKeyDown:keyHandler,
 dispatchTransaction(tr){if(tr.getMeta('uiEvent')==='cut')closeHistory(tr);const prev=view.state;view.updateState(view.state.apply(tr));if(tr.docChanged){entry.dirty=true;options.hydrate?.(host);emit(entry);}if((tr.docChanged||menu?.typed)&&tr.getMeta('uiEvent')!=='paste')slashUpdate(view);if(prev.selection!==view.state.selection||tr.docChanged)refreshUI(view);},
 handleDOMEvents:{beforeinput:(view,event)=>{if(event.isComposing||view.composing||!event.cancelable)return false;if(/^delete(?:Content|Word|SoftLine|HardLine)(?:Backward|Forward)$/.test(event.inputType)){view.domObserver.flush();const back=event.inputType.endsWith('Backward'),s=view.state;if(!event.inputType.startsWith('deleteContent')&&(!s.selection.empty||s.selection.$from.parentOffset!==(back?0:s.selection.$from.parent.content.size)))return false;if((back?backspace:forwardDelete)(view)){event.preventDefault();return true;}return false;}if(event.inputType!=='insertParagraph')return false;view.domObserver.flush();if(keyHandler(view,{key:'Enter',isComposing:false})||enter(view)){event.preventDefault();return true;}return false;},focus:()=>{active=view;return false},compositionstart:()=>{closeMenu();inline?.remove();inline=null;return false},compositionend:()=>{queueMicrotask(()=>slashUpdate(view));return false}},
 handleClick(view,pos,event){const block=event.target.closest('.todo');if(block&&event.clientX-block.getBoundingClientRect().left<26){const at=view.posAtDOM(block,0)-1,n=view.state.doc.nodeAt(at);if(n?.type===schema.nodes.paragraph){view.dispatch(view.state.tr.setNodeMarkup(at,null,{...n.attrs,checked:!n.attrs.checked}));return true;}}const b=blockFromDOM(view,event.target);if(b)refreshUI(view,b);return false;},
 handlePaste(view,event){const cd=event.clipboardData;if(!cd)return false;const files=[...(cd.files||[])].filter(f=>/^image\//.test(f.type));if(files.length){options.photo?.(host,currentBlock(host),files);return true;}const text=cd.getData('text/plain'),html=cd.getData('text/html');if(/^https?:\/\/\S+$/i.test(text.trim())&&!view.state.selection.empty){const {from,to}=view.state.selection;view.dispatch(view.state.tr.addMark(from,to,schema.marks.link.create({href:text.trim()})));return true;}if(html||/https?:\/\/|www\./i.test(text)){const c=document.createElement('div');c.innerHTML=normalizeRichHTML(html||options.linkify?.(text)||'');const parser=PMParser.fromSchema(schema),b=textBlock(view.state);let tr=closeHistory(view.state.tr);
 if(b?.node.type===schema.nodes.paragraph&&!b.node.content.size){const content=parser.parse(c).content;tr.replaceWith(b.pos,b.pos+b.node.nodeSize,content);selectText(tr,b.pos+content.size-1);}
 else tr.replaceSelection(parser.parseSlice(c));
 view.dispatch(tr.scrollIntoView().setMeta('uiEvent','paste'));return true;}return false;}
 });entry.view=view;options.hydrate?.(host);}
 function currentBlock(host){const view=withView(host);if(!view)return null;const b=blockAt(view.state);return b?view.nodeDOM(b.pos):null;}
 function refreshUI(view,hover=null){if(!view.dom.isConnected||view.composing||linkDialog||drag?.view===view)return;if(!hover&&!view.hasFocus()&&active!==view)return;active=view;inline?.remove();inline=null;
 const b=hover||blockAt(view.state);if(!b)return;const node=view.nodeDOM(b.pos);if(!node?.getBoundingClientRect)return;const rect=node.getBoundingClientRect();if(!rect.width||rect.bottom<0||rect.top>innerHeight){tools?.remove();tools=null;toolContext=null;return;}
 toolContext={view,pos:b.pos};if(!tools){tools=document.createElement('div');tools.className='nb-tools';tools.setAttribute('aria-label','문단 도구');tools.innerHTML='<button type="button" data-block-add aria-label="문단 추가" title="문단 추가">+</button><button type="button" data-block-menu aria-label="문단 서식 및 이동" title="드래그해 이동 · 클릭해 서식 (Alt+↑↓)">⠿</button>';document.body.append(tools);}tools.style.left=Math.max(2,rect.left-(matchMedia('(pointer:coarse)').matches?38:44))+'px';tools.style.top=Math.max(0,rect.top-1)+'px';
 if(!view.state.selection.empty&&view.state.selection.$from.parent.isTextblock){inline=document.createElement('div');inline.className='nb-inline';inline.setAttribute('role','toolbar');inline.setAttribute('aria-label','선택한 글 서식');inline.innerHTML=[['strong','굵게','B'],['em','기울임','I'],['underline','밑줄','U'],['strike','취소선','S'],['code','인라인 코드','〈〉'],['link','링크','↗']].map(([k,l,t])=>`<button type="button" data-mark="${k}" aria-label="${l}">${t}</button>`).join('');document.body.append(inline);place(inline,view.coordsAtPos(view.state.selection.from),true);}
 }
 document.addEventListener('mousedown',event=>{if(event.target.closest('.nb-tools,.nb-menu,.nb-inline')){event.preventDefault();return;}if(menu&&!event.target.closest('.nb-editor'))closeMenu();});
 document.addEventListener('click',event=>{let bt=event.target.closest('[data-block-command]');if(bt){pick(+bt.dataset.blockCommand);return;}if(event.target.closest('[data-block-menu]')){const view=activateTool();if(view)openMenu(view,{actions:true,rect:event.target.getBoundingClientRect()});return;}if(event.target.closest('[data-block-add]')){const view=activateTool();if(!view)return;const b=blockAt(view.state),range=blockRange(view);if(!b)return;if(range.nodes.length>1||b.node.type!==schema.nodes.paragraph||b.node.content.size){const at=range.to;view.dispatch(selectText(view.state.tr.insert(at,paragraph()),at+1));}view.focus();openMenu(view);return;}bt=event.target.closest('[data-mark]');if(bt&&active){if(bt.dataset.mark==='link'){openLink(active);return;}else toggleMark(schema.marks[bt.dataset.mark])(active.state,active.dispatch);active.focus();refreshUI(active);}});
 document.addEventListener('click',event=>{const title=event.target.closest('.nb-toggle-title');if(!title||title.closest('.nb-editor'))return;event.preventDefault();event.stopImmediatePropagation();const wrap=title.parentElement;wrap.dataset.expanded=String(wrap.dataset.expanded==='false');title.setAttribute('aria-expanded',String(wrap.dataset.expanded!=='false'));},true);
 document.addEventListener('keydown',event=>{const title=event.target;if(!title.matches?.('.nb-toggle-title[role=button]')||title.closest('.nb-editor')||!['Enter',' '].includes(event.key))return;event.preventDefault();event.stopImmediatePropagation();const wrap=title.parentElement;wrap.dataset.expanded=String(wrap.dataset.expanded==='false');title.setAttribute('aria-expanded',String(wrap.dataset.expanded!=='false'));},true);
 document.addEventListener('selectionchange',()=>{if(active?.hasFocus()&&!active.composing&&!menu){active.domObserver.flush();refreshUI(active);}});
 document.addEventListener('focusin',event=>{const host=event.target.closest?.('.rt[contenteditable="true"]');if(host){mount(host);active=views.get(host)?.view;}else if(!event.target.closest('.nb-tools,.nb-menu,.nb-inline,.lpop,#one')){hideUI();active=null;}},true);
 document.addEventListener('pointerdown',event=>{if(!event.target.closest('.nb-tools,.nb-menu,.nb-inline,.nb-editor,.lpop,#one')){hideUI();active=null;}});
 moving=installBlockMoving({
  view:host=>views.get(host)?.view,context:()=>toolContext,
  range:blockRange,session:value=>{drag=value;},closeMenu,
  hover:(view,b)=>{if(!menu&&!linkDialog)refreshUI(view,b);},
  refresh:view=>{if(view.dom.isConnected)refreshUI(view);},
  menu:(view,context)=>{if(activateTool(context))openMenu(view,{actions:true,rect:tools?.getBoundingClientRect()||view.coordsAtPos(view.state.selection.from)});},
  move:moveRange
 });
 window.addEventListener('scroll',event=>{if(drag)return;if(menu){if(menu.dom.contains(event.target))return;if(menu.view.dom.isConnected){menu.rect=menu.view.coordsAtPos(menu.view.state.selection.from);place(menu.dom,menu.rect);}else closeMenu();}if(active?.hasFocus())refreshUI(active);else if(tools&&toolContext?.view===active&&active.dom.isConnected)refreshUI(active,{pos:toolContext.pos});else if(!menu&&!linkDialog)hideUI()},{passive:true,capture:true});
 function viewportChanged(){if(menu){if(menu.view.dom.isConnected){menu.rect=menu.view.coordsAtPos(menu.view.state.selection.from);place(menu.dom,menu.rect);}else closeMenu();}if(active?.hasFocus())refreshUI(active);}
 window.addEventListener('resize',viewportChanged);window.visualViewport?.addEventListener('resize',viewportChanged);
 function scan(){document.querySelectorAll('.rt:not([contenteditable]) .nb-toggle-title').forEach(title=>{if(title.closest('.nb-editor'))return;title.setAttribute('role','button');title.tabIndex=0;title.setAttribute('aria-expanded',String(title.parentElement.dataset.expanded!=='false'));});for(const [host,entry] of views)if(!host.isConnected){if(active===entry.view){hideUI();active=null;}entry.view.destroy();views.delete(host);}document.querySelectorAll('.rt[contenteditable="true"]').forEach(mount);}
 let pending=false;new MutationObserver(()=>{if(pending)return;pending=true;queueMicrotask(()=>{pending=false;scan();});}).observe(document.body,{childList:true,subtree:true});scan();
 return {
  has:host=>views.has(host),
  busy:()=>!!linkDialog||!!drag,
  link(host,anchor){const view=withView(host);if(view)openLink(view,anchor);},
  closeTopLayer(){if(moving?.cancel())return true;if(linkDialog){linkDialog.cancel();return true;}if(menu){closeMenu();active?.focus();return true;}return false;},
  serialize(host){const view=withView(host),entry=views.get(host);if(!view)return null;if(!entry.dirty)return entry.original;const c=document.createElement('div');c.append(DOMSerializer.fromSchema(schema).serializeFragment(view.state.doc.content));return c.innerHTML;},
  currentBlock,
  insertImage(host,block,id){const view=withView(host);if(!view)return null;let b=blockAt(view.state);if(block&&host.contains(block)){try{let pos=view.posAtDOM(block,0);const $p=view.state.doc.resolve(pos);if($p.parent.isTextblock)b={node:$p.parent,pos:$p.before()};}catch(_){}}
   if(!b)b={node:null,pos:view.state.doc.content.size};const replace=b.node?.type===schema.nodes.paragraph&&!b.node.content.size,at=replace?b.pos:b.pos+(b.node?.nodeSize||0);const image=schema.nodes.image.create({id}),nx=paragraph(),tr=view.state.tr.replaceWith(at,replace?at+b.node.nodeSize:at,Fragment.fromArray([image,nx]));view.dispatch(selectText(closeHistory(tr),at+image.nodeSize+1));options.hydrate?.(host);view.focus();return view.nodeDOM(at+image.nodeSize);
  }
 };
}
