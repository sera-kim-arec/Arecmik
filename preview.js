// Only the isolated sample page uses these layout changes. Original editors,
// actions and data are reused; changing the comparison mode never copies data.
let previewLayout='refined';
const previewFoldState=new Map();

function previewFold(section,key,title,hint='',initialOpen=false){
 if(!section)return null;
 const scope=[U.tab,U.sp,U.pid,key].join(':'),fold=document.createElement('details');
 fold.className='g preview-fold';fold.dataset.previewFold=key;
 fold.open=previewFoldState.get(scope)??initialOpen;
 const summary=document.createElement('summary');
 summary.innerHTML=`<span class="preview-fold-title">${esc(title)}</span><span class="preview-fold-hint">${esc(hint)}</span><span class="preview-chevron" aria-hidden="true">⌄</span>`;
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
  const undated=D.todos.filter(x=>inSp(x)&&!x.done&&!x.date).length;
  extras.append(previewFold(und,'undated',late?'미뤄 둔 할 일 · 날짜 없는 할 일':'날짜 없는 할 일',`${late+undated}개`,late>0));
 }
 if(bottom){
  const sections=[...bottom.querySelectorAll(':scope > .col > section')];
  for(const section of sections){
   const memo=section.classList.contains('rcard'),spend=section.classList.contains('spend');
   extras.append(previewFold(section,memo?'memo':spend?'spend':'journal',memo?'잊지 말 것 · 자료':spend?'쓴 돈':`오늘 ${LW(U.sp).t}`,memo?'메모와 자주 쓰는 정보':spend?'선택한 날짜의 지출':'하루를 한 줄씩 남겨요'));
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
 if(timeline)more.append(previewFold(timeline,'timeline','타임라인','일정과 기록의 흐름'));
 const history=main.querySelector('.pmemo:not(.pcore)');
 if(history)more.append(previewFold(history,'history','진행 기록',`${D.moms.filter(m=>m.pid===project.id).length}개 · 날짜별로 모아보기`));
 const records=main.querySelector('.project-records');
 if(records)more.append(previewFold(records,'records','관련 기록','글 · 메모 · 자료를 함께 보기'));
}

function previewRecordsLayout(main){
 const archive=main.querySelector('.archive');if(!archive)return;
 const heading=main.querySelector('.rh'),intro=archive.querySelector('.archive-intro');
 const action=intro?.querySelector('[data-record-new]');if(action&&heading)heading.append(action);
 intro?.querySelector('h2')?.remove();
 const tools=[...archive.querySelectorAll(':scope > .archive-tools')];if(tools.length!==2)return;
 const toolbar=document.createElement('div');toolbar.className='preview-record-toolbar';
 const favorite=tools[0].querySelector('[data-archive-favorites]');if(favorite)toolbar.append(favorite);
 const count=tools[1].querySelector('.archive-help');if(count)toolbar.append(count);
 const contents=document.createElement('div');contents.className='preview-filter-controls';
 tools[0].before(toolbar,contents);contents.append(...tools);
 const state=archiveState[U.sp],active=[state.kind,state.month,state.pid].filter(Boolean).length;
 const fold=previewFold(contents,'filters','필터',active?`${active}개 조건 적용 중`:'종류 · 월 · 프로젝트');
 fold.classList.add('preview-filter-fold');
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
 const choice=event.target.closest?.('[data-preview-layout]');if(!choice||choice.dataset.previewLayout===previewLayout)return;
 flushAutoSaves();captureLineInputs();document.activeElement?.blur();
 previewLayout=choice.dataset.previewLayout==='current'?'current':'refined';render();
});
