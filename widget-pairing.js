const encoder=new TextEncoder();
export function b64(bytes){let text='';for(const byte of new Uint8Array(bytes))text+=String.fromCharCode(byte);return btoa(text).replaceAll('+','-').replaceAll('/','_').replace(/=+$/,'');}
export function unb64(text){if(typeof text!=='string'||!/^[A-Za-z0-9_-]+$/.test(text))throw new Error('연결 주소 형식이 올바르지 않아요.');const value=atob(text.replaceAll('-','+').replaceAll('_','/'));return Uint8Array.from(value,ch=>ch.charCodeAt(0));}
export function readRequest(fragment,now=Date.now()){
 if(!fragment.startsWith('#pair=')||fragment.length>1500)throw new Error('위젯 앱에서 ‘브라우저에서 계정 연결’을 눌러 시작해 주세요.');
 const request=JSON.parse(new TextDecoder().decode(unb64(fragment.slice(6))));
 if(request.v!==1||typeof request.nonce!=='string'||!/^[A-Za-z0-9_-]{32}$/.test(request.nonce)||!Number.isSafeInteger(request.expires)||request.expires<=now||request.expires>now+630000||typeof request.publicKey!=='string'||unb64(request.publicKey).length!==91)throw new Error('연결 주소가 만료되었거나 올바르지 않아요. 위젯 앱에서 다시 시작해 주세요.');
 return request;
}
export async function sealAccount(request,account){
 if(request.expires<=Date.now())throw new Error('연결 시간이 지났어요. 위젯 앱에서 다시 시작해 주세요.');
 const recipient=await crypto.subtle.importKey('spki',unb64(request.publicKey),{name:'ECDH',namedCurve:'P-256'},false,[]);
 const pair=await crypto.subtle.generateKey({name:'ECDH',namedCurve:'P-256'},true,['deriveBits']);
 const shared=new Uint8Array(await crypto.subtle.deriveBits({name:'ECDH',public:recipient},pair.privateKey,256));
 const aad=encoder.encode('arecmik-widget:v1:'+request.nonce),material=new Uint8Array(shared.length+aad.length);material.set(shared);material.set(aad,shared.length);
 const key=await crypto.subtle.importKey('raw',await crypto.subtle.digest('SHA-256',material),'AES-GCM',false,['encrypt']);
 const iv=crypto.getRandomValues(new Uint8Array(12));const data=await crypto.subtle.encrypt({name:'AES-GCM',iv,additionalData:aad},key,encoder.encode(JSON.stringify(account)));
 const envelope={v:1,nonce:request.nonce,publicKey:b64(await crypto.subtle.exportKey('spki',pair.publicKey)),iv:b64(iv),data:b64(data)};
 return 'arecmik-widget://connect#data='+b64(encoder.encode(JSON.stringify(envelope)));
}
