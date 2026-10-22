// The Android shell offers an origin-bound MessagePort, never a JavaScript interface.
export function setupAndroidApp({auth,GoogleAuthProvider,signInWithCredential,signOut,loginButton,notify,onBack,onReady,onOpenTask,onReminderNotices}){
 if(!navigator.userAgent.includes('ArecmikAndroid/1'))return null;
 let port=null,busy=false,supportsUpdate=false,supportsReminders=false,supportsPopups=false,nativeUid='',pendingOpenTask=null,queue=Promise.resolve();
 const send=(type,extra={})=>{if(!port){notify('앱을 연결하는 중이에요. 잠시 후 다시 눌러 주세요.');return false;}port.postMessage(JSON.stringify({type,...extra}));return true;};
 window.addEventListener('message',event=>{
  if(event.source!==null||event.data!=='arecmik-native-v1'||event.ports.length!==1||port)return;
  port=event.ports[0];
  port.onmessage=event=>{queue=queue.then(async()=>{let message;try{message=JSON.parse(event.data);}catch(_){return;}
   if(message.type==='account'){
    nativeUid=message.uid||'';
    supportsUpdate=Array.isArray(message.capabilities)&&message.capabilities.includes('update');
    supportsReminders=Array.isArray(message.capabilities)&&message.capabilities.includes('reminders');
    supportsPopups=Array.isArray(message.capabilities)&&message.capabilities.includes('reminder-popups');
    await auth.authStateReady();
    if(auth.currentUser&&auth.currentUser.uid!==message.uid)await signOut(auth);
    onReady?.();
   }
   if(message.type==='credential'&&!busy){busy=true;loginButton.disabled=true;
    try{
     const credential=GoogleAuthProvider.credential(message.idToken||null,message.accessToken||null);
     const result=await signInWithCredential(auth,credential);
     if(result.user.uid!==message.uid){await signOut(auth);throw new Error('계정이 달라요. 다시 연결해 주세요.');}
     send('auth-ok',{uid:result.user.uid});
     if(pendingOpenTask?.uid===result.user.uid){onOpenTask?.(pendingOpenTask);pendingOpenTask=null;}
    }catch(_){notify('앱에 로그인하지 못했어요. Google로 로그인을 눌러 다시 연결해 주세요.');}
    finally{busy=false;loginButton.disabled=false;message=null;}
   }
   if(message?.type==='signed-out'){pendingOpenTask=null;nativeUid='';await signOut(auth);}
   if(message?.type==='backup-result')notify(message.ok?'백업 파일을 저장했어요.':'백업 파일을 저장하지 않았어요. 다시 시도할 수 있어요.');
   if(message?.type==='back'&&!onBack?.())send('back-unhandled');
   if(message?.type==='open-task'){if(auth.currentUser?.uid===message.uid)onOpenTask?.(message);else if(nativeUid&&nativeUid===message.uid)pendingOpenTask=message;}
   if(message?.type==='reminder-notices'&&auth.currentUser?.uid===message.uid)onReminderNotices?.(message);
  }).catch(()=>notify('앱 연결을 확인하지 못했어요. 다시 로그인해 주세요.'));};
  port.start();send('ready');
 });
 loginButton.onclick=()=>send('login');
 return {reminderNotices:()=>supportsPopups&&send('reminders-notices'),dismissReminder:id=>supportsPopups&&send('reminders-dismiss',{id}),remindersSupported:()=>supportsReminders,remindersSettings:()=>supportsReminders&&send('reminders-settings'),syncReminders:(uid,tasks)=>{if(!supportsReminders)return false;return send('reminders-sync',{uid,tasks:tasks.map(t=>Object.fromEntries(['id','date','time','title','kind','space','reminder','done'].filter(k=>t[k]!==undefined).map(k=>[k,t[k]])))});},settings:()=>send('settings'),update:()=>supportsUpdate?send('update'):false,logout:()=>{if(confirm('앱과 위젯의 계정 연결을 해제할까요? 이 휴대폰의 전송 대기 중인 완료 변경도 지워집니다. 원본 기록은 유지돼요.'))send('logout');},backup:(name,content)=>send('backup',{name,content})};
}
