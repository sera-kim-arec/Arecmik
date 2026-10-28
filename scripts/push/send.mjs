// Runs every few minutes in GitHub Actions: reads each user's Arecmik data
// and sends due reminders to the devices that turned on "앱을 닫아도 알림 받기".
import admin from 'firebase-admin';
import webpush from 'web-push';
import { dueReminders, message } from './reminders.mjs';

const VAPID_PUBLIC = 'BEfRYpvT3nE53dP86dK8ubzFSS03GzXe6mjS7i-cIK-CzfbCrJgqXaD671yZyQ9Um89xkfJoWhr25AA13Vbl9vg';
const { FIREBASE_SA, WEB_PUSH_PRIVATE_KEY } = process.env;
if (!FIREBASE_SA || !WEB_PUSH_PRIVATE_KEY) {
  console.log('Secrets FIREBASE_SA and WEB_PUSH_PRIVATE_KEY are not set yet. Nothing to do.');
  process.exit(0);
}
admin.initializeApp({ credential: admin.credential.cert(JSON.parse(FIREBASE_SA)) });
const db = admin.firestore();
webpush.setVapidDetails('mailto:arecmik@users.noreply.github.com', VAPID_PUBLIC, WEB_PUSH_PRIVATE_KEY);

const now = Date.now();
const users = await db.collection('users').listDocuments();
let total = 0;
for (const user of users) {
  const pushCol = user.collection('arecmik2push');
  const subs = (await pushCol.where('type', '==', 'sub').get()).docs;
  if (!subs.length) continue;
  const logRef = pushCol.doc('log');
  const sent = ((await logRef.get()).data() || {}).sent || {};

  const rows = (await user.collection('arecmik2').get()).docs;
  const items = [];
  let settings = {};
  for (const r of rows) {
    const j = r.get('j'); if (!j) continue;
    try {
      if (r.id.startsWith('items__')) items.push(JSON.parse(j));
      else if (r.id === 'meta__settings') settings = JSON.parse(j).settings || {};
    } catch { /* skip a broken row */ }
  }
  const tz = subs[0].get('tz') || 'Asia/Seoul';
  const due = dueReminders({ items, settings, tz, now, sent });
  if (!due.length) continue;

  for (const { key, it } of due) {
    const payload = JSON.stringify({ ...message(it, tz), key });
    for (const s of subs) {
      try {
        await webpush.sendNotification(JSON.parse(s.get('sub')), payload, { TTL: 1800, urgency: 'high' });
      } catch (err) {
        if (err.statusCode === 404 || err.statusCode === 410) await s.ref.delete(); // device unsubscribed
        else console.log('push failed', err.statusCode || err.message);
      }
    }
    sent[key] = now; total++;
  }
  // keep three days of history so nothing is sent twice
  const kept = Object.fromEntries(Object.entries(sent).filter(([, ts]) => now - ts < 3 * 86400000));
  await logRef.set({ sent: kept });
}
console.log(`sent ${total} reminder(s)`);
