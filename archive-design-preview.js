/* An isolated layout prototype: example data and drafts live in memory only. */
(() => {
  'use strict';
  const $=selector=>document.querySelector(selector);
  const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const shapes={search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/>',book:'<path d="M5 3h13v18H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"/><path d="M6 3v14h12M3 19h15M10 7h5"/>',movie:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4"/>',daily:'<path d="M5 3h14v18H5zM9 3v18M12 8h4M12 12h4"/>',note:'<path d="M6 3h8l4 4v14H6zM14 3v5h4M9 12h6M9 16h4"/>',folder:'<path d="M3 6h6l2 2h10v11H3zM3 6V4h6l2 2h8v2"/>',star:'<path d="m12 3 2.8 5.7 6.3.9-4.6 4.5 1.1 6.3-5.6-3-5.6 3 1.1-6.3L3 9.6l6.2-.9z"/>',close:'<path d="m6 6 12 12M18 6 6 18"/>',arrow:'<path d="M5 12h14m-5-5 5 5-5 5"/>',link:'<path d="m10 14 4-4m-6 6-2 2a3 3 0 0 1-4-4l4-4a3 3 0 0 1 4 0m4 0 2-2a3 3 0 0 1 4 4l-4 4a3 3 0 0 1-4 0"/>',all:'<rect x="4" y="4" width="6" height="6" rx="1"/><rect x="14" y="4" width="6" height="6" rx="1"/><rect x="4" y="14" width="6" height="6" rx="1"/><rect x="14" y="14" width="6" height="6" rx="1"/>'};
  const icon=name=>`<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${shapes[name]||shapes.note}</svg>`;
  const labels={daily:'일상',book:'독서',movie:'영화',note:'메모',journal:'업무일지'};
  const folders=[{id:'life-reading',space:'life',name:'독서와 문장'},{id:'life-perspective',space:'life',name:'새로운 관점'},{id:'life-travel',space:'life',name:'여행'},{id:'work-hr',space:'work',name:'인사·채용'},{id:'work-onboard',space:'work',name:'입사 안내',parent:'work-hr'},{id:'work-forms',space:'work',name:'서식'},{id:'work-guides',space:'work',name:'업무 가이드'}];
  const today=new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Seoul'});
  let nextId=1;
  const items=[
    {id:'life-book',space:'life',mode:'record',kind:'book',title:'책을 덮고 나서 남은 생각',body:'끝까지 읽고 나니, 잘 이해하려는 마음에도 기다림이 필요하다는 생각이 들었다.\n\n오늘은 마음에 남은 장면 한 가지를 내 말로 적어두었다. 다음에 읽을 때는 지금과 다른 생각이 들지도 모르겠다.',date:today,fav:false,related:['life-quote']},
    {id:'life-film',space:'life',mode:'record',kind:'movie',title:'영화를 보고, 집으로 돌아오는 길',body:'좋아하는 장면을 바로 설명하지 못해도 괜찮았다.\n\n집으로 돌아오는 동안 자꾸 떠오르던 표정 하나. 조용한 영화를 오래 기억하게 되는 이유를 조금 알 것 같았다.',date:today,fav:false},
    {id:'life-day',space:'life',mode:'record',kind:'daily',title:'별일 없어서 좋았던 하루',body:'오랜만에 서두르지 않고 걸었다. 빵집에 들렀다가, 집에 와서 따뜻한 차를 마셨다.\n\n이런 날도 잊지 않고 모아두고 싶다.',date:'2026-10-21',fav:true},
    {id:'life-book2',space:'life',mode:'record',kind:'book',title:'천천히 읽을수록 보이는 것들',body:'한 번에 많이 읽는 것보다, 읽은 뒤 잠깐 멈추는 시간이 좋았다.\n\n기억하고 싶은 질문을 한 가지 남겼다. 나는 요즘 무엇을 너무 빨리 판단하고 있을까?',date:'2026-10-19',fav:false},
    {id:'life-quote',space:'life',mode:'library',folder:'life-reading',title:'다시 읽고 싶은 문장과 질문',body:'책을 읽다가 다시 생각해 보고 싶었던 질문들을 모은 예시 자료예요.\n\n• 내가 당연하게 여긴 기준은 어디에서 왔을까?\n• 같은 장면을 다르게 바라볼 수 있을까?\n• 지금의 내 생각을 바꾼 경험은 무엇일까?',date:today,fav:true,related:['life-book']},
    {id:'life-interview',space:'life',mode:'library',folder:'life-perspective',title:'좋은 질문을 만드는 사람들의 습관',body:'인터뷰를 읽으며 참고하고 싶은 점을 모았어요.\n\n대답을 서둘러 정리하지 않기. 구체적인 경험을 한 번 더 물어보기. 모르는 것은 모른다고 말하기.\n\n다음에 누군가와 깊게 이야기하고 싶을 때 다시 꺼내 볼 자료예요.',date:today,fav:true},
    {id:'life-reading-guide',space:'life',mode:'library',folder:'life-reading',title:'독서 모임에서 나눠 볼 질문들',body:'어떤 장면이 가장 오래 남았나요?\n같은 상황이라면 다른 선택을 했을까요?\n읽기 전과 후에 달라진 생각이 있나요?',date:'2026-10-22',fav:false},
    {id:'life-trip',space:'life',mode:'library',folder:'life-travel',title:'다음 여행에서 가 보고 싶은 곳',body:'조용히 걷기 좋은 길, 해 질 무렵 들르고 싶은 바다, 혼자 오래 앉아 있어도 편한 카페.\n\n이름과 위치를 알아볼 때마다 이 자료에 모아두기.',date:'2026-10-20',fav:false},
    {id:'life-loose',space:'life',mode:'library',folder:'',title:'나중에 한 번 더 생각해 볼 관점',body:'지금 분류를 정하지 않아도 우선 보관해 두고, 필요할 때 검색해서 다시 읽어보기.',date:'2026-10-18',fav:false},
    {id:'work-journal',space:'work',mode:'record',kind:'journal',title:'입사 안내 절차를 정리한 날',body:'반복해서 받는 질문을 확인하고 안내 순서를 정리했다.\n\n입사 전 안내에서 빠지기 쉬운 항목은 자료실의 체크리스트에 모았다. 다음 담당자에게 설명할 때도 같은 자료를 사용하면 좋겠다.',date:today,fav:false,related:['work-guide']},
    {id:'work-memo',space:'work',mode:'record',kind:'note',title:'이번 주 회의에서 정한 것',body:'진행 상황을 길게 나열하기보다, 결정한 내용과 다음에 확인할 일을 먼저 적기로 했다.\n\n서로 다른 곳에 메모하지 않고, 같은 자료를 보고 이야기하기.',date:'2026-10-22',fav:true},
    {id:'work-retro',space:'work',mode:'record',kind:'journal',title:'반복 업무를 조금 가볍게 만들기',body:'지난달 자료를 찾는 데 걸린 시간이 생각보다 길었다.\n\n자주 쓰는 양식과 절차를 한곳에 모으고, 이름을 구체적으로 적어두었다.',date:'2026-10-20',fav:false},
    {id:'work-guide',space:'work',mode:'library',folder:'work-onboard',title:'신규 입사자 안내 체크리스트',body:'입사 전\n• 제출 서류와 기한 안내\n• 출근 장소와 담당자 연락처 전달\n\n첫 출근일\n• 계정과 기본 도구 확인\n• 사내 규정과 필요한 연락처 안내\n\n입사 후\n• 제출 서류 누락 확인\n• 정기적으로 확인할 절차 안내',date:today,fav:true,related:['work-journal','work-form']},
    {id:'work-form',space:'work',mode:'library',folder:'work-forms',title:'자주 쓰는 안내 메일 문구',body:'안녕하세요. 요청하신 내용을 안내드립니다.\n\n확인이 필요한 사항\n1. 대상과 진행 일정\n2. 제출해야 할 자료\n3. 담당자와 문의 방법\n\n검토 후 편하신 방법으로 회신 부탁드립니다.',date:'2026-10-22',fav:true},
    {id:'work-procedure',space:'work',mode:'library',folder:'work-hr',title:'채용 진행 단계별 확인 사항',body:'모집 전: 역할과 일정 확인\n서류 검토: 판단 기준 공유\n면접 전: 안내 문구와 질문 확인\n면접 후: 결정 내용과 회신 일정 기록',date:'2026-10-21',fav:false},
    {id:'work-report',space:'work',mode:'library',folder:'work-guides',title:'보고서를 작성하기 전에 확인할 것',body:'누가 읽는지, 어떤 결정을 돕는지, 필요한 근거는 무엇인지 먼저 확인한다.\n\n결론 → 근거 → 필요한 다음 행동 순서로 정리하기.',date:'2026-10-19',fav:false}
  ];
  const bucket=()=>({query:'',kind:'',folder:'',favorites:false});
  const views={life:{record:bucket(),library:bucket()},work:{record:bucket(),library:bucket()}};
  const state={space:'life',mode:'record',selected:null,editing:false};
  const drafts=new Map();
  const view=()=>views[state.space][state.mode];
  const all=()=>items.filter(item=>item.space===state.space&&item.mode===state.mode);
  const folderPath=id=>{const names=[],seen=new Set();let folder=folders.find(f=>f.id===id);while(folder&&!seen.has(folder.id)){seen.add(folder.id);names.unshift(folder.name);folder=folders.find(f=>f.id===folder.parent)}return names.join(' / ')};
  const descendants=id=>{const ids=new Set([id]);for(let pass=0;pass<folders.length;pass++)for(const folder of folders)if(ids.has(folder.parent))ids.add(folder.id);return ids};
  const types=()=>state.space==='life'?['daily','book','movie']:['journal','note'];
  const stamp=date=>{const parts=date.split('-');return `${+parts[1]}.${+parts[2]}`};
  const itemContext=item=>item.mode==='record'?labels[item.kind]||'기록':folderPath(item.folder)||'폴더 없음';
  const categories=()=>[{value:'',label:'전체 기록',icon:'all'},...types().map(kind=>({value:kind,label:labels[kind],icon:kind==='journal'?'daily':kind}))];
  const selectedItems=()=>{const v=view(),tokens=v.query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean),ids=v.folder&&v.folder!=='none'?descendants(v.folder):null;return all().filter(item=>(!v.kind||item.kind===v.kind)&&(!v.favorites||item.fav)&&(!v.folder||(v.folder==='none'?!item.folder:ids.has(item.folder)))&&tokens.every(token=>[item.title,item.body,itemContext(item)].join(' ').toLocaleLowerCase().includes(token))).sort((a,b)=>b.date.localeCompare(a.date))};
  function filterButton(value,label,shape,count,pressed,attr,extra=''){return `<button type="button" ${attr}="${esc(value)}" aria-pressed="${pressed}" class="${extra}">${icon(shape)}<span>${esc(label)}</span><span class="count">${count}</span></button>`}
  function renderNavigation(){
    const v=view(),list=all();
    document.querySelectorAll('[data-space]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.space===state.space));
    document.querySelectorAll('[data-mode]').forEach(b=>{const isRecord=b.dataset.mode==='record';b.innerHTML=icon(isRecord?'book':'folder')+(isRecord?(state.space==='life'?'나의 기록':'업무 기록'):'자료실');b.setAttribute('aria-pressed',b.dataset.mode===state.mode)});
    const favorite=filterButton('','즐겨찾기','star',list.filter(i=>i.fav).length,v.favorites,'data-favorites','favorites-filter');
    let desktop='',mobile='';
    if(state.mode==='record'){
      desktop='<p class="filter-heading">기록 모아보기</p><div class="filter-nav">'+categories().map(c=>filterButton(c.value,c.label,c.icon,list.filter(i=>!c.value||i.kind===c.value).length,v.kind===c.value,'data-kind')).join('')+'<div class="filter-separator"></div>'+favorite+'</div>';
      mobile=categories().map(c=>`<button type="button" data-kind="${c.value}" aria-pressed="${v.kind===c.value}">${c.value?c.label:'전체'}</button>`).join('')+`<button type="button" data-favorites aria-label="즐겨찾는 기록" aria-pressed="${v.favorites}">${icon('star')}</button>`;
    }else{
      const choices=folders.filter(f=>f.space===state.space);
      desktop='<p class="filter-heading">내 책장</p><div class="filter-nav">'+filterButton('','전체 자료','all',list.length,!v.folder,'data-folder')+favorite+'<div class="filter-separator"></div>'+choices.map(f=>filterButton(f.id,f.name,'folder',list.filter(i=>descendants(f.id).has(i.folder)).length,v.folder===f.id,'data-folder',f.parent?'nested':'')).join('')+filterButton('none','폴더 없음','note',list.filter(i=>!i.folder).length,v.folder==='none','data-folder')+'</div>';
      mobile=`<select id="mobile-folder" aria-label="보관 폴더"><option value="">전체 자료</option>${choices.map(f=>`<option value="${esc(f.id)}"${v.folder===f.id?' selected':''}>${esc(folderPath(f.id))}</option>`).join('')}<option value="none"${v.folder==='none'?' selected':''}>폴더 없음</option></select>`+`<button type="button" class="favorites-filter" data-favorites aria-pressed="${v.favorites}">${icon('star')}즐겨찾기</button>`;
    }
    $('#desktop-filters').innerHTML=desktop;$('#mobile-filters').innerHTML=mobile;
    $('#space-count').textContent=state.space==='life'?`${items.filter(i=>i.space==='life'&&i.mode==='record').length}개의 기록, ${items.filter(i=>i.space==='life'&&i.mode==='library').length}개의 자료`:`${items.filter(i=>i.space==='work'&&i.mode==='record').length}개의 기록, ${items.filter(i=>i.space==='work'&&i.mode==='library').length}개의 자료`;
  }
  function row(item){return `<div class="item-row"><button type="button" class="item-open" data-open="${esc(item.id)}" aria-label="${esc(item.title)} 열기"><span class="item-symbol ${item.mode==='library'?'library':item.kind==='journal'?'daily':item.kind}">${icon(item.mode==='library'?'note':item.kind==='journal'?'daily':item.kind)}</span><span class="item-text"><span class="item-meta">${esc(itemContext(item))}</span><strong class="item-title">${esc(item.title)}</strong><span class="item-excerpt">${esc(item.body.split('\n').find(line=>line.trim())||'')}</span></span><span class="item-date">${stamp(item.date)}</span></button><button type="button" class="favorite" data-favorite="${esc(item.id)}" aria-label="${esc(item.title)} 즐겨찾기 ${item.fav?'해제':'추가'}" aria-pressed="${item.fav}">${icon('star')}</button></div>`}
  function render(){
    const v=view(),isRecord=state.mode==='record',list=selectedItems(),filtered=!!(v.query||v.kind||v.folder||v.favorites);
    renderNavigation();$('#eyebrow').textContent=state.space==='life'?'LIFE':'WORK';$('#heading').textContent=isRecord?(state.space==='life'?'나의 기록':'업무 기록'):(v.folder&&v.folder!=='none'?folderPath(v.folder).split(' / ').at(-1):'자료실');
    $('#new-item').innerHTML=`<span class="plus" aria-hidden="true">＋</span>${isRecord?'기록 남기기':'자료 보관'}`;
    $('#search-icon').innerHTML=icon('search');$('#search').placeholder=isRecord?'제목이나 기억나는 내용으로 찾기':'필요한 정보, 문장, 링크 찾기';if($('#search').value!==v.query)$('#search').value=v.query;
    $('#result-count').textContent=`${filtered?'찾은 ':''}${isRecord?'기록':'자료'} ${list.length}개`;
    $('#clear-filters').hidden=!filtered;
    let html='';
    if(!list.length){html=`<div class="empty"><img src="lemon-mark.svg" alt=""><strong>${filtered?'찾는 내용이 아직 없어요':isRecord?'첫 기록을 남겨 볼까요?':'꺼내 볼 정보를 모아 보세요'}</strong><p>${filtered?'검색어나 분류를 바꿔서 다시 찾아보세요.':isRecord?'오늘의 생각을 한 줄만 적어도 좋아요.':'읽고 싶은 글, 기억할 문장부터 가볍게 보관해요.'}</p>${filtered?'<button type="button" class="text-button" data-reset>조건 지우기</button>':''}<button type="button" class="primary" data-create>${isRecord?'기록 남기기':'자료 보관'}</button></div>`}
    else if(!isRecord&&!filtered){const favorites=list.filter(i=>i.fav),recent=list.filter(i=>!i.fav);if(favorites.length)html+=`<h2 class="section-heading">${icon('star')}자주 꺼내 보는 자료 <span>${favorites.length}</span></h2><div class="paper-list">${favorites.map(row).join('')}</div>`;if(recent.length)html+=`<h2 class="section-heading">최근 보관한 자료 <span>${recent.length}</span></h2><div class="paper-list">${recent.map(row).join('')}</div>`}
    else{html=`<div class="paper-list">${list.map(row).join('')}</div>`}
    $('#content').innerHTML=html;
  }
  function notify(message){clearTimeout(notify.timer);$('#toast').textContent=message;$('#toast').hidden=false;notify.timer=setTimeout(()=>$('#toast').hidden=true,2800)}
  function draftKey(){return state.selected==='new'?`new:${state.space}:${state.mode}`:state.selected}
  function captureDraft(){const form=$('#write-form');if(!form||!state.selected||!state.editing)return;drafts.set(draftKey(),Object.fromEntries(new FormData(form)))}
  function closeReader(){captureDraft();if(history.state?.arecmikDesignPanel)history.back();else{state.selected=null;$('#reader').close()}}
  function openReader(id,editing=false){captureDraft();state.selected=id;state.editing=editing||drafts.has(id);if(!$('#reader').open)history.pushState({arecmikDesignPanel:true},'');renderReader();if(!$('#reader').open)$('#reader').showModal();requestAnimationFrame(()=>{if(state.editing)$('#write-form [name=body]')?.focus();else $('#reader-close')?.focus()})}
  const validURL=value=>{try{const url=new URL(value);return /^https?:$/.test(url.protocol)?url.href:''}catch{return ''}};
  function renderReader(){
    const item=items.find(i=>i.id===state.selected),isNew=state.selected==='new',isRecord=(item?.mode||state.mode)==='record';
    if(!isNew&&!item)return;
    const v=view(),draft=drafts.get(draftKey()),data=draft||{title:item?.title||'',body:item?.body||'',kind:item?.kind||(isRecord?v.kind||'':''),folder:item?.folder||(v.folder&&v.folder!=='none'?v.folder:''),url:item?.url||''};
    const context=state.editing?(isRecord?'기록 남기기':'자료 보관'):itemContext(item);
    const top=`<div class="reader-top"><div class="reader-context">${icon(isRecord?'book':'folder')}<span>${esc(context)}</span></div><div class="reader-actions">${!state.editing?`<button type="button" class="favorite" data-favorite="${esc(item.id)}" aria-label="즐겨찾기 ${item.fav?'해제':'추가'}" aria-pressed="${item.fav}">${icon('star')}</button><button type="button" class="small-button" data-edit>수정</button>`:''}<button type="button" class="icon-button" id="reader-close" aria-label="닫기">${icon('close')}</button></div></div>`;
    if(state.editing){
      const options=isRecord?types().map(kind=>`<option value="${kind}"${kind===data.kind?' selected':''}>${esc(labels[kind])}</option>`).join(''):folders.filter(f=>f.space===state.space).map(f=>`<option value="${esc(f.id)}"${f.id===data.folder?' selected':''}>${esc(folderPath(f.id))}</option>`).join('');
      $('#reader-content').innerHTML=top+`<form id="write-form" class="write-form"><h2 id="reader-title" hidden>${isRecord?'기록 남기기':'자료 보관'}</h2><input id="write-title" class="write-title" name="title" aria-label="제목" placeholder="${isRecord?'제목은 나중에 적어도 좋아요':'어떤 자료인가요?'}" value="${esc(data.title)}"><textarea class="write-body" name="body" aria-label="내용" placeholder="${isRecord?'오늘 남겨 두고 싶은 생각을 적어요.':'다시 읽을 내용이나 링크를 모아 두세요.'}">${esc(data.body)}</textarea><details class="optional-fields"><summary>${isRecord?'기록 종류':'보관 폴더'} · ${esc(isRecord?labels[data.kind]||'분류 없음':folderPath(data.folder)||'폴더 없음')}</summary><label>${isRecord?'기록 종류':'보관 폴더'}<select name="${isRecord?'kind':'folder'}"><option value="">${isRecord?'분류 없이 기록':'폴더 없음'}</option>${options}</select></label>${isRecord?'':`<label>출처 링크 · 선택<input type="url" name="url" placeholder="https://" value="${esc(data.url)}"></label>`}</details><p id="form-error" class="form-error" role="alert" hidden></p><div class="write-footer"><span class="draft-note">예시 데이터에만 저장돼요.<br>작성 중 내용은 이 화면을 켜 둔 동안 유지돼요.</span><button type="submit" class="primary">저장</button></div></form>`;
    }else{
      const related=(item.related||[]).map(id=>items.find(i=>i.id===id&&i.space===item.space)).filter(Boolean);
      $('#reader-content').innerHTML=top+`<article class="reader-body"><h2 id="reader-title">${esc(item.title)}</h2><p class="reader-date">${esc(item.date.replaceAll('-','. '))} · ${esc(item.space.toUpperCase())}</p><div class="reader-prose">${esc(item.body)}</div>${validURL(item.url)?`<a class="source-link" href="${esc(validURL(item.url))}" target="_blank" rel="noopener">${icon('link')}출처 열기 ↗</a>`:''}${related.length?`<section class="related"><h3>함께 꺼내 볼 ${related.every(r=>r.mode==='library')?'자료':'기록과 자료'}</h3>${related.map(r=>`<button type="button" data-open="${esc(r.id)}">${icon(r.mode==='library'?'folder':'book')}${esc(r.title)}<span aria-hidden="true">↗</span></button>`).join('')}</section>`:''}</article>`;
    }
  }
  history.replaceState({arecmikDesignRoot:true},'');
  window.addEventListener('popstate',()=>{captureDraft();state.selected=null;state.editing=false;if($('#reader').open)$('#reader').close();render()});
  $('#reader').addEventListener('cancel',event=>{event.preventDefault();closeReader()});
  $('#reader').addEventListener('click',event=>{if(event.target!==$('#reader'))return;const r=$('#reader').getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)closeReader()});
  document.addEventListener('click',event=>{
    const button=event.target.closest('button');if(!button)return;
    if(button.dataset.space){state.space=button.dataset.space;render();return}
    if(button.dataset.mode){state.mode=button.dataset.mode;render();return}
    if(button.hasAttribute('data-kind')){view().kind=button.dataset.kind;render();return}
    if(button.hasAttribute('data-folder')){view().folder=button.dataset.folder;render();return}
    if(button.hasAttribute('data-favorites')){view().favorites=!view().favorites;render();return}
    if(button.id==='clear-filters'||button.hasAttribute('data-reset')){Object.assign(view(),bucket());render();$('#search').focus();return}
    if(button.dataset.favorite){const item=items.find(i=>i.id===button.dataset.favorite);if(!item)return;item.fav=!item.fav;render();if($('#reader').open&&!state.editing)renderReader();notify(item.fav?'즐겨찾기에 모았어요':'즐겨찾기에서 뺐어요');return}
    if(button.dataset.open){openReader(button.dataset.open);return}
    if(button.id==='reader-close'){closeReader();return}
    if(button.hasAttribute('data-edit')){state.editing=true;renderReader();$('#write-form [name=body]').focus();return}
    if(button.id==='new-item'||button.hasAttribute('data-create')){openReader('new',true)}
  });
  $('#search').addEventListener('input',event=>{view().query=event.target.value;render()});
  document.addEventListener('change',event=>{if(event.target.id==='mobile-folder'){view().folder=event.target.value;render()}if(event.target.closest('#write-form')){captureDraft();const form=$('#write-form'),isRecord=!!form.elements.namedItem('kind'),value=form.elements.kind?.value||form.elements.folder?.value||'';form.querySelector('summary').textContent=(isRecord?'기록 종류':'보관 폴더')+' · '+(isRecord?labels[value]||'분류 없음':folderPath(value)||'폴더 없음')}});
  document.addEventListener('input',event=>{if(event.target.closest('#write-form')){captureDraft();$('#form-error').hidden=true}});
  document.addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'&&!$('#reader').open){event.preventDefault();$('#search').focus()}});
  $('#reader').addEventListener('submit',event=>{
    if(event.target.id!=='write-form')return;event.preventDefault();const form=event.target,data=Object.fromEntries(new FormData(form)),body=data.body.trim(),url=validURL(data.url),existing=items.find(item=>item.id===state.selected),mode=existing?.mode||state.mode;
    if(!body&&!url){$('#form-error').hidden=false;$('#form-error').textContent=mode==='record'?'남기고 싶은 내용을 한 줄 적어 주세요.':'내용이나 출처 링크를 하나 넣어 주세요.';form.elements.body.focus();return}
    const title=data.title.trim()||body.split('\n')[0].slice(0,80)||(url?new URL(url).hostname:'제목 없는 자료');
    const value={...existing,id:existing?.id||`example-${nextId++}`,space:state.space,mode:existing?.mode||state.mode,title,body,date:existing?.date||today,fav:existing?.fav||false,...(mode==='record'?{kind:labels[data.kind]?data.kind:''}:{folder:folders.some(f=>f.space===state.space&&f.id===data.folder)?data.folder:'',url})};
    if(existing)Object.assign(existing,value);else items.unshift(value);drafts.delete(draftKey());if(mode===state.mode)Object.assign(view(),bucket());state.editing=false;$('#reader').close();state.selected=null;if(history.state?.arecmikDesignPanel)history.back();render();notify('예시 데이터에 저장했어요 · 새로고침하면 초기화돼요');
  });
  render();
})();
