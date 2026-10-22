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
 const isMobile=/Android|iPhone|iPad/.test(navigator.userAgent),supported='Notification'in window&&!isMobile;
 const key=()=>`arecmik:reminders:${uid()||''}`;
 const load=()=>{try{return JSON.parse(storage.getItem(key())||'{}')}catch(_){return {}}};
 const save=value=>{try{storage.setItem(key(),JSON.stringify(value));return true}catch(_){notify('알림 설정을 저장하지 못했어요. 기기 저장 공간을 확인해 주세요.');return false}};
 const signature=(t,at)=>`${t.id}|${t.date}|${t.time||''}|${at}`;
 function closeActive(){for(const {n} of active.values())n.close();active.clear();}
 function status(){const out=document.getElementById('reminder-status');if(!out)return;const state=load();out.textContent=!supported?'이 브라우저에서는 PC 알림을 지원하지 않아요. PC의 Chrome·Edge에서 사용하거나 안드로이드 앱을 이용해 주세요.':Notification.permission==='denied'?'브라우저 알림이 차단되어 있어요. 주소창의 사이트 설정에서 알림을 허용해 주세요.':state.enabled&&Notification.permission==='granted'?'이 PC에서 알림을 받고 있어요.': '이 PC의 알림은 꺼져 있어요.';}
 function settings(){
  if(preview){openSheet('<h3>일정 알림 🍋</h3><p class="archive-help">실제 앱의 설정에서 알림을 켤 수 있어요. 미리보기에서는 알림 권한을 요청하거나 예약하지 않아요.</p><button class="soft" data-sx="0">닫기</button>');return;}
  if(nativeApp){if(nativeApp.remindersSupported())nativeApp.remindersSettings();else openSheet('<h3>일정 알림 🍋</h3><p class="archive-help">알림 기능은 안드로이드 앱 v1.3.0부터 사용할 수 있어요. 앱을 업데이트한 뒤 이 메뉴를 다시 열어 주세요.</p><div class="es-b"><button class="soft" data-sx="0">닫기</button><button class="ink" data-apk-download>APK 설치 · 업데이트</button></div>');return;}
  const state=load();openSheet(`<h3>일정 알림 🍋</h3><p id="reminder-status" role="status" class="archive-help"></p><label class="reminder-setting">기본 알림<select id="reminder-lead">${[['15','15분 전'],['30','30분 전'],['60','1시간 전'],['0','시작할 때'],['morning','당일 오전 9시']].map(([v,l])=>`<option value="${v}"${(state.lead||'15')===v?' selected':''}>${l}</option>`).join('')}</select></label><p class="archive-help">시간 없는 일정은 당일 오전 9시, 여러 날 일정은 시작일에 한 번 알려줘요. 일정 상세에서 개별 알림을 바꾸거나 끌 수 있어요.</p><p class="archive-help">PC 알림은 이 앱의 탭을 열어둔 동안 작동해요. 창을 최소화해도 되지만, PC 절전이나 브라우저의 탭 절전 중에는 늦어지거나 놓칠 수 있어요. 알림을 누르면 해당 일정이 열려요.</p><p class="archive-help">휴대폰에서는 안드로이드 앱을 업데이트하고 알림을 켜면 앱을 닫아도 받을 수 있어요.</p><div class="reminder-setting-actions"><button class="soft" data-reminder-off>이 PC 알림 끄기</button><button class="ink" data-reminder-on${supported?'':' disabled'}>이 PC 알림 켜기</button><button class="soft" data-reminder-test${supported?'':' disabled'}>테스트 알림</button></div><div class="es-b"><button class="soft" data-sx="0">닫기</button></div>`);status();
 }
 function show(task,at,test=false){
  const text=test?'알림이 이렇게 도착해요 🍋':`${task.space==='life'?'LIFE':'WORK'} · ${task.date} ${task.time||'종일'}`;
  const n=new Notification(test?'Arecmik 알림 테스트':task.title||'일정',{body:text,icon:new URL('icon-192.png',location.href).href,tag:`arecmik:${uid()}:${test?'test':task.id}`});
  const id=test?'test':task.id;active.get(id)?.n.close();active.set(id,{n,key:signature(task,at)});
  const owner=uid();n.onclick=()=>{window.focus();n.close();if(!test&&uid()===owner)openTask({uid:owner,id:task.id});};
 }
 async function tick(){
  if(preview)return;
  if(busy)return;busy=true;
  try{
   const user=uid();if(account!==user){closeActive();account=user;}
   if(!user||!ready())return;
   const tasks=data();if(nativeApp){nativeApp.syncReminders(user,tasks);return;}
   const state=load();if(!supported||!state.enabled||Notification.permission!=='granted')return;
   for(const [id,{n,key}]of active){if(id==='test')continue;const t=tasks.find(t=>t.id===id),at=t&&reminderAt(t,state.lead||'15');if(!at||key!==signature(t,at)){n.close();active.delete(id);}}
   const now=Date.now(),run=()=>{
    if(uid()!==user||!ready())return;
    const state=load(),delivered=state.delivered||{},keep={};
    if(!state.enabled||Notification.permission!=='granted')return;
    for(const t of tasks){const at=reminderAt(t,state.lead||'15'),sig=signature(t,at);if(delivered[sig])keep[sig]=true;
     if(!at||at<started||at>now||now-at>15*60000||delivered[sig])continue;
     // Persist the claim before displaying; another open tab sees the same claim.
     keep[sig]=true;if(!save({...state,delivered:{...delivered,...keep}}))continue;
     try{show(t,at);lastError=false;}catch(_){delete keep[sig];delete delivered[sig];if(!lastError){notify('PC 알림을 표시하지 못했어요. 브라우저와 운영체제의 알림 설정을 확인해 주세요.');lastError=true;}}
    }
    save({...state,delivered:keep});
   };
   if(navigator.locks)await navigator.locks.request(`arecmik-reminder:${user}`,{ifAvailable:true},lock=>{if(lock)run()});else run();
  }finally{busy=false;}
 }
 document.addEventListener('click',async event=>{
  if(event.target.closest?.('[data-reminders-open]')){document.getElementById('menu')?.classList.remove('on');settings();return;}
  const button=event.target.closest?.('[data-reminder-on],[data-reminder-off],[data-reminder-test]');if(!button)return;
  if(button.hasAttribute('data-reminder-off')){save({...load(),enabled:false});closeActive();status();return;}
  const owner=uid();button.disabled=true;try{
   if(!supported)return;
   const permission=Notification.permission==='default'?await Notification.requestPermission():Notification.permission;
   if(uid()!==owner)return;
   if(permission!=='granted'){status();return;}
   if(button.hasAttribute('data-reminder-test'))show({},Date.now(),true);
   else {if(save({...load(),enabled:true,lead:document.getElementById('reminder-lead')?.value||'15'})){status();notify('이 PC의 일정 알림을 켰어요.');tick();}}
  }catch(_){notify('알림을 켜지 못했어요. 브라우저의 알림 설정을 확인해 주세요.');}finally{button.disabled=false;}
 });
 document.addEventListener('change',event=>{if(event.target.id==='reminder-lead'){save({...load(),lead:event.target.value});tick();}});
 window.addEventListener('storage',event=>{if(event.key===key()){if(!load().enabled)closeActive();status();}});
 window.addEventListener('focus',()=>tick());document.addEventListener('visibilitychange',()=>{if(!document.hidden)tick()});
 // Native snapshots are sent on data changes, not on every browser timer tick.
 if(!nativeApp)setInterval(tick,15000);
 tick();return {sync:tick,settings};
}
