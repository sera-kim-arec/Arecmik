// The Android shell offers an origin-bound MessagePort, never a JavaScript interface.
export function setupAndroidApp({auth,GoogleAuthProvider,signInWithCredential,signOut,loginButton,notify,onBack}){
 if(!navigator.userAgent.includes('ArecmikAndroid/1'))return null;
 let port=null,busy=false,queue=Promise.resolve();
 const send=(type,extra={})=>{if(!port){notify('앱을 연결하는 중이에요. 잠시 후 다시 눌러 주세요.');return false;}port.postMessage(JSON.stringify({type,...extra}));return true;};
 window.addEventListener('message',event=>{
  if(event.source!==null||event.data!=='arecmik-native-v1'||event.ports.length!==1||port)return;
  port=event.ports[0];
  port.onmessage=event=>{queue=queue.then(async()=>{let message;try{message=JSON.parse(event.data);}catch(_){return;}
   if(message.type==='account'){
    await auth.authStateReady();
    if(auth.currentUser&&auth.currentUser.uid!==message.uid)await signOut(auth);
   }
   if(message.type==='credential'&&!busy){busy=true;loginButton.disabled=true;
    try{
     const credential=GoogleAuthProvider.credential(message.idToken||null,message.accessToken||null);
     const result=await signInWithCredential(auth,credential);
     if(result.user.uid!==message.uid){await signOut(auth);throw new Error('계정이 달라요. 다시 연결해 주세요.');}
     send('auth-ok',{uid:result.user.uid});
    }catch(_){notify('앱에 로그인하지 못했어요. Google로 로그인을 눌러 다시 연결해 주세요.');}
    finally{busy=false;loginButton.disabled=false;message=null;}
   }
   if(message?.type==='signed-out')await signOut(auth);
   if(message?.type==='backup-result')notify(message.ok?'백업 파일을 저장했어요.':'백업 파일을 저장하지 않았어요. 다시 시도할 수 있어요.');
   if(message?.type==='back'&&!onBack?.())send('back-unhandled');
  }).catch(()=>notify('앱 연결을 확인하지 못했어요. 다시 로그인해 주세요.'));};
  port.start();send('ready');
 });
 loginButton.onclick=()=>send('login');
 return {settings:()=>send('settings'),logout:()=>{if(confirm('앱과 위젯의 계정 연결을 해제할까요? 이 휴대폰의 전송 대기 중인 완료 변경도 지워집니다. 원본 기록은 유지돼요.'))send('logout');},backup:(name,content)=>send('backup',{name,content})};
}
