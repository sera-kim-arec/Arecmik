// 앱 설치용 최소 서비스워커: 저장(캐시)하지 않고 항상 최신 파일을 받아요.
self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));
self.addEventListener('fetch',()=>{});
