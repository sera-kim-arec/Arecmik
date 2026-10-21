// Only the isolated sample page uses these layout changes. Original editors,
// actions and data are reused; changing the comparison mode never copies data.
let previewLayout='refined';
const previewFoldState=new Map();
const previewTypeScroll=new Map();
const previewSnippet=(value,max=60)=>{const s=String(value||'').replace(/\s+/g,' ').trim();return s.length>max?s.slice(0,max)+'…':s};
function previewEditorSummary(editor){const text=previewSnippet(txt(outHTML(editor))),photos=editor.querySelectorAll('img').length;return text||(photos?`사진 ${photos}장`:'')}

function previewFold(section,key,title,hint='',initialOpen=false){
 if(!section)return null;
 const scope=[U.tab,U.sp,U.pid,key].join(':'),fold=document.createElement('details');
 fold.className='g preview-fold';fold.dataset.previewFold=key;
 fold.open=previewFoldState.get(scope)??initialOpen;
 const summary=document.createElement('summary');
 summary.innerHTML=`<span class="preview-fold-title">${esc(title)}</span><span class="preview-fold-hint">${esc(hint)}</span><span class="preview-chevron" aria-hidden="true">⌄</span>`;
 summary.querySelector('.preview-fold-hint').title=hint;
 const body=document.createElement('div');body.className='preview-fold-body';
 section.replaceWith(fold);body.append(section);fold.append(summary,body);
 fold.addEventListener('toggle',()=>{
  previewFoldState.set(scope,fold.open);
  if(fold.open&&key==='timeline'&&U.pid&&PJ(U.pid))requestAnimationFrame(()=>drawTL(PJ(U.pid)));
 });
 return fold;
}

function previewHomeLayout(main){
 const extras=document.createElement('div');extras.className='preview-home-extras';
 const und=main.querySelector('.undbox'),bottom=main.querySelector('.hg');
 if(und){
  const late=D.todos.filter(x=>inSp(x)&&!x.done&&x.date&&endOf(x)<T()&&!isEv(x)).length;
  const pending=D.todos.filter(x=>inSp(x)&&!x.done&&(!x.date||endOf(x)<T()&&!isEv(x)));
  const names=pending.sort(ordT).slice(0,2).map(x=>x.title).join(' · ');
  extras.append(previewFold(und,'undated',late?'미룬 일 · 날짜 없는 일':'날짜 없는 할 일',`${pending.length}개${names?' · '+previewSnippet(names):''}`,late>0));
 }
 if(bottom){
  const sections=[...bottom.querySelectorAll(':scope > .col > section')];
  for(const section of sections){
   const memo=section.classList.contains('rcard'),spend=section.classList.contains('spend');
   if(memo){
    const editor=section.querySelector('[data-memo]'),reminder=document.createElement('section');
    reminder.className='preview-reminder-editor';
    if(editor){section.querySelector('.ct')?.remove();reminder.append(editor);}
    const fold=previewFold(reminder,'reminder','잊지 말 것',previewEditorSummary(editor));
    fold.classList.add('preview-reminder');main.querySelector('.hhead')?.after(fold);
    const hint=fold.querySelector('.preview-fold-hint');
    editor.addEventListener('input',()=>{hint.textContent=previewEditorSummary(editor);hint.title=txt(outHTML(editor))});
    section.querySelector('.ct')?.removeAttribute('style');
    extras.append(previewFold(section,'refs','자료',`${D.refs.filter(inSp).length}개`));
   }else{
    const k=U.calSel||T(),rows=spend?expDay(k):[],journal=getLogs(U.sp)[T()];
    const hint=spend?`${won(rows.reduce((sum,e)=>sum+expAmt(e),0))}원 · ${rows.length}건`:previewSnippet(txt(journal?.html||''));
    extras.append(previewFold(section,spend?'spend':'journal',spend?'쓴 돈':`오늘 ${LW(U.sp).t}`,hint));
   }
  }
  bottom.replaceWith(extras);
 }else main.append(extras);
 const panel=main.querySelector('.dside');
 if(panel){
  const tasks=D.todos.filter(x=>inSp(x)&&onDay(x,U.calSel));
  const overview=document.createElement('p');overview.className='preview-day-overview';
  overview.textContent=`일정 ${tasks.filter(isEv).length} · 할 일 ${tasks.filter(x=>!isEv(x)).length} · 완료 ${tasks.filter(x=>x.done).length}`;
  panel.querySelector('.ct')?.after(overview);
 }
}

function previewProjectLayout(main){
 const project=PJ(U.pid),grid=main.querySelector('.pg');if(!project||!grid)return;
 const up=grid.querySelector('.up'),core=main.querySelector('.pcore');
 const secondary=[...grid.querySelectorAll('.pcol > section')];
 const primary=document.createElement('div');primary.className='preview-project-primary';
 const more=document.createElement('div');more.className='preview-project-more';
 grid.before(primary,more);if(up)primary.append(up);if(core)primary.append(core);
 const tasks=ptodos(project),remaining=tasks.filter(t=>!t.done);
 const title=up?.querySelector('.ct');
 if(title)title.firstChild.textContent='다음 일정 · 할 일';
 const overview=document.createElement('p');overview.className='preview-project-overview';
 overview.textContent=`남은 일 ${remaining.length}개 · 완료 ${tasks.length-remaining.length}/${tasks.length}`;
 main.querySelectorAll('.ph .meta>span').forEach(span=>{if(span.textContent.startsWith('할 일 '))span.remove()});
 main.querySelector('.ph')?.after(overview);
 for(const section of secondary){
  const cost=section.classList.contains('pcost');
  more.append(previewFold(section,cost?'cost':'status',cost?'비용':'업체 · 항목',cost?`${won(pExpSum(project))}원 지급`:`${pRows(project).length}개 항목`,!cost&&!!rowOpen&&pRows(project).some(r=>r.id===rowOpen)));
 }
 grid.remove();
 const timeline=main.querySelector('.tlc');
 if(timeline)more.append(previewFold(timeline,'timeline','타임라인',`${tasks.filter(t=>t.date).length}개 일정 · ${D.moms.filter(m=>m.pid===project.id).length}개 기록`));
 const history=main.querySelector('.pmemo:not(.pcore)');
 const recent=D.moms.filter(m=>m.pid===project.id).sort((a,b)=>(b.d||'').localeCompare(a.d||'')||(b.at||0)-(a.at||0));
 if(history)more.append(previewFold(history,'history','진행 기록',recent.length?`${md(recent[0].d||T())} · ${previewSnippet(recent[0].t||txt(recent[0].h||''))}`:''));
 const records=main.querySelector('.project-records');
 if(records){const first=records.querySelector('.archive-content strong'),count=records.querySelector('.ct small')?.textContent||`${records.querySelectorAll('.archive-row').length}개`;more.append(previewFold(records,'records','관련 기록',`${count}${first?' · '+previewSnippet(first.textContent):''}`))}
}

function previewRecordsLayout(main){
 const heading=main.querySelector('.rh');if(!heading)return;
 heading.querySelector('.seg')?.remove();
 const write=document.createElement('details');write.className='preview-write';
 write.innerHTML='<summary>＋ 기록 남기기</summary><div class="g solid preview-write-options"><button type="button" data-record-new="">짧은 기록</button><button type="button" data-preview-journal>오늘 '+LW(U.sp).t+'</button><button type="button" data-newdoc>긴 글</button><button type="button" data-newref>자료</button></div>';
 heading.append(write);
 if(U.rt!=='archive'&&!U.q.trim()){
  const back=document.createElement('button');back.className='back';back.dataset.previewArchiveBack='';back.textContent='‹ 기록 전체';heading.before(back);
  heading.querySelector('h1').textContent={log:LW(U.sp).t,doc:'글',ref:'자료'}[U.rt]||'기록';return;
 }
 const original=main.querySelector('.archive')||main.querySelector('.archive-list');if(!original)return;
 const state=archiveState[U.sp],q=U.q.trim(),all=archiveEntries(!!state.favorites||!!q,!!q);
 const rows=all.filter(r=>(!state.favorites||archiveIsFavorite(r.kind,r.id))&&(!state.kind||(state.kind==='record'?['mom','pmemo','fb'].includes(r.kind):r.kind===state.kind))&&(!state.month||r.date.startsWith(state.month))&&(!state.pid||r.pid===state.pid||connectionUI?.belongsToProject(r.kind,r.id,state.pid))&&(!q||archiveMatches(r,q)));
 const months=[...new Set([...all.map(r=>r.date.slice(0,7)),...(state.month?[state.month]:[])])].filter(Boolean).sort().reverse();
 const archive=document.createElement('section');archive.className='archive preview-archive';
 const kinds=[['','전체'],['record','메모·기록'],['log','일지'],['doc','글'],['ref','자료'],['todo','할 일·일정'],['expense','지출']];
 const favorite=`<button type="button" data-archive-favorites class="${state.favorites?'on':''}" aria-pressed="${!!state.favorites}">★ 즐겨찾기</button>`;
 const chips=kinds.map(([k,l],i)=>`<button type="button" data-archive-filter="${k}" aria-pressed="${state.kind===k}" class="${state.kind===k?'on':''}">${l}</button>${i===0?favorite:''}`).join('');
 let day='';
 const feed=rows.slice(0,state.limit).map(r=>{const head=day!==r.date?`<h3 class="archive-day">${r.date?r.date.replace(/-/g,'. '):'날짜 없음'}${r.date?' · '+DOW[P(r.date).getDay()]:''}</h3>`:'';day=r.date;return head+archiveRow(r,q)}).join('');
 const filtered=!!(q||state.kind||state.month||state.pid||state.favorites);
 archive.innerHTML=`<div class="preview-record-types" role="group" aria-label="기록 분류">${chips}</div><div class="preview-record-toolbar"><span class="archive-help">${rows.length}개의 기록</span>${filtered?'<button type="button" class="link" data-preview-reset>조건 지우기</button>':''}</div><div class="preview-filter-controls"><div class="archive-tools"><select data-archive-month aria-label="기록 월"><option value="">모든 달</option>${months.map(m=>`<option value="${m}"${m===state.month?' selected':''}>${m.replace('-','년 ')}월</option>`).join('')}</select><select data-archive-project aria-label="기록 프로젝트"><option value="">모든 프로젝트</option>${D.projects.filter(inSp).map(p=>`<option value="${esc(p.id)}"${p.id===state.pid?' selected':''}>${esc(p.name)}</option>`).join('')}</select></div></div><div class="g box archive-list">${feed||`<div class="archive-empty">${filtered?'조건에 맞는 기록이 없어요.':'아직 기록이 없어요.'}<div class="empty-actions">${filtered?'<button type="button" class="soft" data-preview-reset>조건 지우기</button>':''}<button type="button" class="soft" data-record-new="">기록 남기기</button></div></div>`}${rows.length>state.limit?'<button class="soft" data-archive-more>이전 기록 더 보기</button>':''}</div>`;
 original.replaceWith(archive);
 const active=[state.month,state.pid&&PJ(state.pid)?.name].filter(Boolean).join(' · ');
 const fold=previewFold(archive.querySelector('.preview-filter-controls'),'filters','날짜 · 프로젝트',active);fold.classList.add('preview-filter-fold');
 const types=archive.querySelector('.preview-record-types');types.scrollLeft=previewTypeScroll.get(U.sp)||0;
 const space=U.sp;types.addEventListener('scroll',()=>previewTypeScroll.set(space,types.scrollLeft),{passive:true});
 archive.querySelectorAll('.archive-row').forEach(row=>{const kind=row.querySelector('.archive-kind'),content=row.querySelector('.archive-content');if(kind&&content)content.prepend(kind)});
 archive.querySelectorAll('.archive-context').forEach(el=>{
  el.textContent=el.textContent.replace(/^\d{4}-\d{2}-\d{2}(\s*·\s*)?/,'');
 });
}

function applyPreviewHints(){
 document.getElementById('preview-loading')?.remove();
 document.documentElement.classList.toggle('preview-refined',previewLayout==='refined');
 document.querySelectorAll('[data-preview-layout]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.previewLayout===previewLayout)));
 const main=document.getElementById('main');
 if(!main||previewLayout!=='refined'||main.querySelector(':scope > [data-preview-organized]'))return;
 if(U.tab==='home')previewHomeLayout(main);
 else if(U.tab==='proj'&&U.pid)previewProjectLayout(main);
 else if(U.tab==='rec'&&!U.doc)previewRecordsLayout(main);
 if(main.firstElementChild)main.firstElementChild.dataset.previewOrganized='true';
}

document.addEventListener('click',event=>{
 if(event.target.closest?.('.preview-write-options'))event.target.closest('.preview-write')?.removeAttribute('open');
 if(event.target.closest?.('[data-preview-journal]')){go('rec',{rt:'log',doc:'',q:'',editLog:T(),ry:+T().slice(0,4),rm:+T().slice(5,7)});return}
 if(event.target.closest?.('[data-preview-archive-back]')){go('rec',{rt:'archive',doc:'',q:''});return}
 if(event.target.closest?.('[data-preview-reset]')){Object.assign(archiveState[U.sp],{kind:'',month:'',pid:'',favorites:false,limit:40});U.q='';U.rt='archive';render();return}
 const choice=event.target.closest?.('[data-preview-layout]');if(!choice||choice.dataset.previewLayout===previewLayout)return;
 flushAutoSaves();captureLineInputs();document.activeElement?.blur();
 previewLayout=choice.dataset.previewLayout==='current'?'current':'refined';render();
});
document.addEventListener('click',event=>{if(previewLayout==='refined'&&event.target.closest?.('.preview-record-types [data-archive-filter],.preview-record-types [data-archive-favorites]'))U.rt='archive'},true);
