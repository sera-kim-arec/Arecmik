import {initializeApp} from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js';
import {getAuth,GoogleAuthProvider,onAuthStateChanged,signInWithPopup} from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js';
import {firebaseConfig} from './widget-firebase-config.js';
import {readRequest,sealAccount} from './widget-pairing.js';
const status=document.querySelector('#connect-status'),login=document.querySelector('#widget-login'),authorize=document.querySelector('#widget-authorize'),back=document.querySelector('#return-widget');
let request=null,user=null;
try{request=readRequest(location.hash);history.replaceState(null,'',location.pathname);}catch(error){status.textContent=error.message;}
if(request){
 const auth=getAuth(initializeApp(firebaseConfig));
 onAuthStateChanged(auth,value=>{user=value;login.hidden=!!value;authorize.hidden=!value;status.textContent=value?`${value.displayName||value.email||'내 계정'}의 일정·할 일을 연결합니다. 위젯의 완료 체크도 원본에 반영돼요.`:'현재 Arecmik에서 쓰는 Google 계정으로 로그인해 주세요.';});
 login.addEventListener('click',async()=>{login.disabled=true;try{await signInWithPopup(auth,new GoogleAuthProvider());}catch(_){status.textContent='로그인하지 못했어요. Chrome 등 기본 브라우저에서 다시 열어 주세요.';}finally{login.disabled=false;}});
 authorize.addEventListener('click',async()=>{if(!user||authorize.disabled)return;authorize.disabled=true;status.textContent='이 휴대폰의 위젯 앱으로 전달할 연결 정보를 암호화하고 있어요…';try{
   await user.getIdToken();if(!user.refreshToken)throw new Error('계정 연결 정보를 읽지 못했어요. 다시 로그인해 주세요.');
   back.href=await sealAccount(request,{projectId:firebaseConfig.projectId,uid:user.uid,refreshToken:user.refreshToken,name:user.displayName||user.email||'내 계정'});
   back.hidden=false;authorize.hidden=true;status.textContent='아래 버튼을 눌러 위젯 앱으로 돌아가 연결을 마쳐 주세요.';
 }catch(error){status.textContent=error.message||'연결 정보를 만들지 못했어요. 위젯 앱에서 다시 시작해 주세요.';authorize.disabled=false;}});
}
