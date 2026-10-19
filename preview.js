/* Appended to the real app module by build-preview.py. No real account is used. */
function applyPreviewHints(){
 document.getElementById('preview-loading')?.remove();
 if(document.documentElement.dataset.previewChanges!=='on')return;
 if(U.tab==='home'){
  const panel=$('.dside');if(!panel)return;
  panel.querySelectorAll('.dlist>.itw').forEach(row=>{
   const id=row.querySelector('[data-edit]')?.dataset.edit,t=D.todos.find(t=>t.id===id);
   if(!t||!isEv(t))return;
   const link=document.createElement('div');link.className='preview-record-link';
   const button=document.createElement('button');button.type='button';button.textContent='이 일정에 기록 남기기';button.dataset.previewEvent=id;link.append(button);row.append(link);
  });
 }
 if(U.tab==='proj'&&U.pid){
  const sections=[['할 일','.up'],['진행 기록','.pmemo:not(.pcore)'],['관련 글','.project-records']];
  const nav=document.createElement('div');nav.className='preview-jumps';nav.setAttribute('aria-label','프로젝트 내용 바로가기');
  sections.forEach(([text,selector])=>{if(!$(selector))return;const button=document.createElement('button');button.textContent=text+' ↓';button.dataset.previewJump=selector;nav.append(button);});
  $('.ph')?.after(nav);
 }
 if(U.tab==='rec'&&!U.doc){
  const help=document.createElement('p');help.className='preview-record-help';help.textContent=(U.sp==='work'?'업무일지':'일기')+'는 하루의 흐름 · 글은 길게 남길 내용 · 자료는 자주 꺼내볼 정보';$('.rh')?.after(help);
 }
}
document.addEventListener('click',event=>{
 const mode=event.target.closest('[data-preview-mode]');
 if(mode){document.documentElement.dataset.previewChanges=mode.dataset.previewMode;document.querySelectorAll('[data-preview-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b===mode)));render();return;}
 const jump=event.target.closest('[data-preview-jump]');if(jump){$(jump.dataset.previewJump)?.scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion:reduce)').matches?'auto':'smooth'});return;}
 const record=event.target.closest('[data-preview-event]');if(record){const task=D.todos.find(t=>t.id===record.dataset.previewEvent);if(!task)return;recordSheet(null,task.projectId||'');$('#record-day').value=U.calSel;$('#record-body').innerHTML='<div>'+esc(task.title)+'에서 기억할 것</div><div><br></div>';persistRecordDraft();}
});
