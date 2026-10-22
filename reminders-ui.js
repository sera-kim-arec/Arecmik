// Local browser reminders: the app tab must stay open. Android uses native alarms.
export function reminderAt(task,lead='15'){
 if(task.done||!/^\d{4}-\d{2}-\d{2}$/.test(task.date||''))return 0;
 let value=task.reminder||'default';
 if(value==='off')return 0;
 if(value==='default'){if(task.kind!=='event'&&!task.time)return 0;value=lead;}
 if(!['0','15','30','60','morning'].includes(value))return 0;
 const [y,m,d]=task.date.split('-').map(Number),time=!task.time||value==='morning'?'09:00':task.time;
 if(!/^([01]\d|2[0-3]):[0-5]\d$/.test(time))return 0;
 const [h,min]=time.split(':').map(Number),date=new Date(y,m-1,d,h,min);
 if(date.getFullYear()!==y||date.getMonth()!==m-1||date.getDate()!==d)return 0;
 return +date-(!task.time||value==='morning'?0:Number(value)*60000);
}
export function installReminders({nativeApp,data,uid,ready,openSheet,openTask,notify,storage=localStorage,preview=false}){
 const started=Date.now();let busy=false,lastError=false,account='';const active=new Map();
 const baseTitle=document.title;let panel=null,testNotice=false,nativeEnabled=false,nativeLead='15';
 const isMobile=/Android|iPhone|iPad/.test(navigator.userAgent),supported='Notification'in window&&!isMobile;
 const key=()=>`arecmik:reminders:${uid()||''}`;
 const load=()=>{try{return JSON.parse(storage.getItem(key())||'{}')}catch(_){return {}}};
 const save=value=>{try{storage.setItem(key(),JSON.stringify(value));return true}catch(_){notify('알림 설정을 저장하지 못했어요. 기기 저장 공간을 확인해 주세요.');return false}};
 const signature=(t,at)=>`${t.id}|${t.date}|${t.time||''}|${at}`;
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function remaining(t){if(!t.time){const now=new Date(),today=[now.getFullYear(),String(now.getMonth()+1).padStart(2,'0'),String(now.getDate()).padStart(2,'0')].join('-');return t.date===today?'오늘의 일정':`${t.date.slice(5).replace('-','/')} 일정`;}const minutes=Math.ceil((+new Date(`${t.date}T${t.time}`)-Date.now())/60000);return minutes>0?`${minutes}분 뒤 시작`:minutes>=-1?'지금 시작해요':'시작 시간이 지났어요';}
 function renderPanel(){
  if(preview)return;
  const state=load(),lead=nativeApp?nativeLead:state.lead||'15',pending=state.pending||{},tasks=data(),visible=[];
  if(uid()&&(nativeApp?nativeEnabled:state.enabled))for(const [key,entry]of Object.entries(pending)){
   const task=tasks.find(t=>t.id===entry.id);if(!task||task.done||signature(task,reminderAt(task,lead))!==key)continue;
   visible.push({key,task});
  }
  if(!panel){panel=document.createElement('aside');panel.id='reminder-popup';panel.className='reminder-popup';panel.setAttribute('aria-label','일정 알림');panel.setAttribute('role','region');panel.hidden=true;document.body.append(panel);}
  const count=visible.length+(testNotice?1:0);panel.hidden=!count;document.title=count?`🍋 알림 ${count} · ${baseTitle}`:baseTitle;
  if(!count){panel.replaceChildren();return;}
  const rows=visible.map(({key,task})=>`<article class="reminder-popup-item"><p class="reminder-popup-when">${esc(remaining(task))}</p><h3>${esc(task.title||'일정')}</h3><p class="reminder-popup-context">${esc(task.time||'종일')} · ${task.space==='life'?'LIFE':'WORK'} · ${esc(task.date)}</p><div class="reminder-popup-actions"><button type="button" class="ink" data-reminder-open="${esc(key)}">일정 열기</button><button type="button" class="soft" data-reminder-dismiss="${esc(key)}">확인했어요</button></div></article>`).join('');
  const sample=testNotice?'<article class="reminder-popup-item"><p class="reminder-popup-when">15분 뒤 시작</p><h3>잠깐, 곧 시작할 일정이 있어요!</h3><p class="reminder-popup-context">테스트 알림이에요 · 실제 일정은 만들지 않아요.</p><div class="reminder-popup-actions"><button type="button" class="ink" data-reminder-sample-close>확인했어요 🍋</button></div></article>':'';
  const html=`<header class="reminder-popup-head"><img src="lemon-mark.svg" alt="" width="44" height="44"><div><strong>레몬이 알려줘요</strong><span role="status" aria-live="polite">일정 알림 ${count}개</span></div><button type="button" class="link" data-reminder-dismiss-all>모두 확인</button></header><div class="reminder-popup-list">${sample}${rows}</div>`;
  if(panel.innerHTML!==html){const focused=panel.contains(document.activeElement)?document.activeElement:null,attribute=focused&&[...focused.attributes].find(a=>a.name.startsWith('data-reminder-'));panel.innerHTML=html;if(attribute){const target=[...panel.querySelectorAll('button')].find(b=>b.getAttribute(attribute.name)===attribute.value);target?.focus({preventScroll:true});}}
 }
 function closeActive(){for(const {n} of active.values())n.close();active.clear();testNotice=false;if(panel){panel.hidden=true;panel.replaceChildren();}document.title=baseTitle;}
 function dismiss(key){const state=load(),pending={...state.pending};const entry=pending[key];delete pending[key];if(!save({...state,pending}))return;active.get(entry?.id)?.n.close();active.delete(entry?.id);if(nativeApp&&entry)nativeApp.dismissReminder?.(entry.id);renderPanel();}
 function receiveNative(message){
  if(preview||message.uid!==uid()||!ready())return;
  nativeEnabled=!!message.enabled;nativeLead=message.lead||'15';const state=load(),pending={...(nativeEnabled?state.pending:{})},delivered={...state.delivered};
  for(const notice of nativeEnabled?message.notices||[]:[]){if(delivered[notice.key])continue;const task=data().find(t=>t.id===notice.id);if(!task)continue;const at=reminderAt(task,nativeLead);if(signature(task,at)!==notice.key)continue;pending[notice.key]={id:task.id,at};delivered[notice.key]=true;}
  save({...state,pending,delivered});renderPanel();
 }
 function status(){const out=document.getElementById('reminder-status');if(!out)return;const state=load();out.textContent=!supported?'이 브라우저에서는 PC 알림을 지원하지 않아요. PC의 Chrome·Edge에서 사용하거나 안드로이드 앱을 이용해 주세요.':Notification.permission==='denied'?'브라우저 알림이 차단되어 있어요. 주소창의 사이트 설정에서 알림을 허용해 주세요.':state.enabled&&Notification.permission==='granted'?'이 PC에서 알림을 받고 있어요.': '이 PC의 알림은 꺼져 있어요.';}
 function settings(){
  if(preview){openSheet('<h3>일정 알림 🍋</h3><p class="archive-help">실제 앱의 설정에서 알림을 켤 수 있어요. 미리보기에서는 알림 권한을 요청하거나 예약하지 않아요.</p><button class="soft" data-sx="0">닫기</button>');return;}
  if(nativeApp){if(nativeApp.remindersSupported())nativeApp.remindersSettings();else openSheet('<h3>일정 알림 🍋</h3><p class="archive-help">알림 기능은 안드로이드 앱 v1.3.0부터 사용할 수 있어요. 앱을 업데이트한 뒤 이 메뉴를 다시 열어 주세요.</p><div class="es-b"><button class="soft" data-sx="0">닫기</button><button class="ink" data-apk-download>APK 설치 · 업데이트</button></div>');return;}
  const state=load();openSheet(`<h3>일정 알림 🍋</h3><p id="reminder-status" role="status" class="archive-help"></p><label class="reminder-setting">기본 알림<select id="reminder-lead">${[['15','15분 전'],['30','30분 전'],['60','1시간 전'],['0','시작할 때'],['morning','당일 오전 9시']].map(([v,l])=>`<option value="${v}"${(state.lead||'15')===v?' selected':''}>${l}</option>`).join('')}</select></label><p class="archive-help">시간 없는 일정은 당일 오전 9시, 여러 날 일정은 시작일에 한 번 알려줘요. 일정 상세에서 개별 알림을 바꾸거나 끌 수 있어요.</p><p class="archive-help">PC 알림은 이 앱의 탭을 열어둔 동안 작동해요. 창을 최소화해도 되지만, PC 절전이나 브라우저의 탭 절전 중에는 늦어지거나 놓칠 수 있어요. 알림을 누르면 해당 일정이 열려요.</p><p class="archive-help">시스템 알림이 사라져도 앱 안의 레몬 팝업은 확인할 때까지 남아요. 다른 앱 위의 시스템 팝업 표시·유지 시간은 브라우저와 기기 설정에 따라 달라요.</p><p class="archive-help">휴대폰에서는 안드로이드 앱을 업데이트하고 알림을 켜면 앱을 닫아도 받을 수 있어요.</p><div class="reminder-setting-actions"><button class="soft" data-reminder-off>이 PC 알림 끄기</button><button class="ink" data-reminder-on${supported?'':' disabled'}>이 PC 알림 켜기</button><button class="soft" data-reminder-test${supported?'':' disabled'}>테스트 알림</button></div><div class="es-b"><button class="soft" data-sx="0">닫기</button></div>`);status();
 }
 function show(task,at,test=false){
  const text=test?'레몬 팝업과 함께 알려드려요 🍋':`${remaining(task)} · ${task.time||'종일'}\n${task.space==='life'?'LIFE':'WORK'} · ${task.date}`;
  const n=new Notification(test?'Arecmik 알림 테스트 🍋':task.title||'일정',{body:text,icon:new URL('icon-192.png',location.href).href,tag:`arecmik:${uid()}:${test?'test':task.id}`,requireInteraction:true});
  const id=test?'test':task.id;active.get(id)?.n.close();active.set(id,{n,key:signature(task,at)});
  const owner=uid();n.onclick=()=>{window.focus();n.close();if(!test&&uid()===owner){dismiss(signature(task,at));openTask({uid:owner,id:task.id});}};
 }
 async function tick(syncNative=false){
  if(preview)return;
  if(busy)return;busy=true;
  try{
   const user=uid();if(account!==user){closeActive();account=user;}
   if(!user||!ready())return;
   const tasks=data();if(nativeApp){if(syncNative)nativeApp.syncReminders(user,tasks);nativeApp.reminderNotices?.();renderPanel();return;}
   const state=load();renderPanel();if(!supported||!state.enabled||Notification.permission!=='granted')return;
   for(const [id,{n,key}]of active){if(id==='test')continue;const t=tasks.find(t=>t.id===id),at=t&&reminderAt(t,state.lead||'15');if(!at||key!==signature(t,at)||!state.pending?.[key]){n.close();active.delete(id);}}
   const now=Date.now(),run=()=>{
    if(uid()!==user||!ready())return;
    const state=load(),delivered=state.delivered||{},keep={},pending={...state.pending};
    if(!state.enabled||Notification.permission!=='granted')return;
    for(const t of tasks){const at=reminderAt(t,state.lead||'15'),sig=signature(t,at);if(delivered[sig])keep[sig]=true;
     if(!at||at<started||at>now||now-at>15*60000||delivered[sig])continue;
     // Persist the claim before displaying; another open tab sees the same claim.
     keep[sig]=true;pending[sig]={id:t.id,at};if(!save({...state,pending,delivered:{...delivered,...keep}}))continue;
     try{show(t,at);lastError=false;}catch(_){if(!lastError){notify('시스템 알림을 표시하지 못해 레몬 팝업에 남겼어요.');lastError=true;}}
    }
    save({...state,pending,delivered:keep});renderPanel();
   };
   if(navigator.locks)await navigator.locks.request(`arecmik-reminder:${user}`,{ifAvailable:true},lock=>{if(lock)run()});else run();
  }finally{busy=false;}
 }
 document.addEventListener('click',async event=>{
  const item=event.target.closest?.('[data-reminder-open],[data-reminder-dismiss]');if(item){const key=item.dataset.reminderOpen||item.dataset.reminderDismiss,entry=load().pending?.[key];if(!entry)return;dismiss(key);if(item.hasAttribute('data-reminder-open'))openTask({uid:uid(),id:entry.id});return;}
  if(event.target.closest?.('[data-reminder-sample-close]')){testNotice=false;active.get('test')?.n.close();active.delete('test');renderPanel();return;}
  if(event.target.closest?.('[data-reminder-dismiss-all]')){for(const key of Object.keys(load().pending||{}))dismiss(key);testNotice=false;active.get('test')?.n.close();active.delete('test');renderPanel();return;}
  if(event.target.closest?.('[data-reminders-open]')){document.getElementById('menu')?.classList.remove('on');settings();return;}
  const button=event.target.closest?.('[data-reminder-on],[data-reminder-off],[data-reminder-test]');if(!button)return;
  if(button.hasAttribute('data-reminder-off')){save({...load(),enabled:false,pending:{}});closeActive();status();return;}
  const owner=uid();button.disabled=true;try{
   if(!supported)return;
   const permission=Notification.permission==='default'?await Notification.requestPermission():Notification.permission;
   if(uid()!==owner)return;
   if(permission!=='granted'){status();return;}
   if(button.hasAttribute('data-reminder-test')){testNotice=true;document.querySelector('#sheet [data-sx="0"]')?.click();renderPanel();show({},Date.now(),true);}
   else {if(save({...load(),enabled:true,lead:document.getElementById('reminder-lead')?.value||'15'})){status();notify('이 PC의 일정 알림을 켰어요.');tick();}}
  }catch(_){notify('알림을 켜지 못했어요. 브라우저의 알림 설정을 확인해 주세요.');}finally{button.disabled=false;}
 });
 document.addEventListener('change',event=>{if(event.target.id==='reminder-lead'){save({...load(),lead:event.target.value});tick();}});
 window.addEventListener('storage',event=>{if(event.key===key()){const state=load();if(!nativeApp&&!state.enabled)closeActive();for(const [id,{n,key}]of active)if(id!=='test'&&!state.pending?.[key]){n.close();active.delete(id);}status();renderPanel();}});
 window.addEventListener('focus',()=>tick());document.addEventListener('visibilitychange',()=>{if(!document.hidden)tick()});
 // Native snapshots are sent on data changes, not on every browser timer tick.
 setInterval(()=>tick(),15000);
 tick(true);return {sync:()=>tick(true),settings,receiveNative};
}
