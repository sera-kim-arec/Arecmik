/* Shared block editor. The checked-in bundle runs locally without a CDN. */
import {Schema, DOMParser as PMParser, DOMSerializer, Fragment} from 'prosemirror-model';
import {EditorState, TextSelection, NodeSelection, Plugin} from 'prosemirror-state';
import {EditorView, Decoration, DecorationSet} from 'prosemirror-view';
import {baseKeymap, toggleMark, splitBlock} from 'prosemirror-commands';
import {history, undo, redo, closeHistory} from 'prosemirror-history';
import {keymap} from 'prosemirror-keymap';
import {inputRules, InputRule, undoInputRule} from 'prosemirror-inputrules';

const kinds=['h1','h2','h3','li','num','todo','qt','co','coc','cite','src','code'];
const safeURL=(url,image=false)=>/^(https?:\/\/|mailto:|tel:|\/|#)/i.test(url||'')||(image&&/^data:image\/(png|gif|jpeg|webp);base64,/i.test(url||''));
function attrsFor(el){return {kind:kinds.find(k=>el.classList.contains(k))||({H1:'h1',H2:'h2',H3:'h3',LI:'li',BLOCKQUOTE:'qt',PRE:'code'}[el.tagName]||''),depth:Math.min(4,Math.max(0,+el.dataset.depth||0)),checked:el.classList.contains('on'),day:el.classList.contains('dayh')};}
function blockAttrs(a){const cls=[a.kind,a.checked?'on':'',a.day?'dayh':''].filter(Boolean).join(' ');return {...(cls?{class:cls}:{}),...(a.depth?{'data-depth':a.depth}:{})};}
const schema=new Schema({nodes:{
 doc:{content:'block+'},
 paragraph:{group:'block',content:'inline*',attrs:{kind:{default:''},depth:{default:0},checked:{default:false},day:{default:false}},parseDOM:[{tag:'div',getAttrs:el=>el.matches('.nb-toggle,.nb-toggle-title,.nb-toggle-body,.nb-toggle-content,.img,.hrl2')?false:attrsFor(el)},{tag:'p',getAttrs:attrsFor},...['h1','h2','h3','li','blockquote','pre'].map(tag=>({tag,getAttrs:attrsFor}))],toDOM:n=>['div',blockAttrs(n.attrs),0]},
 toggle:{group:'block',content:'toggle_title toggle_body',defining:true,isolating:true,attrs:{open:{default:true}},parseDOM:[{tag:'div.nb-toggle',getAttrs:el=>({open:el.dataset.expanded!=='false'})}],toDOM:n=>['div',{class:'nb-toggle','data-expanded':String(n.attrs.open)},0]},
 toggle_title:{content:'inline*',defining:true,parseDOM:[{tag:'div.nb-toggle-title'}],toDOM:()=>['div',{class:'nb-toggle-title'},0]},
 toggle_body:{content:'block+',defining:true,parseDOM:[{tag:'div.nb-toggle-body'}],toDOM:()=>['div',{class:'nb-toggle-body'},0]},
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
const views=new Map();let menu=null,tools=null,inline=null,active=null,drag=null;
function blockAt(state){const $p=state.selection.$from;for(let d=$p.depth;d>0;d--){const n=$p.node(d);if(n.type===schema.nodes.toggle_title)return {node:$p.node(d-1),pos:$p.before(d-1),depth:d-1};if(n.type.isBlock&&n.type!==schema.nodes.toggle_body)return {node:n,pos:$p.before(d),depth:d};}if(state.selection instanceof NodeSelection)return {node:state.selection.node,pos:state.selection.from,depth:0};return null;}
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
function changeKind(view,kind){const s=view.state,b=blockAt(s);if(!b)return false;
 let node;if(kind==='toggle'){
  if(b.node.type===schema.nodes.toggle)return true;
  node=schema.nodes.toggle.create({open:true},[schema.nodes.toggle_title.create(null,b.node.isTextblock?b.node.content:null),schema.nodes.toggle_body.create(null,paragraph())]);
 }else if(kind==='rule')node=schema.nodes.rule.create();
 else if(b.node.type===schema.nodes.toggle){
  const title=b.node.firstChild,body=b.node.lastChild;const first=schema.nodes.paragraph.create({kind:kind==='text'?'':kind},title.content);
  const tr=s.tr.replaceWith(b.pos,b.pos+b.node.nodeSize,Fragment.fromArray([first,...body.content.content]));view.dispatch(selectText(closeHistory(tr),b.pos+1));view.focus();return true;
 }else if(b.node.type===schema.nodes.image||b.node.type===schema.nodes.rule)node=schema.nodes.paragraph.create({kind:kind==='text'?'':kind});
 else node=schema.nodes.paragraph.create({...b.node.attrs,kind:kind==='text'?'':kind,checked:false},b.node.content);
 const tr=s.tr.replaceWith(b.pos,b.pos+b.node.nodeSize,node);if(kind==='rule'){tr.insert(b.pos+node.nodeSize,paragraph());selectText(tr,b.pos+node.nodeSize+1)}else selectText(tr,b.pos+(kind==='toggle'?2:1)+Math.min(s.selection.$from.parentOffset,node.type===schema.nodes.toggle?node.firstChild.content.size:node.content.size));view.dispatch(closeHistory(tr));view.focus();return true;
}
function moveBlock(view,dir){const b=blockAt(view.state);if(!b)return;const $p=view.state.doc.resolve(b.pos),parent=$p.parent,index=$p.index(),other=parent.maybeChild(index+dir);if(!other)return;
 const at=dir<0?b.pos-other.nodeSize:b.pos+b.node.nodeSize,from=dir<0?at:b.pos,to=dir<0?b.pos+b.node.nodeSize:at+other.nodeSize;
 const tr=view.state.tr.replaceWith(from,to,Fragment.fromArray(dir<0?[b.node,other]:[other,b.node]));view.dispatch(selectText(closeHistory(tr),dir<0?at+1:b.pos+other.nodeSize+1));view.focus();
}
function indent(view,dir){const {state}=view,b=blockAt(state);if(!b)return false;
 // Shift+Tab takes a block out of its enclosing toggle, preserving the block.
 const $p=state.doc.resolve(b.pos);if(dir<0&&$p.parent.type===schema.nodes.toggle_body){const wrapperDepth=$p.depth-1,outerPos=$p.before(wrapperDepth),outer=$p.node(wrapperDepth);if($p.parent.childCount===1){const tr=state.tr.replaceWith(b.pos,b.pos+b.node.nodeSize,paragraph());const after=tr.mapping.map(outerPos+outer.nodeSize);tr.insert(after,b.node);view.dispatch(selectText(tr,after+1));}else{const tr=state.tr.delete(b.pos,b.pos+b.node.nodeSize),after=tr.mapping.map(outerPos+outer.nodeSize);tr.insert(after,b.node);view.dispatch(selectText(tr,after+1));}view.focus();return true;}
 if(dir>0){const index=$p.index(),prev=index>0?$p.parent.child(index-1):null;if(prev?.type===schema.nodes.toggle){const start=b.pos-prev.nodeSize,bodyPos=start+prev.nodeSize-2,tr=state.tr.delete(b.pos,b.pos+b.node.nodeSize);tr.setNodeMarkup(start,null,{open:true});tr.insert(bodyPos,b.node);view.dispatch(selectText(tr,bodyPos+1));view.focus();return true;}}
 if(b.node.type!==schema.nodes.paragraph)return true;
 let tr=state.tr;const {from,to}=state.selection;state.doc.nodesBetween(from,to,(n,pos)=>{if(n.type===schema.nodes.paragraph)tr.setNodeMarkup(pos,null,{...n.attrs,depth:Math.min(4,Math.max(0,n.attrs.depth+dir))})});if(!tr.docChanged)tr.setNodeMarkup(b.pos,null,{...b.node.attrs,depth:Math.min(4,Math.max(0,b.node.attrs.depth+dir))});view.dispatch(tr);return true;
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
function backspace(view){if(undoInputRule(view.state,view.dispatch))return true;const s=view.state,{$from,empty}=s.selection;if(!empty||$from.parentOffset!==0)return false;const b=textBlock(s);if(!b)return false;
 if(b.node.type===schema.nodes.toggle_title)return changeKind(view,'text');
 if(b.node.attrs.kind||b.node.attrs.depth){view.dispatch(s.tr.setNodeMarkup(b.pos,null,{...b.node.attrs,kind:'',depth:0,checked:false}));return true;}
 if($from.depth>1&&$from.node($from.depth-1).type===schema.nodes.toggle_body&&$from.index($from.depth-1)===0)return indent(view,-1);
 return false;
}
function rules(){const specs=[[/^#\s$/,'h1'],[/^##\s$/,'h2'],[/^###\s$/,'h3'],[/^[-*•]\s$/,'li'],[/^1[.)]\s$/,'num'],[/^\[\s?\]\s$/,'todo'],[/^>>?\s$/,'toggle'],[/^["“]\s$/,'qt'],[/^!\s$/,'co'],[/^```\s$/,'code']];const blocks=specs.map(([re,kind])=>new InputRule(re,(state,match,start,end)=>{
 const $p=state.doc.resolve(start);if($p.parent.type!==schema.nodes.paragraph||$p.parent.attrs.kind)return null;const tr=state.tr.delete(start,end),pos=$p.before();if(kind==='toggle'){const original=tr.doc.nodeAt(pos);const toggle=schema.nodes.toggle.create({open:true},[schema.nodes.toggle_title.create(null,original.content),schema.nodes.toggle_body.create(null,paragraph())]);tr.replaceWith(pos,pos+original.nodeSize,toggle);return selectText(tr,pos+2)}return tr.setNodeMarkup(pos,null,{...$p.parent.attrs,kind});
 }));return [...blocks,...[['->','→'],['<-','←'],['=>','⇒']].map(([from,to])=>new InputRule(new RegExp(from.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'$'),(state,match,start,end)=>state.selection.$from.parent.attrs.kind==='code'?null:state.tr.insertText(to,start,end))),new InputRule(/(https?:\/\/[^\s<]+|www\.[^\s<]+\.[^\s<]+)\s$/,(state,match,start,end)=>{if(state.selection.$from.parent.attrs.kind==='code')return null;const url=/^https?:/i.test(match[1])?match[1]:'https://'+match[1];return state.tr.insertText(' ',end).addMark(start,end,schema.marks.link.create({href:url})).removeStoredMark(schema.marks.link)})];}
function decorations(state,placeholder){const d=[],number=new Map();state.doc.descendants((n,pos,parent)=>{if(n.type===schema.nodes.paragraph||n.type===schema.nodes.toggle_title){const attrs={};if(!n.content.size)attrs['data-placeholder']=n.type===schema.nodes.toggle_title?'토글 제목':parent.type===schema.nodes.toggle_body?'내용을 적거나 / 로 추가':state.doc.childCount===1?placeholder||'내용을 적거나 / 로 블록 추가':'/ 로 블록 추가';if(n.attrs.kind==='num'){let a=number.get(parent)||[0,0,0,0,0];a[n.attrs.depth]++;attrs['data-n']=String(a[n.attrs.depth]);number.set(parent,a)}else if(n.type===schema.nodes.paragraph)number.set(parent,[0,0,0,0,0]);if(Object.keys(attrs).length)d.push(Decoration.node(pos,pos+n.nodeSize,attrs));}});return DecorationSet.create(state.doc,d);}
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
 let linkDialog=null;
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

 function execute(view,key){consumeSlash(view);closeMenu();if(key==='image'){options.photo?.(view.dom,currentBlock(view.dom));return;}if(key==='link'){openLink(view);return;}changeKind(view,key);}
 function openMenu(view,{typed=false,rect=null,actions=false}={}){closeMenu();inline?.remove();inline=null;const dom=document.createElement('div');dom.className='nb-menu';dom.setAttribute('role','listbox');dom.setAttribute('aria-label','문단 메뉴');dom.innerHTML='<div class="nb-menu-label">'+(actions?'문단':'블록 추가')+'</div><div class="nb-menu-items"></div><div class="nb-menu-help">↑↓ 이동 · Enter 선택 · Esc 닫기</div>';document.body.append(dom);menu={view,dom,typed,q:'',index:0,actions,rect:rect||view.coordsAtPos(view.state.selection.from)};drawMenu();}
 function menuItems(){let items=commands.filter(c=>!menu.q||(c[1]+' '+c[0]+' '+c[3]).toLowerCase().includes(menu.q.toLowerCase()));if(menu.actions&&!menu.q)items=[['insert','아래에 문단 추가','+'],['up','위로 이동','↑'],['down','아래로 이동','↓'],['duplicate','복제','⧉'],['delete','삭제','×'],['undo','실행 취소','↶'],['redo','다시 실행','↷'],...items];return items;}
 function pick(index){if(!menu)return;const {view}=menu,key=menuItems()[index]?.[0];if(!key)return;consumeSlash(view);closeMenu();view.focus();const b=blockAt(view.state);if(key==='insert'&&b){const at=b.pos+b.node.nodeSize;view.dispatch(selectText(view.state.tr.insert(at,paragraph()),at+1));view.focus();return;}if(key==='up'||key==='down'){moveBlock(view,key==='up'?-1:1);return;}if(key==='undo'||key==='redo'){(key==='undo'?undo:redo)(view.state,view.dispatch);return;}if(key==='duplicate'&&b){const at=b.pos+b.node.nodeSize,tr=view.state.tr.insert(at,b.node);view.dispatch(selectText(closeHistory(tr),at+1));return;}if(key==='delete'&&b){const tr=view.state.tr.delete(b.pos,b.pos+b.node.nodeSize);view.dispatch(selectText(closeHistory(tr),Math.min(b.pos,tr.doc.content.size)));return;}execute(view,key);}
 function drawMenu(){if(!menu)return;const items=menuItems();menu.index=Math.max(0,Math.min(menu.index,items.length-1));menu.dom.querySelector('.nb-menu-items').innerHTML=items.length?items.map((c,i)=>`<button type="button" role="option" aria-selected="${i===menu.index}" data-block-command="${i}"><span class="nb-menu-icon">${c[2]}</span><span><b>${c[1]}</b>${c[3]?'<small>'+c[3]+'</small>':''}</span></button>`).join(''):'<div class="nb-no-results">맞는 블록이 없어요.</div>';place(menu.dom,menu.rect);menu.dom.querySelector('[aria-selected="true"]')?.scrollIntoView({block:'nearest'});}
 function slashUpdate(view){if(view.composing)return;if(menu&&menu.view!==view)closeMenu();const {$from,empty}=view.state.selection;if(!empty||!$from.parent.isTextblock){if(menu?.typed)closeMenu();return;}const pre=$from.parent.textBetween(0,$from.parentOffset,'\n','\n'),m=pre.match(/(?:^|\s)\/([^\s/]*)$/);if(!m){if(menu?.typed)closeMenu();return;}if(!menu)openMenu(view,{typed:true});if(menu?.typed){menu.q=m[1];drawMenu();}}
 function keyHandler(view,event){if(event.isComposing||view.composing)return false;view.domObserver.flush();if(event.key==='Escape'&&menu){closeMenu();return true;}if(menu?.view===view){const items=menuItems();if(event.key==='ArrowDown'||event.key==='ArrowUp'){menu.index=items.length?(menu.index+(event.key==='ArrowDown'?1:-1)+items.length)%items.length:0;drawMenu();return true;}if(event.key==='Enter'){pick(menu.index);return true;}if(event.key==='Tab'){closeMenu();return false;}}
 if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){openLink(view);return true;}if(event.key==='Tab')return indent(view,event.shiftKey?-1:1);return false;}
 function mount(host){if(views.has(host)||!host.isConnected||host.getAttribute('contenteditable')!=='true')return;const original=host.innerHTML,clean=document.createElement('div');clean.innerHTML=normalizeRichHTML(original);const doc=PMParser.fromSchema(schema).parse(clean);const entry={host,view:null,original,dirty:false,flushing:false};views.set(host,entry);
 const customKeys={'Enter':(s,d,v)=>enter(v),'Backspace':(s,d,v)=>backspace(v),'Mod-z':undo,'Shift-Mod-z':redo,'Mod-y':redo,'Mod-b':toggleMark(schema.marks.strong),'Mod-i':toggleMark(schema.marks.em),'Mod-u':toggleMark(schema.marks.underline),'Mod-`':toggleMark(schema.marks.code),'Shift-Enter':(s,d)=>{d(s.tr.replaceSelectionWith(schema.nodes.hard_break.create()).scrollIntoView());return true},'Alt-ArrowUp':(s,d,v)=>{moveBlock(v,-1);return true},'Alt-ArrowDown':(s,d,v)=>{moveBlock(v,1);return true}};
 const view=new EditorView({mount:host},{state:EditorState.create({schema,doc,plugins:[history(),inputRules({rules:rules()}),keymap(customKeys),keymap(baseKeymap),new Plugin({props:{decorations:state=>decorations(state,host.dataset.ph)}})]}),attributes:{class:'nb-editor',role:'textbox','aria-multiline':'true','aria-label':host.getAttribute('aria-label')||'글과 메모 편집기',spellcheck:'true'},nodeViews:{toggle:(...args)=>new ToggleView(...args)},handleKeyDown:keyHandler,
 dispatchTransaction(tr){const prev=view.state;view.updateState(view.state.apply(tr));if(tr.docChanged){entry.dirty=true;options.hydrate?.(host);emit(entry);}if((tr.docChanged||menu?.typed)&&tr.getMeta('uiEvent')!=='paste')slashUpdate(view);if(prev.selection!==view.state.selection||tr.docChanged)refreshUI(view);},
 handleDOMEvents:{beforeinput:(view,event)=>{if(event.inputType!=='insertParagraph'||event.isComposing||!event.cancelable)return false;view.domObserver.flush();if(keyHandler(view,{key:'Enter',isComposing:false})||enter(view)){event.preventDefault();return true;}return false;},focus:()=>{active=view;queueMicrotask(()=>refreshUI(view));return false},compositionstart:()=>{closeMenu();inline?.remove();inline=null;return false},compositionend:()=>{queueMicrotask(()=>slashUpdate(view));return false}},
 handleClick(view,pos,event){const block=event.target.closest('.todo');if(block&&event.clientX-block.getBoundingClientRect().left<26){const at=view.posAtDOM(block,0)-1,n=view.state.doc.nodeAt(at);if(n?.type===schema.nodes.paragraph){view.dispatch(view.state.tr.setNodeMarkup(at,null,{...n.attrs,checked:!n.attrs.checked}));return true;}}return false;},
 handlePaste(view,event){const cd=event.clipboardData;if(!cd)return false;const files=[...(cd.files||[])].filter(f=>/^image\//.test(f.type));if(files.length){options.photo?.(host,currentBlock(host),files);return true;}const text=cd.getData('text/plain'),html=cd.getData('text/html');if(/^https?:\/\/\S+$/i.test(text.trim())&&!view.state.selection.empty){const {from,to}=view.state.selection;view.dispatch(view.state.tr.addMark(from,to,schema.marks.link.create({href:text.trim()})));return true;}if(html||/https?:\/\/|www\./i.test(text)){const c=document.createElement('div');c.innerHTML=normalizeRichHTML(html||options.linkify?.(text)||'');const slice=PMParser.fromSchema(schema).parseSlice(c);view.dispatch(view.state.tr.replaceSelection(slice).scrollIntoView());return true;}return false;}
 });entry.view=view;options.hydrate?.(host);}
 function currentBlock(host){const view=withView(host);if(!view)return null;const b=blockAt(view.state);return b?view.nodeDOM(b.pos):null;}
 function refreshUI(view){if(!view.dom.isConnected||view.composing||linkDialog||drag?.view===view)return;if(!view.hasFocus()&&active!==view)return;active=view;tools?.remove();tools=null;inline?.remove();inline=null;
 const b=blockAt(view.state);if(!b)return;const node=view.nodeDOM(b.pos);if(!node?.getBoundingClientRect)return;const rect=node.getBoundingClientRect();if(!rect.width||rect.bottom<0||rect.top>innerHeight)return;
 tools=document.createElement('div');tools.className='nb-tools';tools.setAttribute('aria-label','문단 도구');tools.innerHTML='<button type="button" data-block-add aria-label="문단 추가" title="문단 추가">+</button><button type="button" data-block-menu draggable="true" aria-label="문단 서식 및 이동" title="서식 · 이동 (Alt+↑↓)">⠿</button>';document.body.append(tools);tools.style.left=Math.max(2,rect.left-(matchMedia('(pointer:coarse)').matches?38:44))+'px';tools.style.top=Math.max(0,rect.top-1)+'px';
 if(!view.state.selection.empty&&view.state.selection.$from.parent.isTextblock){inline=document.createElement('div');inline.className='nb-inline';inline.setAttribute('role','toolbar');inline.setAttribute('aria-label','선택한 글 서식');inline.innerHTML=[['strong','굵게','B'],['em','기울임','I'],['underline','밑줄','U'],['strike','취소선','S'],['code','인라인 코드','〈〉'],['link','링크','↗']].map(([k,l,t])=>`<button type="button" data-mark="${k}" aria-label="${l}">${t}</button>`).join('');document.body.append(inline);place(inline,view.coordsAtPos(view.state.selection.from),true);}
 }
 document.addEventListener('mousedown',event=>{if(event.target.closest('.nb-tools,.nb-menu,.nb-inline')){if(!event.target.closest('[draggable=true]'))event.preventDefault();return;}if(menu&&!event.target.closest('.nb-editor'))closeMenu();});
 document.addEventListener('click',event=>{let bt=event.target.closest('[data-block-command]');if(bt){pick(+bt.dataset.blockCommand);return;}if(event.target.closest('[data-block-menu]')&&active){openMenu(active,{actions:true,rect:event.target.getBoundingClientRect()});return;}if(event.target.closest('[data-block-add]')&&active){const view=active,b=blockAt(view.state);if(!b)return;if(b.node.type!==schema.nodes.paragraph||b.node.content.size){const at=b.pos+b.node.nodeSize;view.dispatch(selectText(view.state.tr.insert(at,paragraph()),at+1));}view.focus();openMenu(view);return;}bt=event.target.closest('[data-mark]');if(bt&&active){if(bt.dataset.mark==='link'){openLink(active);return;}else toggleMark(schema.marks[bt.dataset.mark])(active.state,active.dispatch);active.focus();refreshUI(active);}});
 document.addEventListener('click',event=>{const title=event.target.closest('.nb-toggle-title');if(!title||title.closest('.nb-editor'))return;event.preventDefault();event.stopImmediatePropagation();const wrap=title.parentElement;wrap.dataset.expanded=String(wrap.dataset.expanded==='false');title.setAttribute('aria-expanded',String(wrap.dataset.expanded!=='false'));},true);
 document.addEventListener('keydown',event=>{const title=event.target;if(!title.matches?.('.nb-toggle-title[role=button]')||title.closest('.nb-editor')||!['Enter',' '].includes(event.key))return;event.preventDefault();event.stopImmediatePropagation();const wrap=title.parentElement;wrap.dataset.expanded=String(wrap.dataset.expanded==='false');title.setAttribute('aria-expanded',String(wrap.dataset.expanded!=='false'));},true);
 document.addEventListener('selectionchange',()=>{if(active?.hasFocus()&&!active.composing&&!menu)refreshUI(active)});
 document.addEventListener('focusin',event=>{const host=event.target.closest?.('.rt[contenteditable="true"]');if(host){mount(host);active=views.get(host)?.view;}else if(!event.target.closest('.nb-tools,.nb-menu,.nb-inline,.lpop,#one')){hideUI();active=null;}},true);
 document.addEventListener('pointerdown',event=>{if(!event.target.closest('.nb-tools,.nb-menu,.nb-inline,.nb-editor,.lpop,#one')){hideUI();active=null;}});
 document.addEventListener('dragstart',event=>{if(!event.target.closest('[data-block-menu]')||!active)return;const b=blockAt(active.state);if(!b)return;drag={view:active,...b};event.dataTransfer.setData('application/x-arecmik-block','move');event.dataTransfer.effectAllowed='move';closeMenu();});
 document.addEventListener('dragover',event=>{if(!drag)return;const host=event.target.closest('.nb-editor');if(host!==drag.view.dom)return;event.preventDefault();event.dataTransfer.dropEffect='move';});
 document.addEventListener('drop',event=>{if(!drag)return;const {view,node,pos}=drag;drag=null;if(!view.dom.contains(event.target))return;event.preventDefault();event.stopPropagation();let targetDOM=event.target.nodeType===1?event.target:event.target.parentElement;while(targetDOM&&targetDOM.parentElement!==view.dom&&!targetDOM.parentElement?.classList.contains('nb-toggle-body'))targetDOM=targetDOM.parentElement;if(!targetDOM||targetDOM===view.dom)return;let target=view.posAtDOM(targetDOM.parentNode,[...targetDOM.parentNode.childNodes].indexOf(targetDOM));const targetNode=view.state.doc.nodeAt(target),rect=targetDOM.getBoundingClientRect();if(!targetNode)return;if(event.clientY>rect.top+rect.height/2)target+=targetNode.nodeSize;if(target>=pos&&target<=pos+node.nodeSize)return;const tr=view.state.tr.delete(pos,pos+node.nodeSize),at=tr.mapping.map(target);try{tr.insert(at,node);view.dispatch(selectText(closeHistory(tr),at+1));view.focus()}catch(_){/* Invalid structural drop leaves the document unchanged. */}},true);
 document.addEventListener('dragend',()=>{drag=null});
 window.addEventListener('scroll',event=>{if(drag)return;if(menu){if(menu.dom.contains(event.target))return;if(menu.view.dom.isConnected){menu.rect=menu.view.coordsAtPos(menu.view.state.selection.from);place(menu.dom,menu.rect);}else closeMenu();}if(active?.hasFocus())refreshUI(active);else if(!menu&&!linkDialog)hideUI()},{passive:true,capture:true});
 function viewportChanged(){if(menu){if(menu.view.dom.isConnected){menu.rect=menu.view.coordsAtPos(menu.view.state.selection.from);place(menu.dom,menu.rect);}else closeMenu();}if(active?.hasFocus())refreshUI(active);}
 window.addEventListener('resize',viewportChanged);window.visualViewport?.addEventListener('resize',viewportChanged);
 function scan(){document.querySelectorAll('.rt:not([contenteditable]) .nb-toggle-title').forEach(title=>{if(title.closest('.nb-editor'))return;title.setAttribute('role','button');title.tabIndex=0;title.setAttribute('aria-expanded',String(title.parentElement.dataset.expanded!=='false'));});for(const [host,entry] of views)if(!host.isConnected){if(active===entry.view){hideUI();active=null;}entry.view.destroy();views.delete(host);}document.querySelectorAll('.rt[contenteditable="true"]').forEach(mount);}
 let pending=false;new MutationObserver(()=>{if(pending)return;pending=true;queueMicrotask(()=>{pending=false;scan();});}).observe(document.body,{childList:true,subtree:true});scan();
 return {
  has:host=>views.has(host),
  busy:()=>!!linkDialog,
  link(host,anchor){const view=withView(host);if(view)openLink(view,anchor);},
  closeTopLayer(){if(linkDialog){linkDialog.cancel();return true;}if(menu){closeMenu();active?.focus();return true;}return false;},
  serialize(host){const view=withView(host),entry=views.get(host);if(!view)return null;if(!entry.dirty)return entry.original;const c=document.createElement('div');c.append(DOMSerializer.fromSchema(schema).serializeFragment(view.state.doc.content));return c.innerHTML;},
  currentBlock,
  insertImage(host,block,id){const view=withView(host);if(!view)return null;let b=blockAt(view.state);if(block&&host.contains(block)){try{let pos=view.posAtDOM(block,0);const $p=view.state.doc.resolve(pos);if($p.parent.isTextblock)b={node:$p.parent,pos:$p.before()};}catch(_){}}
   if(!b)b={node:null,pos:view.state.doc.content.size};const replace=b.node?.type===schema.nodes.paragraph&&!b.node.content.size,at=replace?b.pos:b.pos+(b.node?.nodeSize||0);const image=schema.nodes.image.create({id}),nx=paragraph(),tr=view.state.tr.replaceWith(at,replace?at+b.node.nodeSize:at,Fragment.fromArray([image,nx]));view.dispatch(selectText(closeHistory(tr),at+image.nodeSize+1));options.hydrate?.(host);view.focus();return view.nodeDOM(at+image.nodeSize);
  }
 };
}
