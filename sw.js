// 앱 설치용 최소 서비스워커: 저장(캐시)하지 않고 항상 최신 파일을 받아요.
// 알림을 누르면 열려 있는 Arecmik 창으로 이동해 그 항목을 열어요.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => {});
self.addEventListener('notificationclick', e => {
  e.notification.close();
  const id = e.notification.data && e.notification.data.id;
  e.waitUntil((async () => {
    const list = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const c of list) {
      if ('focus' in c) { await c.focus(); if (id) c.postMessage({ open: id }); return; }
    }
    if (self.clients.openWindow) await self.clients.openWindow('./#work');
  })());
});

// 서버(GitHub 자동 실행)에서 보낸 알림. 앱이 화면에 떠 있으면 앱 안에서 보여줘요.
self.addEventListener('push', e => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (err) { d = { title: 'Arecmik', body: e.data ? e.data.text() : '' }; }
  e.waitUntil((async () => {
    const list = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    const shown = list.find(c => c.visibilityState === 'visible');
    if (shown) { shown.postMessage({ ring: d }); return; }
    await self.registration.showNotification(d.title || 'Arecmik', { body: d.body || '', icon: 'icon-192-lemon.png', badge: 'icon-192-lemon.png', tag: 'arecmik-' + (d.id || 'push'), data: { id: d.id }, requireInteraction: true, renotify: true });
  })());
});
